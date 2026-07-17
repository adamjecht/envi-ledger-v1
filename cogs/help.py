from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import envi_embed


class HelpCog(commands.Cog):
    """
    Public command and permissions guide for ENVI Ledger.
    """

    def __init__(
        self,
        bot: commands.Bot,
    ):
        self.bot = bot

    @app_commands.command(
        name="help",
        description=(
            "View ENVI Ledger V2 commands, roles, "
            "and citation rules."
        ),
    )
    async def help(
        self,
        interaction: discord.Interaction,
    ):
        embed = envi_embed(
            title="ENVI LEDGER V2 HELP",
            description=(
                "**Institutions & Consequences**\n"
                "Citizens earn. Businesses trade. "
                "Institutions pay. ENVI records. "
                "The Black Badge collects.\n\n"
                "Currency: **₦C — Nexus Credits**"
            ),
        )

        embed.add_field(
            name="Citizen Economy",
            value=(
                "`/ping` — Confirm ENVI is online.\n"
                "`/balance` — View a citizen balance.\n"
                "`/daily` — Claim the Civic Dividend.\n"
                "`/work` — Complete a Shift Assignment.\n"
                "`/pay` — Transfer credits to a citizen.\n"
                "`/leaderboard` — View leading balances.\n"
                "`/help` — Open this command guide."
            ),
            inline=False,
        )

        embed.add_field(
            name="Commercial Exchange & Assets",
            value=(
                "`/shop` — Browse the paginated Exchange.\n"
                "`/buy` — Purchase a system or "
                "organization-owned item.\n"
                "`/inventory` — View owned assets.\n"
                "`/use` — Use an eligible owned item.\n\n"
                "System purchases remove credits from "
                "circulation. Commercial purchases route "
                "revenue to the listed seller organization."
            ),
            inline=False,
        )

        embed.add_field(
            name="Black Badge Citations",
            value=(
                "`/fines` — Privately review your open and "
                "recent resolved citations.\n"
                "`/payfine` — Pay one citation issued to "
                "your own account.\n\n"
                "**OPEN** may be paid, collected, or voided. "
                "**PAID** and **VOID** are terminal. "
                "Payments require the full amount; partial "
                "payments are not supported."
            ),
            inline=False,
        )

        embed.add_field(
            name="Organizations",
            value=(
                "`/org info` — View a public profile.\n"
                "`/org balance` — View an authorized balance.\n"
                "`/org members` — View an authorized roster.\n"
                "`/org deposit` — Deposit personal credits.\n"
                "`/org payuser` — Pay a citizen.\n"
                "`/org payorg` — Pay another organization.\n"
                "`/org ledger` — Audit authorized activity."
            ),
            inline=False,
        )

        embed.add_field(
            name="Organization Roles",
            value=(
                "**OWNER** — Full authority, including "
                "financial actions and leadership control.\n"
                "**MANAGER** — May deposit, issue payments, "
                "and inspect private financial records.\n"
                "**MEMBER** — May inspect permitted public "
                "organization and membership information.\n"
                "Inactive organizations and memberships "
                "cannot authorize new financial activity."
            ),
            inline=False,
        )

        embed.add_field(
            name="Staff — Economy, Items & Maintenance",
            value=(
                "`/admin status`, `/admin addcredits`, "
                "`/admin removecredits`, `/admin setbalance`\n"
                "`/admin additem`, `/admin edititem`, "
                "`/admin removeitem`, `/admin iteminfo`, "
                "`/admin restock`\n"
                "`/admin transactions`, `/admin economy`, "
                "`/admin economyreport`\n"
                "`/admin clearcooldowns`, `/admin resetuser`"
            ),
            inline=False,
        )

        embed.add_field(
            name="Staff — Organizations",
            value=(
                "`/admin org create`, `/admin org edit`\n"
                "`/admin org deactivate`, "
                "`/admin org reactivate`\n"
                "`/admin org addmember`, "
                "`/admin org removemember`, "
                "`/admin org setrole`\n"
                "`/admin org revenue`, "
                "`/admin org setbalance`"
            ),
            inline=False,
        )

        embed.add_field(
            name="Staff — Black Badge",
            value=(
                "`/admin fine issue` — Create an OPEN citation.\n"
                "`/admin fine view` — Inspect its full record.\n"
                "`/admin fine void` — Permanently void an OPEN citation.\n"
                "`/admin fine collect` — Collect an eligible "
                "OPEN citation in full."
            ),
            inline=False,
        )

        embed.add_field(
            name="Ledger Safety",
            value=(
                "Financial operations validate permissions, "
                "balances, statuses, and ownership before "
                "committing. Major activity is written to the "
                "staff audit channel. Unexpected failures use "
                "safe incident references rather than exposing "
                "database details."
            ),
            inline=False,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


async def setup(
    bot: commands.Bot,
):
    await bot.add_cog(
        HelpCog(bot)
    )