import discord

from utils.constants import ENVI_GREEN


def envi_embed(title: str, description: str = "") -> discord.Embed:
    """
    Creates a standard ENVI-styled embed.
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=ENVI_GREEN,
    )

    embed.set_footer(text="ENVI Ledger v1")
    return embed


def envi_error(title: str, reason: str) -> discord.Embed:
    """
    Creates a standard ENVI error embed.
    """
    embed = discord.Embed(
        title=title,
        description=f"Reason: {reason}",
        color=ENVI_GREEN,
    )

    embed.set_footer(text="ENVI Ledger v1")
    return embed