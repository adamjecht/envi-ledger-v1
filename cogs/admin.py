import discord
from discord import app_commands

from services.economy_service import (
    add_credits,
    ensure_user,
    get_balance,
    remove_credits,
    set_balance,
)
from services.economy_stats_service import get_economy_stats
from services.economy_report_service import build_economy_report
from services.organization_finance_service import (
    add_admin_organization_revenue,
    set_admin_organization_balance,
)
from services.item_audit_service import get_item_audit
from services.log_channel_service import send_ledger_log
from services.maintenance_service import clear_user_cooldowns, reset_user_data
from services.organization_membership_service import (
    add_organization_member,
    remove_organization_member,
    set_organization_member_role,
)
from services.organization_service import (
    create_organization,
    deactivate_organization,
    get_organization_by_name,
    reactivate_organization,
    update_organization,
)
from services.shop_service import (
    create_shop_item,
    deactivate_shop_item,
    format_item_seller,
    format_stock,
    restock_limited_item,
    update_shop_item,
)
from services.transaction_service import get_recent_transactions, log_transaction
from utils.checks import user_has_admin_role
from utils.constants import (
    ITEM_RARITIES,
    SHOP_CATEGORIES,
    TRANSACTION_ADMIN_ADD,
    TRANSACTION_ADMIN_REMOVE,
    TRANSACTION_ADMIN_RESET,
    TRANSACTION_ADMIN_SET,
    ORGANIZATION_ROLE_MANAGER,
    ORGANIZATION_ROLE_MEMBER,
    ORGANIZATION_ROLE_OWNER,
    ORGANIZATION_TYPE_BUSINESS,
    ORGANIZATION_TYPE_GOVERNMENT,
    ORGANIZATION_TYPE_INSTITUTION,
    SHOP_SYSTEM_SELLER_VALUE,
)
from utils.autocomplete import (
    admin_edit_item_autocomplete,
    admin_iteminfo_autocomplete,
    admin_remove_item_autocomplete,
    admin_restock_item_autocomplete,
)
from utils.embeds import envi_embed, envi_error
from utils.formatting import format_credits
from utils.organization_autocomplete import (
    active_organization_autocomplete,
    admin_organization_autocomplete,
    inactive_organization_autocomplete,
    shop_seller_organization_autocomplete,
)


admin_group = app_commands.Group(
    name="admin",
    description="ENVI Ledger staff tools.",
)

admin_org_group = app_commands.Group(
    name="org",
    description="Manage ENVI Ledger organizations.",
)

admin_group.add_command(admin_org_group)

def format_transaction_amount(amount: int) -> str:
    """
    Formats transaction amounts with clear positive/negative signs.
    """
    if amount > 0:
        return f"+{format_credits(amount)}"

    if amount < 0:
        return f"-{format_credits(abs(amount))}"

    return format_credits(amount)

def format_audit_text(
    value: object,
    fallback: str = "Not registered.",
    limit: int = 1024,
) -> str:
    """
    Formats optional item text safely for a Discord embed field.
    """

    if value is None:
        return fallback

    text = str(value).strip()

    if not text:
        return fallback

    if len(text) <= limit:
        return text

    return f"{text[: limit - 3]}..."

def format_organization_type(
    organization_type: object,
) -> str:
    """
    Formats an organization type for staff output.
    """

    return str(organization_type).replace(
        "_",
        " ",
    ).title()


def format_organization_status(
    active: object,
) -> str:
    """
    Formats an organization active value.
    """

    return (
        "Active"
        if int(active) == 1
        else "Inactive"
    )

def resolve_item_seller_org_id(
    seller_selection: str | None,
) -> int | None:
    """
    Converts an admin seller selection into an organization
    ID.

    None and the explicit system value both represent the
    ENVI Commercial Exchange.
    """
    if seller_selection is None:
        return None

    clean_selection = seller_selection.strip()

    if (
        not clean_selection
        or clean_selection
        == SHOP_SYSTEM_SELLER_VALUE
    ):
        return None

    organization = get_organization_by_name(
        clean_selection
    )

    if organization is None:
        raise ValueError(
            "Selected seller organization is not "
            "registered."
        )

    if int(organization["active"]) != 1:
        raise ValueError(
            "Inactive organizations cannot receive new "
            "shop-item assignments."
        )

    return int(
        organization["organization_id"]
    )

def format_organization_role(
    role: object,
) -> str:
    """
    Formats an organization membership role.
    """

    return str(role).replace(
        "_",
        " ",
    ).title()


def build_organization_change_summary(
    before: dict,
    after: dict,
    changed_fields: tuple[str, ...],
) -> str:
    """
    Builds a readable before-and-after organization audit.
    """

    lines: list[str] = []

    if "name" in changed_fields:
        lines.append(
            f"Name: **{before['name']}** "
            f"→ **{after['name']}**"
        )

    if "organization_type" in changed_fields:
        lines.append(
            "Type: "
            f"**{format_organization_type(before['organization_type'])}** "
            "→ "
            f"**{format_organization_type(after['organization_type'])}**"
        )

    if "description" in changed_fields:
        old_description = format_audit_text(
            before["description"],
            fallback="No description registered.",
            limit=600,
        )

        new_description = format_audit_text(
            after["description"],
            fallback="No description registered.",
            limit=600,
        )

        lines.append(
            "**Previous Description**\n"
            f"{old_description}\n\n"
            "**Updated Description**\n"
            f"{new_description}"
        )

    return "\n".join(lines)


