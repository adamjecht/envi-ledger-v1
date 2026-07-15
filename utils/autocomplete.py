from __future__ import annotations

import discord
from discord import app_commands

from services.inventory_service import get_user_inventory
from services.shop_service import (
    get_active_shop_items,
    get_all_shop_items,
)


AUTOCOMPLETE_LIMIT = 25
DISCORD_CHOICE_TEXT_LIMIT = 100


def _shorten_choice_label(label: str) -> str:
    """
    Keeps the visible suggestion label within Discord's 100-character limit.
    """

    if len(label) <= DISCORD_CHOICE_TEXT_LIMIT:
        return label

    return f"{label[:97]}..."


def _find_matching_items(
    items: list[dict],
    current: str,
) -> list[dict]:
    """
    Performs case-insensitive partial item-name matching.

    Items whose names begin with the user's text appear before items
    that merely contain the text. Results never exceed Discord's limit.
    """

    query = current.strip().casefold()
    ranked_items: list[tuple[int, str, dict]] = []
    seen_names: set[str] = set()

    for item in items:
        raw_name = item.get("name")

        if raw_name is None:
            continue

        name = str(raw_name).strip()

        if not name:
            continue

        # Discord choice values cannot exceed 100 characters.
        if len(name) > DISCORD_CHOICE_TEXT_LIMIT:
            continue

        normalized_name = name.casefold()

        if normalized_name in seen_names:
            continue

        if query and query not in normalized_name:
            continue

        seen_names.add(normalized_name)

        starts_with_query = (
            not query
            or normalized_name.startswith(query)
        )

        match_rank = 0 if starts_with_query else 1

        ranked_items.append(
            (
                match_rank,
                normalized_name,
                item,
            )
        )

    ranked_items.sort(
        key=lambda result: (
            result[0],
            result[1],
        )
    )

    return [
        result[2]
        for result in ranked_items[:AUTOCOMPLETE_LIMIT]
    ]


async def buy_item_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Suggests active shop items that currently have stock available.

    Unlimited-stock items are included.
    Sold-out limited-stock items are excluded.
    """

    del interaction

    active_items = get_active_shop_items()

    available_items = [
        item
        for item in active_items
        if (
            item["stock"] is None
            or int(item["stock"]) > 0
        )
    ]

    matches = _find_matching_items(
        items=available_items,
        current=current,
    )

    return [
        app_commands.Choice(
            name=_shorten_choice_label(str(item["name"])),
            value=str(item["name"]),
        )
        for item in matches
    ]


async def use_item_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Suggests usable items currently owned by the interacting user.
    """

    inventory_items = get_user_inventory(
        user_id=interaction.user.id,
    )

    usable_items = [
        item
        for item in inventory_items
        if (
            int(item["usable"]) == 1
            and int(item["quantity"]) > 0
        )
    ]

    matches = _find_matching_items(
        items=usable_items,
        current=current,
    )

    choices: list[app_commands.Choice[str]] = []

    for item in matches:
        item_name = str(item["name"])
        quantity = int(item["quantity"])

        choices.append(
            app_commands.Choice(
                name=_shorten_choice_label(
                    f"{item_name} — Owned: {quantity}"
                ),
                value=item_name,
            )
        )

    return choices


async def admin_edit_item_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Suggests active and inactive items for /admin edititem.
    """

    del interaction

    all_items = get_all_shop_items()

    matches = _find_matching_items(
        items=all_items,
        current=current,
    )

    choices: list[app_commands.Choice[str]] = []

    for item in matches:
        item_name = str(item["name"])
        status = (
            "Active"
            if int(item["active"]) == 1
            else "Inactive"
        )

        choices.append(
            app_commands.Choice(
                name=_shorten_choice_label(
                    f"{item_name} — {status}"
                ),
                value=item_name,
            )
        )

    return choices


async def admin_remove_item_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Suggests active items for /admin removeitem.
    """

    del interaction

    active_items = get_active_shop_items()

    matches = _find_matching_items(
        items=active_items,
        current=current,
    )

    return [
        app_commands.Choice(
            name=_shorten_choice_label(str(item["name"])),
            value=str(item["name"]),
        )
        for item in matches
    ]


async def admin_iteminfo_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Suggests active and inactive items for the future /admin iteminfo command.
    """

    del interaction

    all_items = get_all_shop_items()

    matches = _find_matching_items(
        items=all_items,
        current=current,
    )

    choices: list[app_commands.Choice[str]] = []

    for item in matches:
        item_name = str(item["name"])
        status = (
            "Active"
            if int(item["active"]) == 1
            else "Inactive"
        )

        choices.append(
            app_commands.Choice(
                name=_shorten_choice_label(
                    f"{item_name} — {status}"
                ),
                value=item_name,
            )
        )

    return choices


async def admin_restock_item_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Suggests limited-stock items for /admin restock.

    Sold-out and inactive limited-stock items remain visible.
    Unlimited-stock items are excluded.
    """

    del interaction

    all_items = get_all_shop_items()

    limited_stock_items = [
        item
        for item in all_items
        if item["stock"] is not None
    ]

    matches = _find_matching_items(
        items=limited_stock_items,
        current=current,
    )

    choices: list[app_commands.Choice[str]] = []

    for item in matches:
        item_name = str(item["name"])
        stock = int(item["stock"])
        status = (
            "Active"
            if int(item["active"]) == 1
            else "Inactive"
        )

        choices.append(
            app_commands.Choice(
                name=_shorten_choice_label(
                    f"{item_name} — Stock: {stock} — {status}"
                ),
                value=item_name,
            )
        )

    return choices