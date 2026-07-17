import os
import traceback

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from db.database import initialize_database
from services.log_channel_service import send_ledger_log
from services.migration_service import run_database_migrations
from services.shop_service import seed_default_shop_items
from services.organization_service import (
    seed_default_organizations,
)
from utils.embeds import envi_embed
from utils.error_handling import (
    build_command_error_presentation,
)
from utils.responses import send_error_response


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")


if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing from your .env file.")

if not GUILD_ID:
    raise RuntimeError("GUILD_ID is missing from your .env file.")

try:
    GUILD_ID_INT = int(GUILD_ID)
except ValueError as error:
    raise RuntimeError("GUILD_ID must be a number with no quotes or spaces.") from error


GUILD_OBJECT = discord.Object(id=GUILD_ID_INT)


class ENVILedgerBot(commands.Bot):
    async def setup_hook(self):
        """
        Runs before the bot fully connects to Discord.

        This is where we prepare the database, load cogs, and sync slash commands.
        """
        initialize_database()
        run_database_migrations()
        seed_default_organizations()
        seed_default_shop_items()

        await self.load_extension("cogs.economy")
        await self.load_extension("cogs.admin")
        await self.load_extension("cogs.organization")
        await self.load_extension("cogs.help")

        # Copies cog slash commands into the test guild for fast syncing.
        self.tree.copy_global_to(guild=GUILD_OBJECT)

        synced_commands = await self.tree.sync(guild=GUILD_OBJECT)
        print(f"Synced {len(synced_commands)} slash command(s) to guild {GUILD_ID_INT}.")

intents = discord.Intents.default()

bot = ENVILedgerBot(
    command_prefix="!",
    intents=intents,
)


@bot.event
async def on_ready():
    """
    Runs when the bot is online.
    """
    print(f"ENVI Ledger online as {bot.user}.")


@bot.tree.command(
    name="ping",
    description="Check if ENVI Ledger is online.",
    guild=GUILD_OBJECT,
)
async def ping(interaction: discord.Interaction):
    """
    Simple test command.
    """
    embed = envi_embed(
        title="ENVI LEDGER ONLINE",
        description="System heartbeat confirmed.",
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
):
    """
    Handles unexpected slash-command errors globally.

    Users and Discord staff logs receive contextual but
    sanitized information. The complete raw traceback is
    retained only in the application console.
    """
    original_error = getattr(
        error,
        "original",
        error,
    )

    command_name = (
        "Unknown Command"
    )

    if interaction.command is not None:
        command_name = (
            interaction.command.qualified_name
        )

    user_text = (
        "Unknown User"
    )

    if interaction.user is not None:
        user_text = (
            f"{interaction.user} "
            f"({interaction.user.id})"
        )

    presentation = (
        build_command_error_presentation(
            error=error,
            command_name=command_name,
            user_text=user_text,
        )
    )

    error_name = type(
        original_error
    ).__name__

    error_message = (
        str(original_error)
        or "No error message provided."
    )

    traceback_text = "".join(
        traceback.format_exception(
            type(original_error),
            original_error,
            original_error.__traceback__,
        )
    )

    print(
        "\n=== ENVI LEDGER COMMAND ERROR ==="
    )
    print(
        f"Incident: "
        f"{presentation.incident_id}"
    )
    print(
        f"Command: {command_name}"
    )
    print(
        f"User: {user_text}"
    )
    print(
        f"Category: "
        f"{presentation.category}"
    )
    print(
        f"Error Type: {error_name}"
    )
    print(
        f"Error Message: {error_message}"
    )
    print(
        traceback_text
    )
    print(
        "=== END ENVI LEDGER COMMAND ERROR ===\n"
    )

    try:
        await send_error_response(
            interaction=interaction,
            title=presentation.title,
            reason=(
                presentation.public_reason
            ),
        )

    except Exception as response_error:
        print(
            "Unable to deliver the safe command "
            "error response: "
            f"{type(response_error).__name__}"
        )

    await send_ledger_log(
        bot=interaction.client,
        title="ENVI COMMAND ERROR LOG",
        description=(
            presentation.log_description
        ),
    )

bot.run(DISCORD_TOKEN)