async def require_admin(interaction: discord.Interaction) -> bool:
    """
    Checks whether the interaction user has ENVI Ledger admin access.

    Sends a denial message and returns False if access is denied.
    """
    if not isinstance(interaction.user, discord.Member):
        embed = envi_error(
            title="ENVI ADMIN ACCESS DENIED",
            reason="This command can only be used inside the server.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False

    if not user_has_admin_role(interaction.user):
        embed = envi_error(
            title="ENVI ADMIN ACCESS DENIED",
            reason="Required role not detected.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False

    return True


@admin_group.command(
    name="status",
    description="Check your ENVI Ledger admin access.",
)
async def admin_status(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return

    embed = envi_embed(
        title="ENVI ADMIN ACCESS CONFIRMED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            "Administrative access verified."
        ),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_org_group.command(
    name="create",
    description="Create a new ENVI Ledger organization.",
)
@app_commands.describe(
    name="The unique organization name.",
    organization_type="The organization classification.",
    description="Optional organization description.",
)
@app_commands.choices(
    organization_type=[
        app_commands.Choice(
            name="Business",
            value=ORGANIZATION_TYPE_BUSINESS,
        ),
        app_commands.Choice(
            name="Institution",
            value=ORGANIZATION_TYPE_INSTITUTION,
        ),
        app_commands.Choice(
            name="Government",
            value=ORGANIZATION_TYPE_GOVERNMENT,
        ),
    ],
)
async def admin_org_create(
    interaction: discord.Interaction,
    name: str,
    organization_type: app_commands.Choice[str],
    description: str = "",
):
    if not await require_admin(interaction):
        return

    try:
        organization = create_organization(
            name=name,
            organization_type=(
                organization_type.value
            ),
            description=description,
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ORGANIZATION CREATION DENIED",
            reason=str(error),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    description_text = format_audit_text(
        organization["description"],
        fallback="No description registered.",
        limit=1000,
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN ORGANIZATION LOG",
        description=(
            "Type: `ADMIN_ORG_CREATE`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Organization ID: "
            f"`{organization['organization_id']}`\n"
            f"Organization: **{organization['name']}**\n"
            "Organization Type: "
            f"**{format_organization_type(organization['organization_type'])}**\n"
            "Starting Balance: "
            f"**{format_credits(organization['balance'])}**\n"
            "Status: **Active**\n\n"
            "**Description**\n"
            f"{description_text}"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION CREATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Organization ID: "
            f"`{organization['organization_id']}`\n"
            f"Organization: **{organization['name']}**\n"
            "Organization Type: "
            f"**{format_organization_type(organization['organization_type'])}**\n"
            "Starting Balance: "
            f"**{format_credits(organization['balance'])}**\n"
            "Status: **Active**\n\n"
            "**Description**\n"
            f"{description_text}"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_org_group.command(
    name="edit",
    description="Edit an existing ENVI Ledger organization.",
)
@app_commands.describe(
    current_name="Start typing the current organization name.",
    new_name="Optional replacement organization name.",
    organization_type="Optional replacement classification.",
    description="Optional replacement description.",
)
@app_commands.choices(
    organization_type=[
        app_commands.Choice(
            name="Business",
            value=ORGANIZATION_TYPE_BUSINESS,
        ),
        app_commands.Choice(
            name="Institution",
            value=ORGANIZATION_TYPE_INSTITUTION,
        ),
        app_commands.Choice(
            name="Government",
            value=ORGANIZATION_TYPE_GOVERNMENT,
        ),
    ],
)
@app_commands.autocomplete(
    current_name=admin_organization_autocomplete,
)
async def admin_org_edit(
    interaction: discord.Interaction,
    current_name: str,
    new_name: str | None = None,
    organization_type: (
        app_commands.Choice[str] | None
    ) = None,
    description: str | None = None,
):
    if not await require_admin(interaction):
        return

    selected_type = (
        organization_type.value
        if organization_type is not None
        else None
    )

    try:
        result = update_organization(
            current_name=current_name,
            new_name=new_name,
            organization_type=selected_type,
            description=description,
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ORGANIZATION UPDATE DENIED",
            reason=str(error),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    before = result["before"]
    after = result["after"]
    changed_fields = result["changed_fields"]

    change_summary = (
        build_organization_change_summary(
            before=before,
            after=after,
            changed_fields=changed_fields,
        )
    )

    status = format_organization_status(
        after["active"]
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN ORGANIZATION LOG",
        description=(
            "Type: `ADMIN_ORG_EDIT`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Organization ID: "
            f"`{after['organization_id']}`\n"
            f"Current Organization: **{after['name']}**\n"
            f"Status: **{status}**\n"
            "Preserved Balance: "
            f"**{format_credits(after['balance'])}**\n\n"
            "**Recorded Changes**\n"
            f"{change_summary}\n\n"
            "_Organization ID, memberships, balance, "
            "and transaction history remain intact._"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION UPDATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Organization ID: "
            f"`{after['organization_id']}`\n"
            f"Organization: **{after['name']}**\n"
            "Organization Type: "
            f"**{format_organization_type(after['organization_type'])}**\n"
            f"Status: **{status}**\n"
            "Preserved Balance: "
            f"**{format_credits(after['balance'])}**\n\n"
            "**Recorded Changes**\n"
            f"{change_summary}\n\n"
            "_Existing memberships and transaction "
            "history remain attached to this record._"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_org_group.command(
    name="deactivate",
    description="Deactivate an ENVI Ledger organization.",
)
@app_commands.describe(
    organization_name="Start typing an active organization name.",
    confirm="Confirm that this organization should be deactivated.",
)
@app_commands.autocomplete(
    organization_name=active_organization_autocomplete,
)
async def admin_org_deactivate(
    interaction: discord.Interaction,
    organization_name: str,
    confirm: bool,
):
    if not await require_admin(interaction):
        return

    if not confirm:
        embed = envi_error(
            title="ENVI ORGANIZATION DEACTIVATION DENIED",
            reason=(
                "Deactivation confirmation was not provided."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    try:
        result = deactivate_organization(
            organization_name
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ORGANIZATION DEACTIVATION DENIED",
            reason=str(error),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    organization = result["after"]

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN ORGANIZATION LOG",
        description=(
            "Type: `ADMIN_ORG_DEACTIVATE`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Organization ID: "
            f"`{organization['organization_id']}`\n"
            f"Organization: **{organization['name']}**\n"
            "Organization Type: "
            f"**{format_organization_type(organization['organization_type'])}**\n"
            "Preserved Balance: "
            f"**{format_credits(organization['balance'])}**\n"
            "Previous Status: **Active**\n"
            "Updated Status: **Inactive**\n\n"
            "_New financial activity is blocked. "
            "Membership and transaction history remain intact._"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION DEACTIVATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Organization ID: "
            f"`{organization['organization_id']}`\n"
            f"Organization: **{organization['name']}**\n"
            "Organization Type: "
            f"**{format_organization_type(organization['organization_type'])}**\n"
            "Preserved Balance: "
            f"**{format_credits(organization['balance'])}**\n"
            "Status: **Inactive**\n\n"
            "New organization financial activity is now blocked. "
            "The organization record, balance, memberships, "
            "and transaction history were not deleted."
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_org_group.command(
    name="reactivate",
    description=(
        "Reactivate an inactive ENVI Ledger organization."
    ),
)
@app_commands.describe(
    organization_name=(
        "Start typing an inactive organization name."
    ),
    reason=(
        "The required reason for reactivation."
    ),
    confirm=(
        "Confirm that this organization should be reactivated."
    ),
)
@app_commands.autocomplete(
    organization_name=(
        inactive_organization_autocomplete
    ),
)
async def admin_org_reactivate(
    interaction: discord.Interaction,
    organization_name: str,
    reason: str,
    confirm: bool,
):
    if not await require_admin(interaction):
        return

    if not confirm:
        embed = envi_error(
            title=(
                "ENVI ORGANIZATION REACTIVATION DENIED"
            ),
            reason=(
                "Reactivation confirmation was not provided."
            ),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    try:
        result = reactivate_organization(
            name=organization_name,
            reason=reason,
        )
    except (ValueError, RuntimeError) as error:
        embed = envi_error(
            title=(
                "ENVI ORGANIZATION REACTIVATION DENIED"
            ),
            reason=str(error),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    before = result["before"]
    organization = result["after"]

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN ORGANIZATION LOG",
        description=(
            "Type: `ADMIN_ORG_REACTIVATE`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Operator ID: `{interaction.user.id}`\n"
            "Organization ID: "
            f"`{organization['organization_id']}`\n"
            f"Organization: **{organization['name']}**\n"
            "Organization Type: "
            f"**{format_organization_type(organization['organization_type'])}**\n"
            "Preserved Balance: "
            f"**{format_credits(organization['balance'])}**\n"
            "Previous Status: **Inactive**\n"
            "Updated Status: **Active**\n"
            "Preserved Membership Records: "
            f"**{result['membership_count']}**\n"
            "Preserved Transaction Records: "
            f"**{result['transaction_count']}**\n"
            f"Reason: {result['reason']}\n\n"
            "_No balance, membership, or transaction "
            "history was changed._"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION REACTIVATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            "Organization ID: "
            f"`{organization['organization_id']}`\n"
            f"Organization: **{organization['name']}**\n"
            "Organization Type: "
            f"**{format_organization_type(organization['organization_type'])}**\n"
            "Preserved Balance: "
            f"**{format_credits(organization['balance'])}**\n"
            "Previous Status: **Inactive**\n"
            "Updated Status: **Active**\n\n"
            "**Reason**\n"
            f"{result['reason']}\n\n"
            "Existing memberships and financial history "
            "remain attached to the organization."
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_org_group.command(
    name="revenue",
    description=(
        "Create controlled revenue for an active organization."
    ),
)
@app_commands.describe(
    organization_name=(
        "Start typing an active organization name."
    ),
    amount=(
        "The amount of newly generated organization revenue."
    ),
    reason=(
        "The required event or institutional revenue reason."
    ),
)
@app_commands.autocomplete(
    organization_name=(
        active_organization_autocomplete
    ),
)
async def admin_org_revenue(
    interaction: discord.Interaction,
    organization_name: str,
    amount: int,
    reason: str,
):
    if not await require_admin(interaction):
        return

    organization = get_organization_by_name(
        organization_name
    )
    if organization is None:
        embed = envi_error(
            title="ENVI ORGANIZATION REVENUE DENIED",
            reason=(
                "Requested organization is not registered."
            ),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    ensure_user(
        user_id=interaction.user.id,
        display_name=interaction.user.display_name,
    )

    try:
        result = add_admin_organization_revenue(
            organization_id=(
                organization["organization_id"]
            ),
            actor_user_id=interaction.user.id,
            amount=amount,
            reason=reason,
        )
    except (ValueError, RuntimeError) as error:
        embed = envi_error(
            title="ENVI ORGANIZATION REVENUE DENIED",
            reason=str(error),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    updated_organization = result[
        "organization"
    ]
    transaction = result[
        "organization_transaction"
    ]

    await send_ledger_log(
        bot=interaction.client,
        title=(
            "ENVI ADMIN ORGANIZATION FINANCE LOG"
        ),
        description=(
            "Type: "
            f"`{transaction['transaction_type']}`\n"
            f"Reference: `{result['reference_id']}`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Operator ID: `{interaction.user.id}`\n"
            "Organization ID: "
            f"`{updated_organization['organization_id']}`\n"
            "Organization: "
            f"**{updated_organization['name']}**\n"
            "Organization Status: **Active**\n"
            "Revenue Created: "
            f"**{format_credits(amount)}**\n"
            "Previous Balance: "
            f"**{format_credits(result['balance_before'])}**\n"
            "Updated Balance: "
            f"**{format_credits(updated_organization['balance'])}**\n"
            f"Reason: {transaction['reason']}\n"
            "Organization Transaction ID: "
            f"`{transaction['organization_transaction_id']}`"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION REVENUE CREATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            "Organization: "
            f"**{updated_organization['name']}**\n"
            "Revenue Created: "
            f"**{format_credits(amount)}**\n"
            "Previous Balance: "
            f"**{format_credits(result['balance_before'])}**\n"
            "Updated Balance: "
            f"**{format_credits(updated_organization['balance'])}**\n"
            f"Reference: `{result['reference_id']}`\n\n"
            "**Reason**\n"
            f"{transaction['reason']}"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_org_group.command(
    name="setbalance",
    description=(
        "Set an organization account balance exactly."
    ),
)
@app_commands.describe(
    organization_name=(
        "Start typing an active or inactive organization name."
    ),
    balance=(
        "The exact replacement organization balance."
    ),
    reason=(
        "The required reason for this balance correction."
    ),
)
@app_commands.autocomplete(
    organization_name=(
        admin_organization_autocomplete
    ),
)
async def admin_org_setbalance(
    interaction: discord.Interaction,
    organization_name: str,
    balance: int,
    reason: str,
):
    if not await require_admin(interaction):
        return

    organization = get_organization_by_name(
        organization_name
    )
    if organization is None:
        embed = envi_error(
            title=(
                "ENVI ORGANIZATION BALANCE SET DENIED"
            ),
            reason=(
                "Requested organization is not registered."
            ),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    ensure_user(
        user_id=interaction.user.id,
        display_name=interaction.user.display_name,
    )

    try:
        result = set_admin_organization_balance(
            organization_id=(
                organization["organization_id"]
            ),
            actor_user_id=interaction.user.id,
            new_balance=balance,
            reason=reason,
        )
    except (ValueError, RuntimeError) as error:
        embed = envi_error(
            title=(
                "ENVI ORGANIZATION BALANCE SET DENIED"
            ),
            reason=str(error),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    updated_organization = result[
        "organization"
    ]
    transaction = result[
        "organization_transaction"
    ]
    status = format_organization_status(
        updated_organization["active"]
    )

    await send_ledger_log(
        bot=interaction.client,
        title=(
            "ENVI ADMIN ORGANIZATION FINANCE LOG"
        ),
        description=(
            "Type: "
            f"`{transaction['transaction_type']}`\n"
            f"Reference: `{result['reference_id']}`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Operator ID: `{interaction.user.id}`\n"
            "Organization ID: "
            f"`{updated_organization['organization_id']}`\n"
            "Organization: "
            f"**{updated_organization['name']}**\n"
            f"Organization Status: **{status}**\n"
            "Previous Balance: "
            f"**{format_credits(result['balance_before'])}**\n"
            "Updated Balance: "
            f"**{format_credits(updated_organization['balance'])}**\n"
            "Net Correction: "
            f"**{format_transaction_amount(result['balance_delta'])}**\n"
            f"Reason: {transaction['reason']}\n"
            "Organization Transaction ID: "
            f"`{transaction['organization_transaction_id']}`"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION BALANCE UPDATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            "Organization: "
            f"**{updated_organization['name']}**\n"
            f"Organization Status: **{status}**\n"
            "Previous Balance: "
            f"**{format_credits(result['balance_before'])}**\n"
            "Updated Balance: "
            f"**{format_credits(updated_organization['balance'])}**\n"
            "Net Correction: "
            f"**{format_transaction_amount(result['balance_delta'])}**\n"
            f"Reference: `{result['reference_id']}`\n\n"
            "**Reason**\n"
            f"{transaction['reason']}"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_org_group.command(
    name="addmember",
    description="Add or reactivate an organization member.",
)
@app_commands.describe(
    organization_name="Start typing the organization name.",
    member="The server member to add.",
    role="The member's organization role.",
)
@app_commands.choices(
    role=[
        app_commands.Choice(
            name="Owner",
            value=ORGANIZATION_ROLE_OWNER,
        ),
        app_commands.Choice(
            name="Manager",
            value=ORGANIZATION_ROLE_MANAGER,
        ),
        app_commands.Choice(
            name="Member",
            value=ORGANIZATION_ROLE_MEMBER,
        ),
    ],
)
@app_commands.autocomplete(
    organization_name=admin_organization_autocomplete,
)
async def admin_org_addmember(
    interaction: discord.Interaction,
    organization_name: str,
    member: discord.Member,
    role: app_commands.Choice[str],
):
    if not await require_admin(interaction):
        return

    organization = get_organization_by_name(
        organization_name
    )

    if organization is None:
        embed = envi_error(
            title="ENVI MEMBERSHIP ADDITION DENIED",
            reason=(
                "Requested organization is not registered."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    ensure_user(
        user_id=member.id,
        display_name=member.display_name,
    )

    try:
        result = add_organization_member(
            organization_id=(
                organization["organization_id"]
            ),
            user_id=member.id,
            role=role.value,
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI MEMBERSHIP ADDITION DENIED",
            reason=str(error),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    membership = result["membership"]
    reactivated = bool(result["reactivated"])

    action_word = (
        "Reactivated"
        if reactivated
        else "Added"
    )

    log_type = (
        "ADMIN_ORG_MEMBER_REACTIVATE"
        if reactivated
        else "ADMIN_ORG_MEMBER_ADD"
    )

    organization_status = (
        format_organization_status(
            membership["organization_active"]
        )
    )

    inactive_note = (
        ""
        if int(
            membership["organization_active"]
        )
        == 1
        else (
            "\n\n"
            "**Notice:** This organization is inactive. "
            "The membership is stored, but it grants no "
            "operational permissions until the organization "
            "is reactivated."
        )
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN ORGANIZATION MEMBERSHIP LOG",
        description=(
            f"Type: `{log_type}`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Organization ID: "
            f"`{membership['organization_id']}`\n"
            "Organization: "
            f"**{membership['organization_name']}**\n"
            f"Organization Status: "
            f"**{organization_status}**\n"
            f"Citizen: {member.mention}\n"
            f"Citizen ID: `{member.id}`\n"
            "Role: "
            f"**{format_organization_role(membership['role'])}**\n"
            f"Membership Action: **{action_word}**\n"
            f"Joined At: `{membership['joined_at']}`\n"
            f"Updated At: `{membership['updated_at']}`"
        ),
    )

    embed = envi_embed(
        title=(
            "ENVI ORGANIZATION MEMBER REACTIVATED"
            if reactivated
            else "ENVI ORGANIZATION MEMBER ADDED"
        ),
        description=(
            f"Operator: {interaction.user.mention}\n"
            "Organization: "
            f"**{membership['organization_name']}**\n"
            f"Organization Status: "
            f"**{organization_status}**\n"
            f"Citizen: {member.mention}\n"
            "Role: "
            f"**{format_organization_role(membership['role'])}**\n"
            f"Membership Status: **Active**"
            f"{inactive_note}"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_org_group.command(
    name="setrole",
    description="Change an active organization member's role.",
)
@app_commands.describe(
    organization_name="Start typing the organization name.",
    member="The active organization member.",
    role="The replacement organization role.",
)
@app_commands.choices(
    role=[
        app_commands.Choice(
            name="Owner",
            value=ORGANIZATION_ROLE_OWNER,
        ),
        app_commands.Choice(
            name="Manager",
            value=ORGANIZATION_ROLE_MANAGER,
        ),
        app_commands.Choice(
            name="Member",
            value=ORGANIZATION_ROLE_MEMBER,
        ),
    ],
)
@app_commands.autocomplete(
    organization_name=admin_organization_autocomplete,
)
async def admin_org_setrole(
    interaction: discord.Interaction,
    organization_name: str,
    member: discord.Member,
    role: app_commands.Choice[str],
):
    if not await require_admin(interaction):
        return

    organization = get_organization_by_name(
        organization_name
    )

    if organization is None:
        embed = envi_error(
            title="ENVI MEMBERSHIP ROLE UPDATE DENIED",
            reason=(
                "Requested organization is not registered."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    try:
        result = set_organization_member_role(
            organization_id=(
                organization["organization_id"]
            ),
            user_id=member.id,
            role=role.value,
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI MEMBERSHIP ROLE UPDATE DENIED",
            reason=str(error),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    before = result["before"]
    after = result["after"]

    organization_status = (
        format_organization_status(
            after["organization_active"]
        )
    )

    inactive_note = (
        ""
        if int(after["organization_active"]) == 1
        else (
            "\n\n"
            "**Notice:** This organization is inactive. "
            "The new role is stored, but it grants no "
            "operational permissions until reactivation."
        )
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN ORGANIZATION MEMBERSHIP LOG",
        description=(
            "Type: `ADMIN_ORG_MEMBER_SET_ROLE`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Organization ID: "
            f"`{after['organization_id']}`\n"
            f"Organization: "
            f"**{after['organization_name']}**\n"
            f"Organization Status: "
            f"**{organization_status}**\n"
            f"Citizen: {member.mention}\n"
            f"Citizen ID: `{member.id}`\n"
            "Previous Role: "
            f"**{format_organization_role(before['role'])}**\n"
            "Updated Role: "
            f"**{format_organization_role(after['role'])}**\n"
            f"Updated At: `{after['updated_at']}`"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION MEMBER ROLE UPDATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Organization: "
            f"**{after['organization_name']}**\n"
            f"Organization Status: "
            f"**{organization_status}**\n"
            f"Citizen: {member.mention}\n"
            "Previous Role: "
            f"**{format_organization_role(before['role'])}**\n"
            "Updated Role: "
            f"**{format_organization_role(after['role'])}**"
            f"{inactive_note}"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_org_group.command(
    name="removemember",
    description="Remove an active organization member.",
)
@app_commands.describe(
    organization_name="Start typing the organization name.",
    member="The active organization member to remove.",
    confirm="Confirm the membership removal.",
)
@app_commands.autocomplete(
    organization_name=admin_organization_autocomplete,
)
async def admin_org_removemember(
    interaction: discord.Interaction,
    organization_name: str,
    member: discord.Member,
    confirm: bool,
):
    if not await require_admin(interaction):
        return

    if not confirm:
        embed = envi_error(
            title="ENVI MEMBERSHIP REMOVAL DENIED",
            reason=(
                "Membership removal confirmation "
                "was not provided."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    organization = get_organization_by_name(
        organization_name
    )

    if organization is None:
        embed = envi_error(
            title="ENVI MEMBERSHIP REMOVAL DENIED",
            reason=(
                "Requested organization is not registered."
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    try:
        result = remove_organization_member(
            organization_id=(
                organization["organization_id"]
            ),
            user_id=member.id,
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI MEMBERSHIP REMOVAL DENIED",
            reason=str(error),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    before = result["before"]
    after = result["after"]

    organization_status = (
        format_organization_status(
            after["organization_active"]
        )
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN ORGANIZATION MEMBERSHIP LOG",
        description=(
            "Type: `ADMIN_ORG_MEMBER_REMOVE`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Organization ID: "
            f"`{after['organization_id']}`\n"
            f"Organization: "
            f"**{after['organization_name']}**\n"
            f"Organization Status: "
            f"**{organization_status}**\n"
            f"Citizen: {member.mention}\n"
            f"Citizen ID: `{member.id}`\n"
            "Previous Role: "
            f"**{format_organization_role(before['role'])}**\n"
            "Previous Membership Status: **Active**\n"
            "Updated Membership Status: **Inactive**\n"
            f"Original Joined At: "
            f"`{after['joined_at']}`\n"
            f"Removed At: `{after['removed_at']}`"
        ),
    )

    embed = envi_embed(
        title="ENVI ORGANIZATION MEMBER REMOVED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Organization: "
            f"**{after['organization_name']}**\n"
            f"Organization Status: "
            f"**{organization_status}**\n"
            f"Citizen: {member.mention}\n"
            "Previous Role: "
            f"**{format_organization_role(before['role'])}**\n"
            "Membership Status: **Inactive**\n\n"
            "The membership was soft-removed. "
            "Its original joining date, former role, "
            "and removal timestamp remain available "
            "for historical inspection."
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_group.command(
    name="addcredits",
    description="Add Nexus Credits to a citizen account.",
)
async def admin_addcredits(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: int,
    reason: str,
):
    if not await require_admin(interaction):
        return

    if amount <= 0:
        embed = envi_error(
            title="ENVI ADMIN CREDIT ADDITION DENIED",
            reason="Amount must be greater than zero.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    ensure_user(
        user_id=user.id,
        display_name=user.display_name,
    )

    new_balance = add_credits(user.id, amount)

    log_transaction(
        user_id=user.id,
        transaction_type=TRANSACTION_ADMIN_ADD,
        amount=amount,
        reason=f"Admin add by {interaction.user.display_name}: {reason}",
        target_user_id=interaction.user.id,
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN CREDIT LOG",
        description=(
            f"Type: `{TRANSACTION_ADMIN_ADD}`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Citizen: {user.mention}\n"
            f"Amount Added: **{format_credits(amount)}**\n"
            f"Updated Balance: **{format_credits(new_balance)}**\n"
            f"Reason: {reason}"
        ),
    )

    embed = envi_embed(
        title="ENVI ADMIN CREDIT ADDITION COMPLETE",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Citizen: {user.mention}\n"
            f"Amount Added: **{format_credits(amount)}**\n"
            f"Updated Balance: **{format_credits(new_balance)}**\n"
            f"Reason: {reason}"
        ),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@admin_group.command(
    name="removecredits",
    description="Remove Nexus Credits from a citizen account.",
)
async def admin_removecredits(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: int,
    reason: str,
):
    if not await require_admin(interaction):
        return

    if amount <= 0:
        embed = envi_error(
            title="ENVI ADMIN CREDIT REMOVAL DENIED",
            reason="Amount must be greater than zero.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    ensure_user(
        user_id=user.id,
        display_name=user.display_name,
    )

    try:
        new_balance = remove_credits(user.id, amount)
    except ValueError as error:
        embed = envi_error(
            title="ENVI ADMIN CREDIT REMOVAL DENIED",
            reason=str(error),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    log_transaction(
        user_id=user.id,
        transaction_type=TRANSACTION_ADMIN_REMOVE,
        amount=-amount,
        reason=f"Admin removal by {interaction.user.display_name}: {reason}",
        target_user_id=interaction.user.id,
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN CREDIT LOG",
        description=(
            f"Type: `{TRANSACTION_ADMIN_REMOVE}`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Citizen: {user.mention}\n"
            f"Amount Removed: **{format_credits(amount)}**\n"
            f"Updated Balance: **{format_credits(new_balance)}**\n"
            f"Reason: {reason}"
        ),
    )

    embed = envi_embed(
        title="ENVI ADMIN CREDIT REMOVAL COMPLETE",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Citizen: {user.mention}\n"
            f"Amount Removed: **{format_credits(amount)}**\n"
            f"Updated Balance: **{format_credits(new_balance)}**\n"
            f"Reason: {reason}"
        ),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@admin_group.command(
    name="setbalance",
    description="Set a citizen account balance exactly.",
)
async def admin_setbalance(
    interaction: discord.Interaction,
    user: discord.Member,
    amount: int,
    reason: str,
):
    if not await require_admin(interaction):
        return

    if amount < 0:
        embed = envi_error(
            title="ENVI ADMIN BALANCE SET DENIED",
            reason="Balance cannot be negative.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    ensure_user(
        user_id=user.id,
        display_name=user.display_name,
    )

    old_balance = get_balance(user.id)
    new_balance = set_balance(user.id, amount)
    balance_delta = new_balance - old_balance

    log_transaction(
        user_id=user.id,
        transaction_type=TRANSACTION_ADMIN_SET,
        amount=balance_delta,
        reason=(
            f"Admin set by {interaction.user.display_name}: "
            f"{format_credits(old_balance)} -> {format_credits(new_balance)}. "
            f"{reason}"
        ),
        target_user_id=interaction.user.id,
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN BALANCE LOG",
        description=(
            f"Type: `{TRANSACTION_ADMIN_SET}`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Citizen: {user.mention}\n"
            f"Previous Balance: **{format_credits(old_balance)}**\n"
            f"Updated Balance: **{format_credits(new_balance)}**\n"
            f"Net Change: **{format_transaction_amount(balance_delta)}**\n"
            f"Reason: {reason}"
        ),
    )

    embed = envi_embed(
        title="ENVI ADMIN BALANCE SET COMPLETE",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Citizen: {user.mention}\n"
            f"Previous Balance: **{format_credits(old_balance)}**\n"
            f"Updated Balance: **{format_credits(new_balance)}**\n"
            f"Net Change: **{format_credits(balance_delta)}**\n"
            f"Reason: {reason}"
        ),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(
    name="additem",
    description=(
        "Add a new item to the ENVI Commercial Exchange."
    ),
)
@app_commands.describe(
    name="The item name.",
    price="The item price in Nexus Credits.",
    description="The item description.",
    category="The item category.",
    rarity="The item rarity.",
    stock=(
        "Optional limited stock. "
        "Leave blank for unlimited stock."
    ),
    seller_organization=(
        "Optional active organization seller. "
        "Leave blank for a system-owned item."
    ),
)
@app_commands.choices(
    category=[
        app_commands.Choice(
            name=category,
            value=category,
        )
        for category in SHOP_CATEGORIES
    ],
    rarity=[
        app_commands.Choice(
            name=rarity,
            value=rarity,
        )
        for rarity in ITEM_RARITIES
    ],
)
@app_commands.autocomplete(
    seller_organization=(
        shop_seller_organization_autocomplete
    ),
)
async def admin_additem(
    interaction: discord.Interaction,
    name: str,
    price: int,
    description: str,
    category: (
        app_commands.Choice[str] | None
    ) = None,
    rarity: (
        app_commands.Choice[str] | None
    ) = None,
    stock: int | None = None,
    seller_organization: str | None = None,
):
    if not await require_admin(interaction):
        return

    selected_category = (
        category.value
        if category is not None
        else None
    )
    selected_rarity = (
        rarity.value
        if rarity is not None
        else None
    )

    try:
        seller_org_id = (
            resolve_item_seller_org_id(
                seller_organization
            )
        )

        item = create_shop_item(
            name=name,
            price=price,
            description=description,
            category=selected_category,
            rarity=selected_rarity,
            stock=stock,
            seller_org_id=seller_org_id,
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ADMIN ITEM CREATION DENIED",
            reason=str(error),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    seller_text = format_item_seller(
        item
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN SHOP LOG",
        description=(
            "Type: `ADMIN_SHOP_ADD`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Item ID: `{item['item_id']}`\n"
            f"Item: **{item['name']}**\n"
            f"Seller: **{seller_text}**\n"
            f"Price: **{format_credits(item['price'])}**\n"
            f"Category: `{item['category']}`\n"
            f"Rarity: `{item['rarity']}`\n"
            f"Stock: `{format_stock(item['stock'])}`\n"
            "Status: **Active**\n"
            f"Description: {item['description']}"
        ),
    )

    embed = envi_embed(
        title="ENVI ADMIN ITEM CREATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Item ID: `{item['item_id']}`\n"
            f"Item: **{item['name']}**\n"
            f"Seller: **{seller_text}**\n"
            f"Price: **{format_credits(item['price'])}**\n"
            f"Category: `{item['category']}`\n"
            f"Rarity: `{item['rarity']}`\n"
            f"Stock: `{format_stock(item['stock'])}`\n"
            "Status: **Active**\n"
            f"Description: {item['description']}"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_group.command(
    name="edititem",
    description=(
        "Edit an existing ENVI Commercial Exchange item."
    ),
)
@app_commands.describe(
    current_name="The current item name.",
    new_name="Optional new item name.",
    price="Optional new item price.",
    description="Optional new item description.",
    active="Optional active/inactive status.",
    category="Optional new item category.",
    rarity="Optional new item rarity.",
    stock=(
        "Optional new stock amount. "
        "Leave blank to keep current stock."
    ),
    seller_organization=(
        "Optional replacement seller. Select "
        "System-Owned to remove an organization seller."
    ),
)
@app_commands.choices(
    category=[
        app_commands.Choice(
            name=category,
            value=category,
        )
        for category in SHOP_CATEGORIES
    ],
    rarity=[
        app_commands.Choice(
            name=rarity,
            value=rarity,
        )
        for rarity in ITEM_RARITIES
    ],
)
@app_commands.autocomplete(
    current_name=admin_edit_item_autocomplete,
    seller_organization=(
        shop_seller_organization_autocomplete
    ),
)
async def admin_edititem(
    interaction: discord.Interaction,
    current_name: str,
    new_name: str | None = None,
    price: int | None = None,
    description: str | None = None,
    active: bool | None = None,
    category: (
        app_commands.Choice[str] | None
    ) = None,
    rarity: (
        app_commands.Choice[str] | None
    ) = None,
    stock: int | None = None,
    seller_organization: str | None = None,
):
    if not await require_admin(interaction):
        return

    selected_category = (
        category.value
        if category is not None
        else None
    )
    selected_rarity = (
        rarity.value
        if rarity is not None
        else None
    )

    update_seller = (
        seller_organization is not None
    )

    try:
        seller_org_id = (
            resolve_item_seller_org_id(
                seller_organization
            )
            if update_seller
            else None
        )

        item = update_shop_item(
            current_name=current_name,
            new_name=new_name,
            price=price,
            description=description,
            active=active,
            category=selected_category,
            rarity=selected_rarity,
            stock=stock,
            seller_org_id=seller_org_id,
            update_seller=update_seller,
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ADMIN ITEM UPDATE DENIED",
            reason=str(error),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    status = (
        "Active"
        if int(item["active"]) == 1
        else "Inactive"
    )
    seller_text = format_item_seller(
        item
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN SHOP LOG",
        description=(
            "Type: `ADMIN_SHOP_EDIT`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Item ID: `{item['item_id']}`\n"
            f"Item: **{item['name']}**\n"
            f"Seller: **{seller_text}**\n"
            f"Price: **{format_credits(item['price'])}**\n"
            f"Category: `{item['category']}`\n"
            f"Rarity: `{item['rarity']}`\n"
            f"Stock: `{format_stock(item['stock'])}`\n"
            f"Status: **{status}**\n"
            f"Description: {item['description']}"
        ),
    )

    embed = envi_embed(
        title="ENVI ADMIN ITEM UPDATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Item ID: `{item['item_id']}`\n"
            f"Item: **{item['name']}**\n"
            f"Seller: **{seller_text}**\n"
            f"Price: **{format_credits(item['price'])}**\n"
            f"Category: `{item['category']}`\n"
            f"Rarity: `{item['rarity']}`\n"
            f"Stock: `{format_stock(item['stock'])}`\n"
            f"Status: **{status}**\n"
            f"Description: {item['description']}"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_group.command(
    name="removeitem",
    description="Deactivate an item from the ENVI Commercial Exchange.",
)
@app_commands.describe(
    name="Start typing the name of an active item.",
)
@app_commands.autocomplete(
    name=admin_remove_item_autocomplete,
)
async def admin_removeitem(
    interaction: discord.Interaction,
    name: str,
):
    if not await require_admin(interaction):
        return

    try:
        item = deactivate_shop_item(name)
    except ValueError as error:
        embed = envi_error(
            title="ENVI ADMIN ITEM REMOVAL DENIED",
            reason=str(error),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN SHOP LOG",
        description=(
            "Type: `ADMIN_SHOP_DEACTIVATE`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Item: **{item['name']}**\n"
            f"Category: `{item['category']}`\n"
            f"Rarity: `{item['rarity']}`\n"
            f"Stock: `{format_stock(item['stock'])}`\n"
            f"Status: **Inactive**"
        ),
    )

    embed = envi_embed(
        title="ENVI ADMIN ITEM DEACTIVATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Item: **{item['name']}**\n"
            f"Category: `{item['category']}`\n"
            f"Rarity: `{item['rarity']}`\n"
            f"Stock: `{format_stock(item['stock'])}`\n"
            f"Status: **Inactive**"
            "Historical records and existing inventories remain intact."
        ),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(
    name="iteminfo",
    description="Inspect a complete ENVI Commercial Exchange item record.",
)
@app_commands.describe(
    item_name="Start typing the name of any active or inactive item.",
)
@app_commands.autocomplete(
    item_name=admin_iteminfo_autocomplete,
)
async def admin_iteminfo(
    interaction: discord.Interaction,
    item_name: str,
):
    if not await require_admin(interaction):
        return

    item = get_item_audit(item_name)

    if item is None:
        embed = envi_error(
            title="ENVI ADMIN ITEM AUDIT DENIED",
            reason="Requested item is not registered.",
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    active_status = (
        "Active"
        if int(item["active"]) == 1
        else "Inactive"
    )

    usable_status = (
        "Yes"
        if int(item["usable"]) == 1
        else "No"
    )

    consumable_status = (
        "Yes"
        if int(item["consumable"]) == 1
        else "No"
    )

    if int(item["usable"]) != 1:
        item_behavior = "Non-Usable / Collectible"
    elif int(item["consumable"]) == 1:
        item_behavior = "Consumable"
    else:
        item_behavior = "Permanent"

    description_text = format_audit_text(
        item["description"],
        fallback="No description registered.",
    )

    use_message_text = format_audit_text(
        item["use_message"],
        fallback="No custom use message registered.",
    )

    seller_text = format_item_seller(
        item
    )

    embed = envi_embed(
        title="ENVI ADMIN ITEM AUDIT",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Complete record for **{item['name']}**."
        ),
    )

    embed.add_field(
        name="Identity",
        value=(
            f"Item ID: `{item['item_id']}`\n"
            f"Name: **{item['name']}**\n"
            f"Status: **{active_status}**\n"
            f"Seller: **{seller_text}**"
        ),
        inline=False,
    )

    embed.add_field(
        name="Commerce",
        value=(
            f"Price: **{format_credits(item['price'])}**\n"
            f"Category: `{item['category']}`\n"
            f"Rarity: `{item['rarity']}`\n"
            f"Stock: **{format_stock(item['stock'])}**"
        ),
        inline=False,
    )

    embed.add_field(
        name="Use Registration",
        value=(
            f"Usable: **{usable_status}**\n"
            f"Consumable: **{consumable_status}**\n"
            f"Behavior: **{item_behavior}**"
        ),
        inline=False,
    )

    embed.add_field(
        name="Description",
        value=description_text,
        inline=False,
    )

    embed.add_field(
        name="Use Message",
        value=use_message_text,
        inline=False,
    )

    embed.add_field(
        name="Ownership",
        value=(
            f"Citizens Holding: **{item['holder_count']}**\n"
            f"Total Units Currently Held: **{item['total_owned']}**"
        ),
        inline=False,
    )

    embed.add_field(
        name="Recorded Purchase Activity",
        value=(
            f"Purchase Transactions: **{item['purchase_count']}**\n"
            f"Units Purchased: **{item['units_purchased']}**\n"
            "_Statistics are matched to the item's current "
            "registered name._"
        ),
        inline=False,
    )

    embed.add_field(
        name="Record Timestamps",
        value=(
            f"Created: `{item['created_at']}`\n"
            f"Last Updated: `{item['updated_at']}`"
        ),
        inline=False,
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_group.command(
    name="restock",
    description="Add stock to a limited ENVI Commercial Exchange item.",
)
@app_commands.describe(
    item_name="Start typing the name of a limited-stock item.",
    quantity="The amount of stock to add.",
)
@app_commands.autocomplete(
    item_name=admin_restock_item_autocomplete,
)
async def admin_restock(
    interaction: discord.Interaction,
    item_name: str,
    quantity: int,
):
    if not await require_admin(interaction):
        return

    try:
        item = restock_limited_item(
            item_name=item_name,
            quantity=quantity,
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ADMIN RESTOCK DENIED",
            reason=str(error),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
        return

    status = (
        "Active"
        if int(item["active"]) == 1
        else "Inactive"
    )

    inactive_note = (
        ""
        if int(item["active"]) == 1
        else (
            "\n\n"
            "**Notice:** This item remains inactive. "
            "Restocking does not reactivate it."
        )
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN SHOP LOG",
        description=(
            "Type: `ADMIN_SHOP_RESTOCK`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Item: **{item['name']}**\n"
            f"Item ID: `{item['item_id']}`\n"
            f"Status: **{status}**\n"
            f"Previous Stock: **{item['old_stock']}**\n"
            f"Quantity Added: **{item['added_quantity']}**\n"
            f"Updated Stock: **{item['new_stock']}**"
        ),
    )

    embed = envi_embed(
        title="ENVI ADMIN ITEM RESTOCKED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Item: **{item['name']}**\n"
            f"Status: **{status}**\n"
            f"Previous Stock: **{item['old_stock']}**\n"
            f"Quantity Added: **{item['added_quantity']}**\n"
            f"Updated Stock: **{item['new_stock']}**"
            f"{inactive_note}"
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )

@admin_group.command(
    name="economy",
    description="View ENVI Ledger economy-wide statistics.",
)
async def admin_economy(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return

    await interaction.response.defer(ephemeral=True)

    stats = get_economy_stats()

    richest_user = stats["richest_user"]

    if richest_user is None:
        richest_text = "No registered citizens."
    else:
        richest_text = (
            f"{richest_user['display_name']} "
            f"({format_credits(richest_user['balance'])})"
        )

    embed = envi_embed(
        title="ENVI ECONOMY STATUS",
        description=(
            "**Citizen Accounts**\n"
            f"Registered Citizens: **{stats['total_users']}**\n"
            f"Credits In Circulation: **{format_credits(stats['total_credits'])}**\n"
            f"Current Highest Balance: **{richest_text}**\n\n"
            "**Credit Flow**\n"
            f"Credits Generated: **{format_credits(stats['credits_generated'])}**\n"
            f"Credits Removed: **{format_credits(stats['credits_removed'])}**\n"
            f"Net Economy Change: **{format_credits(stats['net_change'])}**\n\n"
            "**Commerce**\n"
            f"Shop Purchases: **{stats['shop_purchase_count']}**\n"
            f"Shop Spending Total: **{format_credits(stats['shop_spending_total'])}**\n"
            f"Player Transfers: **{stats['transfer_count']}**\n"
            f"Transfer Volume: **{format_credits(stats['transfer_volume'])}**\n\n"
            "**Exchange Inventory**\n"
            f"Active Shop Items: **{stats['active_shop_items']}**\n"
            f"Limited Stock Items: **{stats['limited_stock_items']}**\n"
            f"Sold Out Items: **{stats['sold_out_items']}**\n"
            f"Total Items Held By Citizens: **{stats['inventory_quantity_total']}**"
        ),
    )

    await interaction.followup.send(embed=embed, ephemeral=True)

@admin_group.command(
    name="economyreport",
    description="Generate a SIN News Financial Pulse economy report.",
)
@app_commands.describe(
    public="Post publicly in this channel instead of privately.",
)
async def admin_economyreport(
    interaction: discord.Interaction,
    public: bool = False,
):
    if not await require_admin(interaction):
        return

    await interaction.response.defer(ephemeral=not public)

    report = build_economy_report()

    embed = envi_embed(
        title=report["title"],
        description=report["description"],
    )

    await interaction.followup.send(embed=embed, ephemeral=not public)

@admin_group.command(
    name="transactions",
    description="View recent ENVI Ledger transactions for a citizen.",
)
async def admin_transactions(
    interaction: discord.Interaction,
    user: discord.Member,
    limit: app_commands.Range[int, 1, 20] = 10,
):
    if not await require_admin(interaction):
        return

    ensure_user(
        user_id=user.id,
        display_name=user.display_name,
    )

    if limit <= 0:
        embed = envi_error(
            title="ENVI TRANSACTION LOOKUP DENIED",
            reason="Limit must be greater than zero.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if limit > 20:
        embed = envi_error(
            title="ENVI TRANSACTION LOOKUP DENIED",
            reason="Limit cannot be greater than 20.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    transactions = get_recent_transactions(
        user_id=user.id,
        limit=limit,
    )

    if not transactions:
        embed = envi_embed(
            title="ENVI TRANSACTION AUDIT",
            description=(
                f"Citizen: {user.mention}\n\n"
                "No transaction records found."
            ),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    transaction_lines = []

    for transaction in transactions:
        transaction_lines.append(
            f"**{transaction['type']}** — "
            f"{format_transaction_amount(transaction['amount'])}\n"
            f"{transaction['reason']}\n"
            f"`{transaction['created_at']}`"
        )

    embed = envi_embed(
        title="ENVI TRANSACTION AUDIT",
        description=(
            f"Citizen: {user.mention}\n"
            f"Records Returned: **{len(transactions)}**\n\n"
            + "\n\n".join(transaction_lines)
        ),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(
    name="clearcooldowns",
    description="Clear a citizen's ENVI Ledger cooldowns.",
)
async def admin_clearcooldowns(
    interaction: discord.Interaction,
    user: discord.Member,
):
    if not await require_admin(interaction):
        return

    ensure_user(
        user_id=user.id,
        display_name=user.display_name,
    )

    deleted_count = clear_user_cooldowns(user_id=user.id)

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN MAINTENANCE LOG",
        description=(
            "Type: `ADMIN_CLEAR_COOLDOWNS`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Citizen: {user.mention}\n"
            f"Cooldown Records Cleared: **{deleted_count}**"
        ),
    )

    embed = envi_embed(
        title="ENVI COOLDOWN RECORDS CLEARED",
        description=(
            f"Citizen: {user.mention}\n"
            f"Cooldown Records Cleared: **{deleted_count}**\n\n"
            "Daily and work cooldown testing may now resume."
        ),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(
    name="resetuser",
    description="Reset one citizen's ENVI Ledger test data.",
)
async def admin_resetuser(
    interaction: discord.Interaction,
    user: discord.Member,
    confirm: bool,
):
    if not await require_admin(interaction):
        return

    if not confirm:
        embed = envi_error(
            title="ENVI USER RESET DENIED",
            reason="Reset confirmation was not provided.",
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    ensure_user(
        user_id=user.id,
        display_name=user.display_name,
    )

    reset_report = reset_user_data(
        user_id=user.id,
        display_name=user.display_name,
    )

    balance_delta = reset_report["new_balance"] - reset_report["old_balance"]

    log_transaction(
        user_id=user.id,
        transaction_type=TRANSACTION_ADMIN_RESET,
        amount=balance_delta,
        reason=(
            f"Admin reset by {interaction.user.display_name}. "
            "User economy test data cleared."
        ),
        target_user_id=interaction.user.id,
    )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN USER RESET LOG",
        description=(
            f"Type: `{TRANSACTION_ADMIN_RESET}`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Citizen: {user.mention}\n"
            f"Previous Balance: **{format_credits(reset_report['old_balance'])}**\n"
            f"Updated Balance: **{format_credits(reset_report['new_balance'])}**\n"
            f"Inventory Records Cleared: **{reset_report['inventory_deleted']}**\n"
            f"Cooldown Records Cleared: **{reset_report['cooldowns_deleted']}**\n"
            f"Transaction Records Cleared: **{reset_report['transactions_deleted']}**"
        ),
    )

    embed = envi_embed(
        title="ENVI USER DATA RESET COMPLETE",
        description=(
            f"Citizen: {user.mention}\n"
            f"Previous Balance: **{format_credits(reset_report['old_balance'])}**\n"
            f"Updated Balance: **{format_credits(reset_report['new_balance'])}**\n\n"
            f"Inventory Records Cleared: **{reset_report['inventory_deleted']}**\n"
            f"Cooldown Records Cleared: **{reset_report['cooldowns_deleted']}**\n"
            f"Transaction Records Cleared: **{reset_report['transactions_deleted']}**\n\n"
            "A fresh admin reset record has been logged."
        ),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    bot.tree.add_command(admin_group)