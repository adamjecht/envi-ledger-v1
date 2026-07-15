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
from services.item_audit_service import get_item_audit
from services.log_channel_service import send_ledger_log
from services.maintenance_service import clear_user_cooldowns, reset_user_data
from services.shop_service import (
    create_shop_item,
    deactivate_shop_item,
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
)
from utils.autocomplete import (
    admin_edit_item_autocomplete,
    admin_iteminfo_autocomplete,
    admin_remove_item_autocomplete,
    admin_restock_item_autocomplete,
)
from utils.embeds import envi_embed, envi_error
from utils.formatting import format_credits


admin_group = app_commands.Group(
    name="admin",
    description="ENVI Ledger staff tools.",
)

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
    description="Add a new item to the ENVI Commercial Exchange.",
)
@app_commands.describe(
    name="The item name.",
    price="The item price in Nexus Credits.",
    description="The item description.",
    category="The item category.",
    rarity="The item rarity.",
    stock="Optional limited stock. Leave blank for unlimited stock.",
)
@app_commands.choices(
    category=[
        app_commands.Choice(name=category, value=category)
        for category in SHOP_CATEGORIES
    ],
    rarity=[
        app_commands.Choice(name=rarity, value=rarity)
        for rarity in ITEM_RARITIES
    ],
)
async def admin_additem(
    interaction: discord.Interaction,
    name: str,
    price: int,
    description: str,
    category: app_commands.Choice[str] | None = None,
    rarity: app_commands.Choice[str] | None = None,
    stock: int | None = None,
):
    if not await require_admin(interaction):
        return

    selected_category = category.value if category is not None else None
    selected_rarity = rarity.value if rarity is not None else None

    try:
        item = create_shop_item(
            name=name,
            price=price,
            description=description,
            category=selected_category,
            rarity=selected_rarity,
            stock=stock,
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ADMIN ITEM CREATION DENIED",
            reason=str(error),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN SHOP LOG",
        description=(
            "Type: `ADMIN_SHOP_ADD`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Item: **{item['name']}**\n"
            f"Price: **{format_credits(item['price'])}**\n"
            f"Category: `{item['category']}`\n"
            f"Rarity: `{item['rarity']}`\n"
            f"Stock: `{format_stock(item['stock'])}`\n"
            f"Status: **Active**\n"
            f"Description: {item['description']}"
        ),
    )

    embed = envi_embed(
        title="ENVI ADMIN ITEM CREATED",
        description=(
            f"Operator: {interaction.user.mention}\n"
            f"Item: **{item['name']}**\n"
            f"Price: **{format_credits(item['price'])}**\n"
            f"Category: `{item['category']}`\n"
            f"Rarity: `{item['rarity']}`\n"
            f"Stock: `{format_stock(item['stock'])}`\n"
            f"Status: **Active**\n"
            f"Description: {item['description']}"
        ),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(
    name="edititem",
    description="Edit an existing ENVI Commercial Exchange item.",
)
@app_commands.describe(
    current_name="The current item name.",
    new_name="Optional new item name.",
    price="Optional new item price.",
    description="Optional new item description.",
    active="Optional active/inactive status.",
    category="Optional new item category.",
    rarity="Optional new item rarity.",
    stock="Optional new stock amount. Leave blank to keep current stock.",
)
@app_commands.choices(
    category=[
        app_commands.Choice(name=category, value=category)
        for category in SHOP_CATEGORIES
    ],
    rarity=[
        app_commands.Choice(name=rarity, value=rarity)
        for rarity in ITEM_RARITIES
    ],
)
@app_commands.autocomplete(
    current_name=admin_edit_item_autocomplete,
)
async def admin_edititem(
    interaction: discord.Interaction,
    current_name: str,
    new_name: str | None = None,
    price: int | None = None,
    description: str | None = None,
    active: bool | None = None,
    category: app_commands.Choice[str] | None = None,
    rarity: app_commands.Choice[str] | None = None,
    stock: int | None = None,
):
    if not await require_admin(interaction):
        return

    selected_category = category.value if category is not None else None
    selected_rarity = rarity.value if rarity is not None else None

    try:
        item = update_shop_item(
            current_name=current_name,
            new_name=new_name,
            price=price,
            description=description,
            active=active,
            category=selected_category,
            rarity=selected_rarity,
            stock=stock,
        )
    except ValueError as error:
        embed = envi_error(
            title="ENVI ADMIN ITEM UPDATE DENIED",
            reason=str(error),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    status = "Active" if int(item["active"]) == 1 else "Inactive"

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI ADMIN SHOP LOG",
        description=(
            "Type: `ADMIN_SHOP_EDIT`\n"
            f"Operator: {interaction.user.mention}\n"
            f"Item: **{item['name']}**\n"
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
            f"Item: **{item['name']}**\n"
            f"Price: **{format_credits(item['price'])}**\n"
            f"Category: `{item['category']}`\n"
            f"Rarity: `{item['rarity']}`\n"
            f"Stock: `{format_stock(item['stock'])}`\n"
            f"Status: **{status}**\n"
            f"Description: {item['description']}"
        ),
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

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
            "Seller: **ENVI Commercial Exchange** "
            "(`System-Owned`)"
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