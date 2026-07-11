import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import envi_embed


class HelpCog(commands.Cog):
    """
    Public help command for ENVI Ledger.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="View ENVI Ledger commands and features.",
    )
    async def help(self, interaction: discord.Interaction):
        embed = envi_embed(
            title="ENVI LEDGER HELP",
            description=(
                "**Citizen Commands**\n"
                "`/balance` — View your Nexus Credit balance.\n"
                "`/daily` — Claim your Civic Dividend.\n"
                "`/work` — Complete a Shift Assignment for Nexus Credits.\n"
                "`/pay` — Transfer Nexus Credits to another citizen.\n"
                "`/leaderboard` — View the top Nexus Credit holders.\n\n"
                "**Commercial Exchange**\n"
                "`/shop` — View active shop items.\n"
                "`/shop category:` — Filter the shop by category.\n"
                "`/buy` — Purchase an item from the shop.\n"
                "`/inventory` — View owned items with category, rarity, use status, and type.\n"
                "`/use` — Use an owned item from your inventory.\n\n"
                "**Item Metadata**\n"
                "Items may include category, rarity, stock, use behavior, and custom use messages.\n"
                "Limited-stock items can sell out. Permanent items remain after use. "
                "Consumable items are removed when used.\n\n"
                "**Staff Commands**\n"
                "`/admin addcredits` — Add credits to a citizen.\n"
                "`/admin removecredits` — Remove credits from a citizen.\n"
                "`/admin setbalance` — Set a citizen balance.\n"
                "`/admin resetbalance` — Reset a citizen balance.\n"
                "`/admin additem` — Create a shop item with metadata.\n"
                "`/admin edititem` — Edit shop item price, metadata, status, or stock.\n"
                "`/admin removeitem` — Deactivate a shop item.\n"
                "`/admin transactions` — View recent citizen ledger activity.\n"
                "`/admin status` — View bot maintenance/status information.\n"
                "`/admin economy` — View economy-wide statistics.\n"
                "`/admin economyreport` — Generate a SIN News Financial Pulse report.\n\n"
                "**Ledger Notes**\n"
                "ENVI logs major economy activity to the configured staff log channel. "
                "All credits, purchases, transfers, item use, and admin actions should be treated "
                "as ledger-visible civic activity."
            ),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))