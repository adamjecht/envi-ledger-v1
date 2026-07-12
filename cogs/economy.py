import random

import discord
from discord import app_commands
from discord.ext import commands

from services.cooldown_service import get_remaining_cooldown, set_cooldown
from services.economy_service import (
    add_credits,
    ensure_user,
    get_balance,
    get_top_balances,
    remove_credits,
)
from services.shop_service import (
    decrease_item_stock,
    format_stock,
    get_active_shop_items,
    get_shop_item_by_name,
)
from services.inventory_service import (
    add_item_to_inventory,
    decrease_item_quantity,
    get_user_inventory,
    get_user_inventory_item_by_name,
)
from services.log_channel_service import send_ledger_log
from services.transaction_service import log_transaction
from utils.constants import (
    DAILY_AMOUNT,
    DAILY_COOLDOWN_SECONDS,
    LEADERBOARD_LIMIT,
    SHOP_CATEGORIES,
    TRANSACTION_DAILY,
    TRANSACTION_SHOP_PURCHASE,
    TRANSACTION_TRANSFER_RECEIVED,
    TRANSACTION_TRANSFER_SENT,
    TRANSACTION_WORK,
    WORK_COOLDOWN_SECONDS,
    WORK_MAX_AMOUNT,
    WORK_MIN_AMOUNT,
)
from utils.embeds import envi_embed, envi_error
from utils.formatting import format_credits, format_seconds


