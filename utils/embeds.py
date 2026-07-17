from __future__ import annotations

import discord

from utils.constants import ENVI_GREEN


ENVI_FOOTER_TEXT = (
    "ENVI Ledger v2 • Institutions & Consequences"
)


def envi_embed(
    title: str,
    description: str = "",
) -> discord.Embed:
    """
    Creates a standard ENVI V2 embed.
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=ENVI_GREEN,
    )

    embed.set_footer(
        text=ENVI_FOOTER_TEXT
    )

    return embed


def envi_error(
    title: str,
    reason: str,
) -> discord.Embed:
    """
    Creates a standard ENVI V2 error embed.

    Command code remains responsible for supplying either
    a deliberate validation message or a safe classified
    unexpected-error message.
    """
    clean_reason = str(
        reason
    ).strip()

    if not clean_reason:
        clean_reason = (
            "No additional guidance was supplied."
        )

    embed = discord.Embed(
        title=title,
        description=(
            f"Reason: {clean_reason}"
        ),
        color=ENVI_GREEN,
    )

    embed.set_footer(
        text=ENVI_FOOTER_TEXT
    )

    return embed