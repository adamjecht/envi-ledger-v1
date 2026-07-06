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
from services.shop_service import get_active_shop_items, get_shop_item_by_name
from services.inventory_service import add_item_to_inventory, get_user_inventory
from services.log_channel_service import send_ledger_log
from services.transaction_service import log_transaction
from utils.constants import (
    DAILY_AMOUNT,
    DAILY_COOLDOWN_SECONDS,
    LEADERBOARD_LIMIT,
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
                "Next assignment available in **1h**."
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
    async def shop(self, interaction: discord.Interaction):
        items = get_active_shop_items()

        if not items:
            embed = envi_error(
                title="ENVI COMMERCIAL EXCHANGE UNAVAILABLE",
                reason="No active shop items are currently registered.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        item_lines = []

        for item in items:
            item_lines.append(
                f"**{item['name']}** — {format_credits(item['price'])}\n"
                f"{item['description']}"
            )

        embed = envi_embed(
            title="ENVI COMMERCIAL EXCHANGE",
            description="\n\n".join(item_lines),
        )

        await interaction.response.send_message(embed=embed)

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
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        item = get_shop_item_by_name(item_name)

        if item is None:
            embed = envi_error(
                title="ENVI PURCHASE DENIED",
                reason="Requested item is not registered in the active exchange.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        total_price = item["price"] * quantity

        try:
            new_balance = remove_credits(user.id, total_price)
        except ValueError as error:
            embed = envi_error(
                title="ENVI PURCHASE DENIED",
                reason=str(error),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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

        await send_ledger_log(
            bot=interaction.client,
            title="ENVI LEDGER PURCHASE LOG",
            description=(
                f"Type: `{TRANSACTION_SHOP_PURCHASE}`\n"
                f"Citizen: {user.mention}\n"
                f"Item: **{item['name']}**\n"
                f"Quantity: **{quantity}**\n"
                f"Total: **{format_credits(total_price)}**\n"
                f"Updated Balance: **{format_credits(new_balance)}**"
            ),
        )

        embed = envi_embed(
            title="ENVI PURCHASE CONFIRMED",
            description=(
                f"Citizen: {user.mention}\n"
                f"Item: **{item['name']}**\n"
                f"Quantity: **{quantity}**\n"
                f"Total: **{format_credits(total_price)}**\n"
                f"Updated Balance: **{format_credits(new_balance)}**"
            ),
        )

        await interaction.response.send_message(embed=embed)

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
            item_lines.append(
                f"**{item['quantity']}x {item['name']}**\n"
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