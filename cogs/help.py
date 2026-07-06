import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import envi_embed


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="View the ENVI Ledger command directory.",
    )
    async def help_command(self, interaction: discord.Interaction):
        embed = envi_embed(
            title="ENVI LEDGER COMMAND DIRECTORY",
            description=(
                "Civic economy interface for Nexus Credits, shop assets, "
                "and staff-controlled financial records."
            ),
        )

        embed.add_field(
            name="Public Commands",
            value=(
                "`/balance` — View your Nexus Credit balance.\n"
                "`/daily` — Claim the Civic Dividend.\n"
                "`/work` — Complete a Shift Assignment for credits.\n"
                "`/pay` — Transfer Nexus Credits to another citizen.\n"
                "`/shop` — View active Commercial Exchange items.\n"
                "`/buy` — Purchase an active shop item.\n"
                "`/inventory` — View registered owned items.\n"
                "`/leaderboard` — View the top Nexus Credit balances.\n"
                "`/help` — View this command directory."
            ),
            inline=False,
        )

        embed.add_field(
            name="Admin Commands",
            value=(
                "`/admin status` — Check ENVI Ledger admin access.\n"
                "`/admin addcredits` — Add credits to a citizen account.\n"
                "`/admin removecredits` — Remove credits from a citizen account.\n"
                "`/admin setbalance` — Set a citizen balance exactly.\n"
                "`/admin additem` — Add a shop item.\n"
                "`/admin edititem` — Edit or reactivate a shop item.\n"
                "`/admin removeitem` — Deactivate a shop item.\n"
                "`/admin transactions` — View recent user transaction records."
            ),
            inline=False,
        )

        embed.add_field(
            name="Operational Notes",
            value=(
                "Admin commands require the configured ENVI Ledger Admin role.\n"
                "Shop item removal deactivates items instead of deleting records.\n"
                "Transactions are logged for audits, corrections, and dispute checks.\n"
                "Nexus Credits are tracked as server economy data, not real currency."
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))