from __future__ import annotations

import math
from datetime import datetime

import discord

from utils.constants import (
    CITATION_STATUS_OPEN,
    CITATION_STATUS_PAID,
    CITATION_STATUS_VOID,
)
from utils.embeds import envi_embed
from utils.formatting import format_credits


CITATIONS_PER_PAGE = 5
RECENT_CITATION_HISTORY_LIMIT = 20
CITATION_VIEW_TIMEOUT_SECONDS = 120.0

EMBED_FIELD_NAME_LIMIT = 256
EMBED_FIELD_VALUE_LIMIT = 1024


def _shorten_text(
    text: str,
    limit: int,
) -> str:
    """
    Shortens text only when required by Discord.
    """
    if len(text) <= limit:
        return text

    return (
        text[: limit - 3]
        + "..."
    )


def _format_timestamp(
    value: object,
) -> str:
    """
    Converts stored ISO timestamps into Discord time.

    Unexpected legacy formats remain readable as text.
    """
    if value is None:
        return "Not recorded"

    text = str(value).strip()

    if not text:
        return "Not recorded"

    try:
        parsed = datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00",
            )
        )

        unix_timestamp = int(
            parsed.timestamp()
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        return f"`{text}`"

    return (
        f"<t:{unix_timestamp}:f>"
        f" • <t:{unix_timestamp}:R>"
    )


def _build_resolution_text(
    citation: dict,
) -> str:
    """
    Builds the citizen-safe resolution information.

    Private administrative notes are deliberately not
    exposed by the public citation view.
    """
    status = str(
        citation["status"]
    ).upper()

    if status == CITATION_STATUS_OPEN:
        identifier = str(
            citation[
                "citation_identifier"
            ]
        )

        return (
            "Resolution: **Payment Pending**\n"
            "Payment Command: "
            f"`/payfine citation_identifier:{identifier}`"
        )

    if status == CITATION_STATUS_PAID:
        transaction_id = citation[
            "payment_transaction_id"
        ]

        return (
            "Resolution: **Paid**\n"
            "Paid At: "
            f"{_format_timestamp(citation['paid_at'])}\n"
            "Payment Transaction: "
            f"`{transaction_id}`"
        )

    if status == CITATION_STATUS_VOID:
        return (
            "Resolution: **Voided**\n"
            "Voided At: "
            f"{_format_timestamp(citation['voided_at'])}"
        )

    return (
        "Resolution: "
        f"**{status}**"
    )


class CitationPaginationView(
    discord.ui.View
):
    """
    Paginated citizen-facing Black Badge record.

    All OPEN citations are displayed first. They are
    followed by recent PAID or VOID history.

    Only the citizen who opened the record may operate
    its navigation buttons.
    """

    def __init__(
        self,
        *,
        open_citations: list[dict],
        recent_history: list[dict],
        report: dict,
        user_id: int,
    ):
        super().__init__(
            timeout=(
                CITATION_VIEW_TIMEOUT_SECONDS
            )
        )

        self.open_citations = list(
            open_citations
        )

        self.recent_history = list(
            recent_history
        )

        self.report = dict(
            report
        )

        self.user_id = user_id

        self.citations = (
            self.open_citations
            + self.recent_history
        )

        self.current_page = 0

        self.total_pages = max(
            1,
            math.ceil(
                len(self.citations)
                / CITATIONS_PER_PAGE
            ),
        )

        self.message = None

        self._update_button_states()

    def _get_current_page_citations(
        self,
    ) -> list[dict]:
        """
        Returns citations belonging to the current page.
        """
        start_index = (
            self.current_page
            * CITATIONS_PER_PAGE
        )

        end_index = (
            start_index
            + CITATIONS_PER_PAGE
        )

        return self.citations[
            start_index:end_index
        ]

    def _update_button_states(
        self,
    ) -> None:
        """
        Disables navigation that cannot be used.
        """
        self.previous_page.disabled = (
            self.current_page <= 0
        )

        self.next_page.disabled = (
            self.current_page
            >= self.total_pages - 1
        )

    def build_embed(
        self,
    ) -> discord.Embed:
        """
        Builds one public citation-ledger page.
        """
        self._update_button_states()

        open_count = int(
            self.report["open_count"]
        )

        open_value = int(
            self.report["open_value"]
        )

        paid_count = int(
            self.report["paid_count"]
        )

        void_count = int(
            self.report["void_count"]
        )

        embed = envi_embed(
            title="BLACK BADGE CITATION RECORD",
            description=(
                "Review your outstanding citations and "
                "recent resolution history.\n\n"
                "**Outstanding**\n"
                f"{open_count} citation(s) totaling "
                f"**{format_credits(open_value)}**\n\n"
                "**Resolved History**\n"
                f"Paid: **{paid_count}**"
                f" • Voided: **{void_count}**\n\n"
                "Fine payments require the full amount "
                "and remove those credits from circulation."
            ),
        )

        for citation in (
            self._get_current_page_citations()
        ):
            identifier = str(
                citation[
                    "citation_identifier"
                ]
            )

            status = str(
                citation["status"]
            ).upper()

            amount = format_credits(
                int(
                    citation["amount"]
                )
            )

            reason = _shorten_text(
                str(
                    citation["reason"]
                ),
                600,
            )

            issuer_name = str(
                citation[
                    "issuer_display_name"
                ]
            )

            field_name = _shorten_text(
                (
                    f"{identifier} — "
                    f"{status} — {amount}"
                ),
                EMBED_FIELD_NAME_LIMIT,
            )

            field_value = _shorten_text(
                (
                    f"Issuer: **{issuer_name}**\n"
                    "Issued: "
                    f"{_format_timestamp(citation['issued_at'])}\n"
                    f"Reason: {reason}\n"
                    f"{_build_resolution_text(citation)}"
                ),
                EMBED_FIELD_VALUE_LIMIT,
            )

            embed.add_field(
                name=field_name,
                value=field_value,
                inline=False,
            )

        embed.set_footer(
            text=(
                f"Page {self.current_page + 1} "
                f"of {self.total_pages}"
                f" • {len(self.open_citations)} open"
                f" • {len(self.recent_history)} "
                "recent resolved"
            )
        )

        return embed

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Prevents other citizens from controlling the view.
        """
        if (
            interaction.user.id
            == self.user_id
        ):
            return True

        await interaction.response.send_message(
            (
                "These citation controls belong to the "
                "citizen who opened them. Use `/fines` "
                "to open your own Black Badge record."
            ),
            ephemeral=True,
        )

        return False

    async def on_timeout(
        self,
    ) -> None:
        """
        Disables buttons after the citation view expires.
        """
        for item in self.children:
            if isinstance(
                item,
                discord.ui.Button,
            ):
                item.disabled = True

        if self.message is None:
            return

        try:
            await self.message.edit(
                view=self
            )

        except (
            discord.NotFound,
            discord.HTTPException,
        ):
            pass

    @discord.ui.button(
        label="Previous",
        style=discord.ButtonStyle.secondary,
        emoji="◀️",
    )
    async def previous_page(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        self.current_page = max(
            0,
            self.current_page - 1,
        )

        self._update_button_states()

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    @discord.ui.button(
        label="Next",
        style=discord.ButtonStyle.secondary,
        emoji="▶️",
    )
    async def next_page(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button

        self.current_page = min(
            self.total_pages - 1,
            self.current_page + 1,
        )

        self._update_button_states()

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )