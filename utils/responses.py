import discord

from utils.embeds import envi_error


async def send_error_response(
    interaction: discord.Interaction,
    title: str,
    reason: str,
) -> None:
    """
    Safely sends an error response to a slash command interaction.

    If the interaction has not been answered yet, this sends the first response.
    If the interaction was already answered, this sends a follow-up message.
    """
    embed = envi_error(
        title=title,
        reason=reason,
    )

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)