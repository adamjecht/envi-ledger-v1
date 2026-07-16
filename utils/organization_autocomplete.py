from __future__ import annotations

import discord
from discord import app_commands

from services.organization_service import (
    get_organizations,
)
from utils.constants import (
    ORGANIZATION_AUTOCOMPLETE_LIMIT,
    ORGANIZATION_NAME_MAX_LENGTH,
    SHOP_SYSTEM_SELLER_LABEL,
    SHOP_SYSTEM_SELLER_VALUE,
)


DISCORD_CHOICE_TEXT_LIMIT = 100


def _shorten_organization_label(
    label: str,
) -> str:
    """
    Keeps visible autocomplete labels within Discord's limit.
    """

    if len(label) <= DISCORD_CHOICE_TEXT_LIMIT:
        return label

    return f"{label[:97]}..."


def _find_matching_organizations(
    organizations: list[dict],
    current: str,
) -> list[dict]:
    """
    Performs case-insensitive partial organization matching.

    Names beginning with the entered text rank ahead of names that
    merely contain it.
    """

    query = current.strip().casefold()

    ranked_results: list[
        tuple[
            int,
            str,
            dict,
        ]
    ] = []

    seen_names: set[str] = set()

    for organization in organizations:
        raw_name = organization.get("name")

        if raw_name is None:
            continue

        name = str(raw_name).strip()

        if not name:
            continue

        if len(name) > ORGANIZATION_NAME_MAX_LENGTH:
            continue

        normalized_name = name.casefold()

        if normalized_name in seen_names:
            continue

        if query and query not in normalized_name:
            continue

        seen_names.add(normalized_name)

        match_rank = (
            0
            if (
                not query
                or normalized_name.startswith(query)
            )
            else 1
        )

        ranked_results.append(
            (
                match_rank,
                normalized_name,
                organization,
            )
        )

    ranked_results.sort(
        key=lambda result: (
            result[0],
            result[1],
        )
    )

    return [
        result[2]
        for result in ranked_results[
            :ORGANIZATION_AUTOCOMPLETE_LIMIT
        ]
    ]


async def active_organization_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Suggests active organizations for public and financial commands.
    """

    del interaction

    organizations = get_organizations(
        active_only=True
    )

    matches = _find_matching_organizations(
        organizations=organizations,
        current=current,
    )

    choices: list[
        app_commands.Choice[str]
    ] = []

    for organization in matches:
        name = str(organization["name"])
        organization_type = str(
            organization["organization_type"]
        ).title()

        choices.append(
            app_commands.Choice(
                name=_shorten_organization_label(
                    f"{name} — {organization_type}"
                ),
                value=name,
            )
        )

    return choices


async def admin_organization_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Suggests active and inactive organizations for staff commands.
    """

    del interaction

    organizations = get_organizations()

    matches = _find_matching_organizations(
        organizations=organizations,
        current=current,
    )

    choices: list[
        app_commands.Choice[str]
    ] = []

    for organization in matches:
        name = str(organization["name"])
        organization_type = str(
            organization["organization_type"]
        ).title()

        status = (
            "Active"
            if int(organization["active"]) == 1
            else "Inactive"
        )

        choices.append(
            app_commands.Choice(
                name=_shorten_organization_label(
                    f"{name} — "
                    f"{organization_type} — "
                    f"{status}"
                ),
                value=name,
            )
        )

    return choices

async def inactive_organization_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Suggests only inactive organizations for reactivation.
    """
    del interaction

    organizations = [
        organization
        for organization in get_organizations()
        if int(organization["active"]) == 0
    ]

    matches = _find_matching_organizations(
        organizations=organizations,
        current=current,
    )

    choices: list[
        app_commands.Choice[str]
    ] = []

    for organization in matches:
        name = str(organization["name"])
        organization_type = str(
            organization["organization_type"]
        ).title()

        choices.append(
            app_commands.Choice(
                name=_shorten_organization_label(
                    f"{name} — "
                    f"{organization_type} — "
                    "Inactive"
                ),
                value=name,
            )
        )

    return choices

async def shop_seller_organization_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Suggests active seller organizations plus the explicit
    system-owned option.

    Inactive organizations are deliberately excluded because
    they cannot receive new shop assignments.
    """
    del interaction

    query = current.strip().casefold()

    choices: list[
        app_commands.Choice[str]
    ] = []

    system_search_text = (
        f"{SHOP_SYSTEM_SELLER_LABEL} "
        "system owned envi commercial exchange"
    ).casefold()

    if (
        not query
        or query in system_search_text
    ):
        choices.append(
            app_commands.Choice(
                name=_shorten_organization_label(
                    SHOP_SYSTEM_SELLER_LABEL
                ),
                value=SHOP_SYSTEM_SELLER_VALUE,
            )
        )

    organizations = get_organizations(
        active_only=True
    )
    matches = _find_matching_organizations(
        organizations=organizations,
        current=current,
    )

    remaining_slots = (
        ORGANIZATION_AUTOCOMPLETE_LIMIT
        - len(choices)
    )

    for organization in matches[
        :remaining_slots
    ]:
        name = str(organization["name"])
        organization_type = str(
            organization["organization_type"]
        ).replace(
            "_",
            " ",
        ).title()

        choices.append(
            app_commands.Choice(
                name=_shorten_organization_label(
                    f"{name} — "
                    f"{organization_type} — "
                    "Organization Seller"
                ),
                value=name,
            )
        )

    return choices