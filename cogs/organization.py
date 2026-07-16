from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.economy_service import (
    ensure_user,
)
from services.log_channel_service import (
    send_ledger_log,
)
from services.organization_finance_service import (
    deposit_user_funds_to_organization,
    pay_organization_funds_to_organization,
    pay_organization_funds_to_user,
)
from services.organization_membership_service import (
    get_organization_members,
    require_organization_balance_access,
    require_organization_ledger_access,
    require_organization_members_access,
)
from services.organization_service import (
    get_organization_by_name,
    get_organization_transactions,
)
from utils.embeds import envi_embed, envi_error
from utils.formatting import format_credits
from utils.organization_autocomplete import (
    active_organization_autocomplete,
)
from utils.organization_members_pagination import (
    OrganizationMembersPaginationView,
)
from utils.organization_ledger_pagination import (
    OrganizationLedgerPaginationView,
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

@org_group.command(
    name="deposit",
    description=(
        "Deposit personal Nexus Credits "
        "into an organization."
    ),
)
@app_commands.describe(
    organization_name=(
        "Start typing an active organization name."
    ),
    amount=(
        "The number of personal Nexus Credits "
        "to deposit."
    ),
    reason=(
        "The required reason for this deposit."
    ),
)
@app_commands.autocomplete(
    organization_name=(
        active_organization_autocomplete
    ),
)
async def org_deposit(
    interaction: discord.Interaction,
    organization_name: str,
    amount: int,
    reason: str,
):
    await interaction.response.defer(
        ephemeral=True
    )

    ensure_user(
        user_id=interaction.user.id,
        display_name=interaction.user.display_name,
    )

    organization = _get_active_organization(
        organization_name
    )

    if organization is None:
        embed = envi_error(
            title="ENVI ORGANIZATION DEPOSIT DENIED",
            reason=(
                "Requested organization is not available "
                "in the active Nexus directory."
            ),
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )
        return

    try:
        result = (
            deposit_user_funds_to_organization(
                organization_id=(
                    organization[
                        "organization_id"
                    ]
                ),
                user_id=interaction.user.id,
                amount=amount,
                reason=reason,
            )
        )
    except (ValueError, RuntimeError) as error:
        embed = envi_error(
            title="ENVI ORGANIZATION DEPOSIT DENIED",
            reason=str(error),
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )
        return

    updated_user = result["user"]
    updated_organization = result[
        "organization"
    ]
    membership = result["membership"]
    user_transaction = result[
        "user_transaction"
    ]
    organization_transaction = result[
        "organization_transaction"
    ]
    reference_id = result["reference_id"]

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ORGANIZATION DEPOSIT LOG",
        description=(
            "Type: "
            f"`{user_transaction['type']}` / "
            f"`{organization_transaction['transaction_type']}`\n"
            f"Reference: `{reference_id}`\n"
            f"Depositor: {interaction.user.mention}\n"
            f"Depositor ID: `{interaction.user.id}`\n"
            "Membership Role: "
            f"**{_format_organization_role(membership['role'])}**\n"
            "Organization: "
            f"**{updated_organization['name']}**\n"
            "Organization ID: "
            f"`{updated_organization['organization_id']}`\n"
            f"Amount: **{format_credits(amount)}**\n"
            f"Reason: {reason.strip()}\n"
            "Personal Updated Balance: "
            f"**{format_credits(updated_user['balance'])}**\n"
            "Organization Updated Balance: "
            f"**{format_credits(updated_organization['balance'])}**\n"
            "Personal Transaction ID: "
            f"`{user_transaction['transaction_id']}`\n"
            "Organization Transaction ID: "
            f"`{organization_transaction['organization_transaction_id']}`"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION DEPOSIT COMPLETE",
        description=(
            f"Depositor: {interaction.user.mention}\n"
            "Organization: "
            f"**{updated_organization['name']}**\n"
            "Membership Role: "
            f"**{_format_organization_role(membership['role'])}**\n"
            f"Amount Deposited: "
            f"**{format_credits(amount)}**\n"
            "Personal Updated Balance: "
            f"**{format_credits(updated_user['balance'])}**\n"
            "Organization Updated Balance: "
            f"**{format_credits(updated_organization['balance'])}**\n"
            f"Reference: `{reference_id}`\n\n"
            "**Reason**\n"
            f"{reason.strip()}"
        ),
    )

    await interaction.followup.send(
        embed=embed,
        ephemeral=True,
    )

@org_group.command(
    name="payuser",
    description=(
        "Pay a citizen from an organization account."
    ),
)
@app_commands.describe(
    organization_name=(
        "Start typing an active organization name."
    ),
    recipient=(
        "The citizen receiving the organization payment."
    ),
    amount=(
        "The number of organization Nexus Credits to pay."
    ),
    reason=(
        "The required reason for this organization payment."
    ),
)
@app_commands.autocomplete(
    organization_name=(
        active_organization_autocomplete
    ),
)
async def org_payuser(
    interaction: discord.Interaction,
    organization_name: str,
    recipient: discord.Member,
    amount: int,
    reason: str,
):
    await interaction.response.defer(
        ephemeral=True
    )

    if recipient.bot:
        embed = envi_error(
            title="ENVI ORGANIZATION PAYMENT DENIED",
            reason=(
                "Bots cannot receive organization payments."
            ),
        )
        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )
        return

    ensure_user(
        user_id=interaction.user.id,
        display_name=interaction.user.display_name,
    )
    ensure_user(
        user_id=recipient.id,
        display_name=recipient.display_name,
    )

    organization = _get_active_organization(
        organization_name
    )
    if organization is None:
        embed = envi_error(
            title="ENVI ORGANIZATION PAYMENT DENIED",
            reason=(
                "Requested organization is not available "
                "in the active Nexus directory."
            ),
        )
        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )
        return

    try:
        result = pay_organization_funds_to_user(
            organization_id=(
                organization["organization_id"]
            ),
            actor_user_id=interaction.user.id,
            recipient_user_id=recipient.id,
            recipient_is_bot=recipient.bot,
            amount=amount,
            reason=reason,
        )
    except (ValueError, RuntimeError) as error:
        embed = envi_error(
            title="ENVI ORGANIZATION PAYMENT DENIED",
            reason=str(error),
        )
        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )
        return

    updated_recipient = result["recipient"]
    updated_organization = result[
        "organization"
    ]
    membership = result["membership"]
    recipient_transaction = result[
        "recipient_transaction"
    ]
    organization_transaction = result[
        "organization_transaction"
    ]
    reference_id = result["reference_id"]

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ORGANIZATION USER PAYMENT LOG",
        description=(
            "Type: "
            f"`{recipient_transaction['type']}` / "
            f"`{organization_transaction['transaction_type']}`\n"
            f"Reference: `{reference_id}`\n"
            f"Authorized By: {interaction.user.mention}\n"
            f"Actor ID: `{interaction.user.id}`\n"
            "Membership Role: "
            f"**{_format_organization_role(membership['role'])}**\n"
            "Organization: "
            f"**{updated_organization['name']}**\n"
            "Organization ID: "
            f"`{updated_organization['organization_id']}`\n"
            f"Recipient: {recipient.mention}\n"
            f"Recipient ID: `{recipient.id}`\n"
            f"Amount: **{format_credits(amount)}**\n"
            "Organization Previous Balance: "
            f"**{format_credits(result['organization_balance_before'])}**\n"
            "Organization Updated Balance: "
            f"**{format_credits(updated_organization['balance'])}**\n"
            "Recipient Previous Balance: "
            f"**{format_credits(result['recipient_balance_before'])}**\n"
            "Recipient Updated Balance: "
            f"**{format_credits(updated_recipient['balance'])}**\n"
            f"Reason: {organization_transaction['reason']}\n"
            "Personal Transaction ID: "
            f"`{recipient_transaction['transaction_id']}`\n"
            "Organization Transaction ID: "
            f"`{organization_transaction['organization_transaction_id']}`"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION PAYMENT COMPLETE",
        description=(
            "Organization: "
            f"**{updated_organization['name']}**\n"
            f"Recipient: {recipient.mention}\n"
            "Authorized By: "
            f"{interaction.user.mention}\n"
            "Membership Role: "
            f"**{_format_organization_role(membership['role'])}**\n"
            f"Amount Paid: **{format_credits(amount)}**\n"
            "Organization Updated Balance: "
            f"**{format_credits(updated_organization['balance'])}**\n"
            f"Reference: `{reference_id}`\n\n"
            "**Reason**\n"
            f"{organization_transaction['reason']}"
        ),
    )

    await interaction.followup.send(
        embed=embed,
        ephemeral=True,
    )

