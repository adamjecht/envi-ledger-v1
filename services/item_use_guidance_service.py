from difflib import get_close_matches

from services.inventory_service import get_user_inventory
from services.shop_service import get_all_shop_items


USE_GUIDANCE_LIMIT = 3
USE_CLOSE_MATCH_CUTOFF = 0.55


def _normalize_item_name(item_name: object) -> str:
    """
    Produces a case-insensitive item name for comparison.
    """

    return str(item_name).strip().casefold()


def _get_usable_inventory_items(
    user_id: int,
) -> list[dict]:
    """
    Returns usable items the user currently owns.
    """

    inventory_items = get_user_inventory(user_id)

    return [
        item
        for item in inventory_items
        if (
            int(item["usable"]) == 1
            and int(item["quantity"]) > 0
        )
    ]


def _get_close_owned_items(
    inventory_items: list[dict],
    requested_name: str,
) -> list[dict]:
    """
    Finds close name matches inside the user's owned inventory.

    Results are case-insensitive and limited to a small guidance list.
    """

    normalized_requested_name = _normalize_item_name(
        requested_name
    )

    if not normalized_requested_name:
        return []

    items_by_normalized_name: dict[str, dict] = {}

    for item in inventory_items:
        normalized_name = _normalize_item_name(item["name"])

        if not normalized_name:
            continue

        items_by_normalized_name.setdefault(
            normalized_name,
            item,
        )

    matching_names = get_close_matches(
        normalized_requested_name,
        list(items_by_normalized_name.keys()),
        n=USE_GUIDANCE_LIMIT,
        cutoff=USE_CLOSE_MATCH_CUTOFF,
    )

    return [
        items_by_normalized_name[name]
        for name in matching_names
    ]


def _format_owned_item_options(
    items: list[dict],
) -> str:
    """
    Formats owned item options for an ENVI error response.
    """

    item_lines: list[str] = []

    for item in items[:USE_GUIDANCE_LIMIT]:
        quantity = int(item["quantity"])

        if int(item["usable"]) != 1:
            behavior = "Not Usable"
        elif int(item["consumable"]) == 1:
            behavior = "Consumable"
        else:
            behavior = "Permanent"

        item_lines.append(
            f"• **{item['name']}** — "
            f"{behavior}, Owned: **{quantity}**"
        )

    return "\n".join(item_lines)


def build_unknown_item_use_reason(
    user_id: int,
    requested_name: str,
) -> str:
    """
    Builds contextual guidance when /use finds no exact owned item.

    It distinguishes between:
    - an empty inventory
    - a registered item the user does not own
    - a likely misspelling
    - a user who owns no usable items
    """

    clean_requested_name = requested_name.strip()
    inventory_items = get_user_inventory(user_id)

    if not inventory_items:
        return (
            "That item was not found in your inventory.\n\n"
            "Your ENVI Asset Registry is currently empty. "
            "Use `/shop` to browse available items."
        )

    usable_items = [
        item
        for item in inventory_items
        if (
            int(item["usable"]) == 1
            and int(item["quantity"]) > 0
        )
    ]

    normalized_requested_name = _normalize_item_name(
        clean_requested_name
    )

    registered_item = next(
        (
            item
            for item in get_all_shop_items()
            if _normalize_item_name(item["name"])
            == normalized_requested_name
        ),
        None,
    )

    if registered_item is not None:
        if usable_items:
            return (
                f"**{registered_item['name']}** is registered, "
                "but you do not own it.\n\n"
                "**Usable items you currently own**\n"
                f"{_format_owned_item_options(usable_items)}\n\n"
                "Use `/use` autocomplete to select one."
            )

        return (
            f"**{registered_item['name']}** is registered, "
            "but you do not own it.\n\n"
            "You currently own no items registered as usable. "
            "Use `/inventory` to review your assets or `/shop` "
            "to browse available items."
        )

    close_owned_items = _get_close_owned_items(
        inventory_items=inventory_items,
        requested_name=clean_requested_name,
    )

    if close_owned_items:
        return (
            f"No exact owned item matched "
            f"**{clean_requested_name}**.\n\n"
            "**Did you mean:**\n"
            f"{_format_owned_item_options(close_owned_items)}\n\n"
            "Use `/use` autocomplete to submit the exact name."
        )

    if usable_items:
        return (
            f"No exact owned item matched "
            f"**{clean_requested_name}**.\n\n"
            "**Usable items you currently own**\n"
            f"{_format_owned_item_options(usable_items)}\n\n"
            "Use `/use` autocomplete to select one."
        )

    return (
        f"No exact owned item matched "
        f"**{clean_requested_name}**.\n\n"
        "You own items, but none are currently registered "
        "as usable. Use `/inventory` to review their status."
    )


def build_non_usable_item_reason(
    user_id: int,
    item: dict,
) -> str:
    """
    Explains why an owned item cannot be used and suggests alternatives.
    """

    base_reason = (
        f"**{item['name']}** is registered as a non-usable item. "
        "It may be collectible, decorative, or reserved for "
        "staff-controlled scenes. It cannot be consumed or activated "
        "with `/use`."
    )

    usable_items = _get_usable_inventory_items(user_id)

    if not usable_items:
        return (
            f"{base_reason}\n\n"
            "You currently own no usable alternatives."
        )

    return (
        f"{base_reason}\n\n"
        "**Usable items you currently own**\n"
        f"{_format_owned_item_options(usable_items)}\n\n"
        "Use `/use` autocomplete to select one."
    )