class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="balance",
        description="View your ENVI Ledger balance.",
    )
    async def balance(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        target_user = user or interaction.user

        ensure_user(
            user_id=target_user.id,
            display_name=target_user.display_name,
        )

        balance_amount = get_balance(target_user.id)

        embed = envi_embed(
            title="ENVI FINANCIAL SUMMARY",
            description=(
                f"Citizen: {target_user.mention}\n"
                f"Available Balance: **{format_credits(balance_amount)}**\n"
                f"Account Status: **Active**"
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="daily",
        description="Claim your daily Civic Dividend.",
    )
    async def daily(self, interaction: discord.Interaction):
        user = interaction.user

        ensure_user(
            user_id=user.id,
            display_name=user.display_name,
        )

        remaining_seconds = get_remaining_cooldown(
            user_id=user.id,
            command_name="daily",
            cooldown_seconds=DAILY_COOLDOWN_SECONDS,
        )

        if remaining_seconds > 0:
            embed = envi_error(
                title="ENVI CIVIC DIVIDEND DENIED",
                reason=(
                    "Civic Dividend has already been processed. "
                    f"Next claim available in **{format_seconds(remaining_seconds)}**."
                ),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        new_balance = add_credits(user.id, DAILY_AMOUNT)

        log_transaction(
            user_id=user.id,
            transaction_type=TRANSACTION_DAILY,
            amount=DAILY_AMOUNT,
            reason="Daily Civic Dividend processed.",
        )

        set_cooldown(
            user_id=user.id,
            command_name="daily",
        )

        embed = envi_embed(
            title="ENVI CIVIC DIVIDEND PROCESSED",
            description=(
                f"Citizen: {user.mention}\n"
                f"Deposit: **{format_credits(DAILY_AMOUNT)}**\n"
                f"Updated Balance: **{format_credits(new_balance)}**\n"
                "Next claim available in **24h**."
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="work",
        description="Complete a Nexus Shift Assignment for credits.",
    )
    async def work(self, interaction: discord.Interaction):
        user = interaction.user

        ensure_user(
            user_id=user.id,
            display_name=user.display_name,
        )

        remaining_seconds = get_remaining_cooldown(
            user_id=user.id,
            command_name="work",
            cooldown_seconds=WORK_COOLDOWN_SECONDS,
        )

        if remaining_seconds > 0:
            embed = envi_error(
                title="ENVI SHIFT ASSIGNMENT DENIED",
                reason=(
                    "Shift Assignment access is currently cooling down. "
                    f"Next assignment available in **{format_seconds(remaining_seconds)}**."
                ),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        assignments = [
            "Completed a service shift at Eclipse.",
            "Processed inventory for Obsession.",
            "Delivered sealed documents through the Luxuria District.",
            "Assisted with guest intake at Elysium Noir.",
            "Catalogued luxury stock for Foxy Delights.",
            "Filed civic receipts through an ENVI terminal.",
            "Cleaned up a suspicious spill near Sinlink.",
            "Escorted a nervous courier through Gutterlight.",
            "Sorted late-night order slips at Afterglow Diner.",
            "Verified guest manifests for Hotel Seraphine.",
            "You sorted Black Badge citations into 'paid,' 'ignored,' and 'politically inconvenient.'",
            "You cleaned glitter, blood, and someone’s ego off the Eclipse floor. ENVI refuses to rank them by toxicity.",
            "You delivered a cursed package across Sinlink. It hummed twice. You pretended that was normal.",
            "You helped SIN News edit a report until the truth became legally attractive.",
            "You restocked Inferno Lounge napkins after Belial allegedly terrified someone into spilling a drink. Allegedly.",
            "You assisted with a private Obsession fitting. The mirror asked better questions than the client did.",
            "You delivered velvet-sealed invitations to Eclipse’s upper floor. Several guests suddenly remembered how to behave.",
            "You helped prepare an Obsession fragrance display. ENVI detected elevated heart rates and approved the layout.",
            "You escorted VIPs through Paradise’s Edge, where the lighting was soft and the consequences were not.",
            "You handled silk, perfume, and confidential measurements at the Obsession Showroom. Professionalism barely survived.",
            "You reconciled luxury invoices at the Endless Reserve. Every number looked hungry.",
            "You updated ENVI civic records inside the Velvet Obelisk. ENVI noted your unusual compliance.",
            "You carried sealed paperwork from Scarlet Atelier to Ambrosia Hall without asking why it was warm.",
            "You helped reset access permissions for a restricted Luxuria Complex elevator.",
            "You logged suspicious transit delays on Sinlink. Three were mechanical. One was probably a demon.",
            "You assisted with guest registration at Hotel Seraphine and learned that diplomacy smells expensive.",
            "You filed medical debt forms at Saint Emiko Medical Complex. Mercy remains billable.",
            "You delivered a discreet envelope to Elysium Noir and were smart enough not to read it.",
            "You helped archive SIN News footage that officially never existed.",
            "You performed inventory checks for Obsession packaging: black boxes, gold foil, crimson tissue, zero innocence.",
            "You ran a courier route through Gutterlight and came back with all your limbs and most of your dignity.",
            "You helped verify vault receipts at Endless Reserve. The vault blinked. You did not.",
            "You assisted with crowd flow near Eclipse before the bass swallowed the block.",
            "You checked ENVI access pings around Edenveil Gardens and found one camera politely refusing to work.",
            "You delivered a maintenance report to the Velvet Vista observation deck and tried not to stare at the city judging you.",
        ]

        assignment = random.choice(assignments)
        payout = random.randint(WORK_MIN_AMOUNT, WORK_MAX_AMOUNT)

        new_balance = add_credits(user.id, payout)

        log_transaction(
            user_id=user.id,
            transaction_type=TRANSACTION_WORK,
            amount=payout,
            reason=assignment,
        )

        set_cooldown(
            user_id=user.id,
            command_name="work",
        )

        embed = envi_embed(
            title="ENVI SHIFT ASSIGNMENT COMPLETE",
            description=(
                f"Citizen: {user.mention}\n"
                f"Assignment: **{assignment}**\n"
                f"Compensation: **{format_credits(payout)}**\n"
                f"Updated Balance: **{format_credits(new_balance)}**\n"
                "Next assignment available in **4h**."
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="pay",
        description="Transfer Nexus Credits to another citizen.",
    )
    async def pay(
        self,
        interaction: discord.Interaction,
        recipient: discord.Member,
        amount: int,
    ):
        sender = interaction.user

        ensure_user(
            user_id=sender.id,
            display_name=sender.display_name,
        )

        ensure_user(
            user_id=recipient.id,
            display_name=recipient.display_name,
        )

        if recipient.id == sender.id:
            embed = envi_error(
                title="ENVI CREDIT TRANSFER DENIED",
                reason="Sender and recipient cannot be the same citizen.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if amount <= 0:
            embed = envi_error(
                title="ENVI CREDIT TRANSFER DENIED",
                reason="Transfer amount must be greater than zero.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            sender_new_balance = remove_credits(sender.id, amount)
        except ValueError as error:
            embed = envi_error(
                title="ENVI CREDIT TRANSFER DENIED",
                reason=str(error),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        recipient_new_balance = add_credits(recipient.id, amount)

        log_transaction(
            user_id=sender.id,
            target_user_id=recipient.id,
            transaction_type=TRANSACTION_TRANSFER_SENT,
            amount=-amount,
            reason=f"Credit transfer sent to {recipient.display_name}.",
        )

        log_transaction(
            user_id=recipient.id,
            target_user_id=sender.id,
            transaction_type=TRANSACTION_TRANSFER_RECEIVED,
            amount=amount,
            reason=f"Credit transfer received from {sender.display_name}.",
        )

        await send_ledger_log(
            bot=interaction.client,
            title="ENVI LEDGER TRANSFER LOG",
            description=(
                f"Type: `{TRANSACTION_TRANSFER_SENT}` / `{TRANSACTION_TRANSFER_RECEIVED}`\n"
                f"Sender: {sender.mention}\n"
                f"Recipient: {recipient.mention}\n"
                f"Amount: **{format_credits(amount)}**\n"
                f"Sender Updated Balance: **{format_credits(sender_new_balance)}**"
            ),
        )

        embed = envi_embed(
            title="ENVI CREDIT TRANSFER COMPLETE",
            description=(
                f"Sender: {sender.mention}\n"
                f"Recipient: {recipient.mention}\n"
                f"Amount: **{format_credits(amount)}**\n"
                f"Sender Updated Balance: **{format_credits(sender_new_balance)}**"
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="shop",
        description="View the ENVI Commercial Exchange.",
    )
    @app_commands.describe(
        category="Optional category filter for the shop.",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name=category, value=category)
            for category in SHOP_CATEGORIES
        ],
    )
    async def shop(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str] | None = None,
    ):
        await interaction.response.defer()

        selected_category = category.value if category is not None else None
        items = get_active_shop_items(selected_category)

        if not items:
            category_text = (
                f" in category `{selected_category}`"
                if selected_category is not None
                else ""
            )

            embed = envi_error(
                title="ENVI COMMERCIAL EXCHANGE UNAVAILABLE",
                reason=f"No active shop items are currently registered{category_text}.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        item_lines = []

        for item in items:
            item_lines.append(
                f"**{item['name']}** — {format_credits(item['price'])}\n"
                f"Category: `{item['category']}` | Rarity: `{item['rarity']}` | "
                f"Stock: `{format_stock(item['stock'])}`\n"
                f"{item['description']}"
            )

        title = "ENVI COMMERCIAL EXCHANGE"

        if selected_category is not None:
            title = f"{title} — {selected_category}"

        embed = envi_embed(
            title=title,
            description="\n\n".join(item_lines),
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="buy",
        description="Purchase an item from the ENVI Commercial Exchange.",
    )
    async def buy(
        self,
        interaction: discord.Interaction,
        item_name: str,
        quantity: int = 1,
    ):
        await interaction.response.defer()

        user = interaction.user

        ensure_user(
            user_id=user.id,
            display_name=user.display_name,
        )

        if quantity <= 0:
            embed = envi_error(
                title="ENVI PURCHASE DENIED",
                reason="Quantity must be greater than zero.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        item = get_shop_item_by_name(item_name)

        if item is None:
            embed = envi_error(
                title="ENVI PURCHASE DENIED",
                reason="Requested item is not registered in the active exchange.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        current_stock = item["stock"]

        if current_stock is not None:
            current_stock = int(current_stock)

            if current_stock <= 0:
                embed = envi_error(
                    title="ENVI PURCHASE DENIED",
                    reason=f"**{item['name']}** is currently sold out.",
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            if current_stock < quantity:
                embed = envi_error(
                    title="ENVI PURCHASE DENIED",
                    reason=(
                        f"Requested quantity exceeds available stock.\n"
                        f"Item: **{item['name']}**\n"
                        f"Available Stock: **{current_stock}**"
                    ),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

        total_price = item["price"] * quantity
        current_balance = get_balance(user.id)

        if current_balance < total_price:
            embed = envi_error(
                title="ENVI PURCHASE DENIED",
                reason=(
                    f"Insufficient Nexus Credits.\n"
                    f"Required: **{format_credits(total_price)}**\n"
                    f"Available: **{format_credits(current_balance)}**"
                ),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        new_balance = remove_credits(user.id, total_price)

        try:
            remaining_stock = decrease_item_stock(
                item_id=item["item_id"],
                quantity=quantity,
            )
        except ValueError as error:
            refunded_balance = add_credits(user.id, total_price)

            embed = envi_error(
                title="ENVI PURCHASE REFUNDED",
                reason=(
                    f"{str(error)}\n\n"
                    f"Your payment was reversed.\n"
                    f"Restored Balance: **{format_credits(refunded_balance)}**"
                ),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        add_item_to_inventory(
            user_id=user.id,
            item_id=item["item_id"],
            quantity=quantity,
        )

        log_transaction(
            user_id=user.id,
            transaction_type=TRANSACTION_SHOP_PURCHASE,
            amount=-total_price,
            reason=f"Purchased {quantity}x {item['name']}.",
        )

        remaining_stock_text = format_stock(remaining_stock)

        await send_ledger_log(
            bot=interaction.client,
            title="ENVI LEDGER PURCHASE LOG",
            description=(
                f"Type: `{TRANSACTION_SHOP_PURCHASE}`\n"
                f"Citizen: {user.mention}\n"
                f"Item: **{item['name']}**\n"
                f"Category: `{item['category']}`\n"
                f"Rarity: `{item['rarity']}`\n"
                f"Quantity: **{quantity}**\n"
                f"Total: **{format_credits(total_price)}**\n"
                f"Stock Remaining: **{remaining_stock_text}**\n"
                f"Updated Balance: **{format_credits(new_balance)}**"
            ),
        )

        embed = envi_embed(
            title="ENVI PURCHASE CONFIRMED",
            description=(
                f"Citizen: {user.mention}\n"
                f"Item: **{item['name']}**\n"
                f"Category: `{item['category']}` | Rarity: `{item['rarity']}`\n"
                f"Quantity: **{quantity}**\n"
                f"Total: **{format_credits(total_price)}**\n"
                f"Stock Remaining: **{remaining_stock_text}**\n"
                f"Updated Balance: **{format_credits(new_balance)}**"
            ),
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="inventory",
        description="View a citizen's ENVI Asset Registry.",
    )
    async def inventory(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        target_user = user or interaction.user

        ensure_user(
            user_id=target_user.id,
            display_name=target_user.display_name,
        )

        inventory_items = get_user_inventory(target_user.id)

        if not inventory_items:
            embed = envi_embed(
                title="ENVI ASSET REGISTRY",
                description=(
                    f"Citizen: {target_user.mention}\n\n"
                    "No registered assets found."
                ),
            )

            await interaction.response.send_message(embed=embed)
            return

        item_lines = []

        for item in inventory_items:
            use_status = "Usable" if int(item["usable"]) == 1 else "Not Usable"
            item_type = "Consumable" if int(item["consumable"]) == 1 else "Permanent"

            item_lines.append(
                f"**{item['quantity']}x {item['name']}**\n"
                f"Category: `{item['category']}` | Rarity: `{item['rarity']}`\n"
                f"Use Status: `{use_status}` | Type: `{item_type}`\n"
                f"{item['description']}"
            )

        embed = envi_embed(
            title="ENVI ASSET REGISTRY",
            description=(
                f"Citizen: {target_user.mention}\n\n"
                + "\n\n".join(item_lines)
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="use",
        description="Use an item from your ENVI inventory.",
    )
    @app_commands.describe(
        item_name="The exact name of the item you want to use.",
    )
    async def use_item(
        self,
        interaction: discord.Interaction,
        item_name: str,
    ):
        ensure_user(interaction.user.id, interaction.user.display_name)

        item = get_user_inventory_item_by_name(
            user_id=interaction.user.id,
            item_name=item_name,
        )

        if item is None:
            embed = envi_error(
                title="ENVI ITEM USE DENIED",
                reason="That item was not found in your inventory.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if int(item["usable"]) != 1:
            embed = envi_error(
                title="ENVI ITEM USE DENIED",
                reason=(
                    f"**{item['name']}** is registered as a non-usable item. "
                    "It may be collectible, decorative, or reserved for staff-controlled scenes."
                ),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        is_consumable = int(item["consumable"]) == 1

        remaining_quantity = int(item["quantity"])

        if is_consumable:
            try:
                remaining_quantity = decrease_item_quantity(
                    user_id=interaction.user.id,
                    item_id=item["item_id"],
                    quantity=1,
                )
            except ValueError as error:
                embed = envi_error(
                    title="ENVI ITEM USE DENIED",
                    reason=str(error),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        use_message = item["use_message"]

        if use_message is None:
            use_message = (
                f"**{item['name']}** used. ENVI has recorded the action."
            )

        inventory_update = (
            f"One **{item['name']}** was consumed.\n"
            f"Remaining Quantity: **{remaining_quantity}**"
            if is_consumable
            else f"**{item['name']}** remains in your inventory."
        )

        await send_ledger_log(
            bot=interaction.client,
            title="ENVI ITEM USE LOG",
            description=(
                f"User: {interaction.user.mention}\n"
                f"Item: **{item['name']}**\n"
                f"Category: `{item['category']}`\n"
                f"Rarity: `{item['rarity']}`\n"
                f"Consumable: **{'Yes' if is_consumable else 'No'}**\n"
                f"Remaining Quantity: **{remaining_quantity}**"
            ),
        )

        embed = envi_embed(
            title="ENVI ITEM USED",
            description=(
                f"User: {interaction.user.mention}\n"
                f"Item: **{item['name']}**\n"
                f"Category: `{item['category']}` | Rarity: `{item['rarity']}`\n\n"
                f"{use_message}\n\n"
                f"**Inventory Update**\n"
                f"{inventory_update}"
            ),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="leaderboard",
        description="View the top Nexus Credit balances.",
    )
    async def leaderboard(self, interaction: discord.Interaction):
        top_users = get_top_balances(LEADERBOARD_LIMIT)

        if not top_users:
            embed = envi_embed(
                title="ENVI ECONOMIC RANKINGS",
                description="No active financial records found.",
            )

            await interaction.response.send_message(embed=embed)
            return

        ranking_lines = []

        for index, user_record in enumerate(top_users, start=1):
            ranking_lines.append(
                f"**{index}. {user_record['display_name']}** — "
                f"{format_credits(user_record['balance'])}"
            )

        embed = envi_embed(
            title="ENVI ECONOMIC RANKINGS",
            description="\n".join(ranking_lines),
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))