@org_group.command(
    name="payorg",
    description=(
        "Transfer Nexus Credits between organizations."
    ),
)
@app_commands.describe(
    source_organization_name=(
        "The active organization issuing the payment."
    ),
    target_organization_name=(
        "The active organization receiving the payment."
    ),
    amount=(
        "The number of organization Nexus Credits to pay."
    ),
    reason=(
        "The required reason for this organization payment."
    ),
)
@app_commands.autocomplete(
    source_organization_name=(
        active_organization_autocomplete
    ),
    target_organization_name=(
        active_organization_autocomplete
    ),
)
async def org_payorg(
    interaction: discord.Interaction,
    source_organization_name: str,
    target_organization_name: str,
    amount: int,
    reason: str,
):
    await interaction.response.defer(
        ephemeral=True
    )

    ensure_user(
        user_id=interaction.user.id,
        display_name=interaction.user.display_name,
    )

    source_organization = _get_active_organization(
        source_organization_name
    )
    if source_organization is None:
        embed = envi_error(
            title="ENVI ORGANIZATION TRANSFER DENIED",
            reason=(
                "Source organization is not available "
                "in the active Nexus directory."
            ),
        )
        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )
        return

    target_organization = _get_active_organization(
        target_organization_name
    )
    if target_organization is None:
        embed = envi_error(
            title="ENVI ORGANIZATION TRANSFER DENIED",
            reason=(
                "Target organization is not available "
                "in the active Nexus directory."
            ),
        )
        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )
        return

    try:
        result = (
            pay_organization_funds_to_organization(
                source_organization_id=(
                    source_organization[
                        "organization_id"
                    ]
                ),
                target_organization_id=(
                    target_organization[
                        "organization_id"
                    ]
                ),
                actor_user_id=interaction.user.id,
                amount=amount,
                reason=reason,
            )
        )
    except (ValueError, RuntimeError) as error:
        embed = envi_error(
            title="ENVI ORGANIZATION TRANSFER DENIED",
            reason=str(error),
        )
        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )
        return

    updated_source = result[
        "source_organization"
    ]
    updated_target = result[
        "target_organization"
    ]
    membership = result["membership"]
    source_transaction = result[
        "source_transaction"
    ]
    target_transaction = result[
        "target_transaction"
    ]
    reference_id = result["reference_id"]

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ORGANIZATION TRANSFER LOG",
        description=(
            "Type: "
            f"`{source_transaction['transaction_type']}` / "
            f"`{target_transaction['transaction_type']}`\n"
            f"Reference: `{reference_id}`\n"
            f"Authorized By: {interaction.user.mention}\n"
            f"Actor ID: `{interaction.user.id}`\n"
            "Membership Role: "
            f"**{_format_organization_role(membership['role'])}**\n"
            "Source Organization: "
            f"**{updated_source['name']}**\n"
            "Source Organization ID: "
            f"`{updated_source['organization_id']}`\n"
            "Target Organization: "
            f"**{updated_target['name']}**\n"
            "Target Organization ID: "
            f"`{updated_target['organization_id']}`\n"
            f"Amount: **{format_credits(amount)}**\n"
            "Source Previous Balance: "
            f"**{format_credits(result['source_balance_before'])}**\n"
            "Source Updated Balance: "
            f"**{format_credits(updated_source['balance'])}**\n"
            "Target Previous Balance: "
            f"**{format_credits(result['target_balance_before'])}**\n"
            "Target Updated Balance: "
            f"**{format_credits(updated_target['balance'])}**\n"
            f"Reason: {source_transaction['reason']}\n"
            "Source Transaction ID: "
            f"`{source_transaction['organization_transaction_id']}`\n"
            "Target Transaction ID: "
            f"`{target_transaction['organization_transaction_id']}`"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION TRANSFER COMPLETE",
        description=(
            "Source Organization: "
            f"**{updated_source['name']}**\n"
            "Target Organization: "
            f"**{updated_target['name']}**\n"
            f"Authorized By: {interaction.user.mention}\n"
            "Membership Role: "
            f"**{_format_organization_role(membership['role'])}**\n"
            f"Amount Paid: **{format_credits(amount)}**\n"
            "Source Updated Balance: "
            f"**{format_credits(updated_source['balance'])}**\n"
            f"Reference: `{reference_id}`\n\n"
            "**Reason**\n"
            f"{source_transaction['reason']}"
        ),
    )

    await interaction.followup.send(
        embed=embed,
        ephemeral=True,
    )

@org_group.command(
    name="ledger",
    description=(
        "View an organization's private transaction ledger."
    ),
)
@app_commands.describe(
    organization_name=(
        "Start typing an active organization name."
    ),
    record_limit=(
        "The number of newest records to load, from 1 to 100."
    ),
)
@app_commands.autocomplete(
    organization_name=(
        active_organization_autocomplete
    ),
)
async def org_ledger(
    interaction: discord.Interaction,
    organization_name: str,
    record_limit: app_commands.Range[
        int,
        1,
        100,
    ] = 25,
):
    organization = _get_active_organization(
        organization_name
    )
    if organization is None:
        embed = envi_error(
            title="ENVI ORGANIZATION LEDGER DENIED",
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
            require_organization_ledger_access(
                organization_id=(
                    organization[
                        "organization_id"
                    ]
                ),
                user_id=interaction.user.id,
            )
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ORGANIZATION LEDGER DENIED",
            reason=str(error),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    try:
        transactions = get_organization_transactions(
            organization_id=(
                organization["organization_id"]
            ),
            limit=int(record_limit),
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ORGANIZATION LEDGER DENIED",
            reason=str(error),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    view = OrganizationLedgerPaginationView(
        organization=organization,
        transactions=transactions,
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