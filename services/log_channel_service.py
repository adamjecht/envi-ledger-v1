from __future__ import annotations

import os

import discord
from dotenv import load_dotenv

from utils.constants import ENVI_GREEN


load_dotenv()


LOG_TITLE_LIMIT = 256
LOG_DESCRIPTION_LIMIT = 4096


def _bounded_log_text(
    value: object,
    *,
    limit: int,
    fallback: str,
) -> str:
    """
    Produces non-empty text that remains within Discord's
    embed limits.
    """
    text = str(value).strip()

    if not text:
        return fallback

    if len(text) <= limit:
        return text

    truncation_notice = (
        "\n\n_[Log text truncated by ENVI Ledger.]_"
    )

    available_length = (
        limit
        - len(truncation_notice)
    )

    return (
        text[:available_length]
        + truncation_notice
    )


def get_log_channel_id() -> int | None:
    """
    Gets the configured staff log channel.

    Missing or invalid configuration disables channel
    logging without crashing the originating command.
    """
    log_channel_id = os.getenv(
        "LOG_CHANNEL_ID"
    )

    if not log_channel_id:
        print(
            "LOG_CHANNEL_ID is missing. "
            "Staff channel logs will be skipped."
        )
        return None

    try:
        return int(
            log_channel_id
        )

    except ValueError:
        print(
            "LOG_CHANNEL_ID must be a number with "
            "no quotes or spaces."
        )
        return None


async def send_ledger_log(
    bot: discord.Client,
    title: str,
    description: str,
) -> bool:
    """
    Sends one bounded ENVI staff-audit record.

    Returns True when Discord accepts the log and False
    when logging is unavailable. Log failure never rolls
    back or crashes the originating completed command.
    """
    log_channel_id = (
        get_log_channel_id()
    )

    if log_channel_id is None:
        return False

    safe_title = _bounded_log_text(
        title,
        limit=LOG_TITLE_LIMIT,
        fallback="ENVI LEDGER EVENT LOG",
    )

    safe_description = _bounded_log_text(
        description,
        limit=LOG_DESCRIPTION_LIMIT,
        fallback=(
            "No event description was supplied."
        ),
    )

    try:
        channel = bot.get_channel(
            log_channel_id
        )

        if channel is None:
            channel = await bot.fetch_channel(
                log_channel_id
            )

        if not hasattr(
            channel,
            "send",
        ):
            print(
                "Configured LOG_CHANNEL_ID does not "
                "point to a sendable channel."
            )
            return False

        embed = discord.Embed(
            title=safe_title,
            description=safe_description,
            color=ENVI_GREEN,
        )

        embed.set_footer(
            text=(
                "ENVI Ledger v2 • Staff Audit"
            )
        )

        embed.timestamp = (
            discord.utils.utcnow()
        )

        await channel.send(
            embed=embed,
            allowed_mentions=(
                discord.AllowedMentions.none()
            ),
        )

        return True

    except discord.Forbidden:
        print(
            "ENVI Ledger cannot send messages to "
            "the configured log channel."
        )

    except discord.HTTPException as error:
        print(
            "Failed to send ENVI Ledger log message: "
            f"{type(error).__name__}"
        )

    except Exception as error:
        print(
            "Unexpected ENVI Ledger log failure: "
            f"{type(error).__name__}"
        )

    return False