import os

import discord
from dotenv import load_dotenv

from utils.constants import ENVI_GREEN


load_dotenv()


def get_log_channel_id() -> int | None:
    """
    Gets the staff log channel ID from the .env file.

    If LOG_CHANNEL_ID is missing or invalid, logging is skipped.
    """
    log_channel_id = os.getenv("LOG_CHANNEL_ID")

    if not log_channel_id:
        print("LOG_CHANNEL_ID is missing. Staff channel logs will be skipped.")
        return None

    try:
        return int(log_channel_id)
    except ValueError:
        print("LOG_CHANNEL_ID must be a number with no quotes or spaces.")
        return None


async def send_ledger_log(
    bot: discord.Client,
    title: str,
    description: str,
) -> None:
    """
    Sends an ENVI Ledger event log to the configured log channel.

    If logging fails, it prints the error instead of crashing the command.
    """
    log_channel_id = get_log_channel_id()

    if log_channel_id is None:
        return

    try:
        channel = bot.get_channel(log_channel_id)

        if channel is None:
            channel = await bot.fetch_channel(log_channel_id)

        if not hasattr(channel, "send"):
            print("Configured LOG_CHANNEL_ID does not point to a sendable channel.")
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=ENVI_GREEN,
        )

        embed.set_footer(text="ENVI Ledger Event Log")
        embed.timestamp = discord.utils.utcnow()

        await channel.send(embed=embed)

    except discord.Forbidden:
        print("ENVI Ledger cannot send messages to the configured log channel.")
    except discord.HTTPException as error:
        print(f"Failed to send ENVI Ledger log message: {error}")
    except Exception as error:
        print(f"Unexpected ENVI Ledger log error: {error}")