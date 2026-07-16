from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.organization_membership_service import (
    get_organization_members,
    require_organization_balance_access,
    require_organization_members_access,
)
from services.organization_service import (
    get_organization_by_name,
)
from utils.embeds import envi_embed, envi_error
from utils.formatting import format_credits
from utils.organization_autocomplete import (
    active_organization_autocomplete,
)
from utils.organization_members_pagination import (
    OrganizationMembersPaginationView,
)


EMBED_FIELD_VALUE_LIMIT = 1024


org_group = app_commands.Group(
    name="org",
    description="Inspect and operate ENVI organizations.",
)


def _format_organization_type(
    organization_type: object,
) -> str:
    """
    Formats an organization type for public output.
    """

    return str(organization_type).replace(
        "_",
        " ",
    ).title()


def _format_organization_role(
    role: object,
) -> str:
    """
    Formats an organization role for public output.
    """

    return str(role).replace(
        "_",
        " ",
    ).title()


def _shorten_text(
    text: str,
    limit: int,
) -> str:
    """
    Shortens text only when it exceeds a Discord limit.
    """

    if len(text) <= limit:
        return text

    return f"{text[: limit - 3]}..."


def _format_leadership_names(
    members: list[dict],
    role: str,
) -> str:
    """
    Formats active leaders assigned to one role.
    """

    names = [
        str(member["display_name"]).strip()
        or f"Citizen {member['user_id']}"
        for member in members
        if str(member["role"]) == role
    ]

    if not names:
        return "None registered."

    return _shorten_text(
        ", ".join(
            f"**{name}**"
            for name in names
        ),
        EMBED_FIELD_VALUE_LIMIT,
    )


def _get_active_organization(
    organization_name: str,
) -> dict | None:
    """
    Retrieves an active organization by exact name.
    """

    organization = get_organization_by_name(
        organization_name
    )

    if organization is None:
        return None

    if int(organization["active"]) != 1:
        return None

    return organization


@org_group.command(
    name="info",
    description="View an active organization's public profile.",
)
@app_commands.describe(
    organization_name="Start typing an active organization name.",
)
@app_commands.autocomplete(
    organization_name=active_organization_autocomplete,
)
async def org_info(
    interaction: discord.Interaction,
    organization_name: str,
):
    organization = _get_active_organization(
        organization_name
    )

    if organization is None:
        embed = envi_error(
            title="ENVI ORGANIZATION DIRECTORY DENIED",
            reason=(
                "Requested organization is not available "
                "in the active Nexus directory."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    members = get_organization_members(
        organization["organization_id"]
    )

    description = str(
        organization["description"]
    ).strip()

    if not description:
        description = (
            "No public organization description "
            "is currently registered."
        )

    owner_names = _format_leadership_names(
        members=members,
        role="OWNER",
    )

    manager_names = _format_leadership_names(
        members=members,
        role="MANAGER",
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION DIRECTORY",
        description=(
            f"**{organization['name']}**\n\n"
            f"{description}"
        ),
    )

    embed.add_field(
        name="Classification",
        value=(
            "Organization Type: "
            f"**{_format_organization_type(organization['organization_type'])}**\n"
            "Operational Status: **Active**"
        ),
        inline=False,
    )

    embed.add_field(
        name="Ownership",
        value=owner_names,
        inline=False,
    )

    embed.add_field(
        name="Management",
        value=manager_names,
        inline=False,
    )

    embed.add_field(
        name="Membership",
        value=(
            "Active Members: "
            f"**{len(members)}**\n"
            "Use `/org members` to inspect the full "
            "roster when authorized."
        ),
        inline=False,
    )

    embed.add_field(
        name="Directory Record",
        value=(
            f"Organization ID: "
            f"`{organization['organization_id']}`\n"
            f"Registered: `{organization['created_at']}`\n"
            f"Last Updated: `{organization['updated_at']}`"
        ),
        inline=False,
    )

    await interaction.response.send_message(
        embed=embed,
    )


@org_group.command(
    name="balance",
    description="View an organization balance when authorized.",
)
@app_commands.describe(
    organization_name="Start typing an active organization name.",
)
@app_commands.autocomplete(
    organization_name=active_organization_autocomplete,
)
async def org_balance(
    interaction: discord.Interaction,
    organization_name: str,
):
    organization = _get_active_organization(
        organization_name
    )

    if organization is None:
        embed = envi_error(
            title="ENVI ORGANIZATION BALANCE DENIED",
            reason=(
                "Requested organization is not available "
                "in the active Nexus directory."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    try:
        membership = (
            require_organization_balance_access(
                organization_id=(
                    organization["organization_id"]
                ),
                user_id=interaction.user.id,
            )
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ORGANIZATION BALANCE DENIED",
            reason=str(error),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    embed = envi_embed(
        title="ENVI ORGANIZATION FINANCIAL SUMMARY",
        description=(
            f"Organization: "
            f"**{organization['name']}**\n"
            "Organization Type: "
            f"**{_format_organization_type(organization['organization_type'])}**\n"
            f"Viewer: {interaction.user.mention}\n"
            "Viewer Role: "
            f"**{_format_organization_role(membership['role'])}**\n"
            "Available Balance: "
            f"**{format_credits(int(organization['balance']))}**\n"
            "Operational Status: **Active**\n\n"
            "_Financial details are restricted to "
            "organization owners and managers._"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )


@org_group.command(
    name="members",
    description="View an organization roster when authorized.",
)
@app_commands.describe(
    organization_name="Start typing an active organization name.",
)
@app_commands.autocomplete(
    organization_name=active_organization_autocomplete,
)
async def org_members(
    interaction: discord.Interaction,
    organization_name: str,
):
    organization = _get_active_organization(
        organization_name
    )

    if organization is None:
        embed = envi_error(
            title="ENVI ORGANIZATION MEMBERSHIP DENIED",
            reason=(
                "Requested organization is not available "
                "in the active Nexus directory."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    try:
        membership = (
            require_organization_members_access(
                organization_id=(
                    organization["organization_id"]
                ),
                user_id=interaction.user.id,
            )
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ORGANIZATION MEMBERSHIP DENIED",
            reason=str(error),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    members = get_organization_members(
        organization["organization_id"]
    )

    if not members:
        embed = envi_error(
            title="ENVI ORGANIZATION MEMBERSHIP DENIED",
            reason=(
                "No active organization membership "
                "records were found."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    view = OrganizationMembersPaginationView(
        organization=organization,
        members=members,
        viewer_user_id=interaction.user.id,
        viewer_role=membership["role"],
    )

    await interaction.response.send_message(
        embed=view.build_embed(),
        view=view,
        ephemeral=True,
    )

    view.message = (
        await interaction.original_response()
    )


async def setup(
    bot: commands.Bot,
):
    bot.tree.add_command(org_group)