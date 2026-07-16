from __future__ import annotations

import math

import discord

from utils.embeds import envi_embed
from utils.formatting import format_credits


ORGANIZATION_LEDGER_ENTRIES_PER_PAGE = 5
ORGANIZATION_LEDGER_VIEW_TIMEOUT_SECONDS = 120.0

EMBED_FIELD_NAME_LIMIT = 256
EMBED_FIELD_VALUE_LIMIT = 1024
LEDGER_REASON_DISPLAY_LIMIT = 350


def _shorten_text(
    text: str,
    limit: int,
) -> str:
    """
    Shortens text only when it exceeds a Discord limit.
    """
    if len(text) <= limit:
        return text

    return f"{text[: limit - 3]}..."


def _format_role(
    role: object,
) -> str:
    """
    Formats an organization role for display.
    """
    return str(role).replace(
        "_",
        " ",
    ).title()


def _format_organization_type(
    organization_type: object,
) -> str:
    """
    Formats an organization type for display.
    """
    return str(organization_type).replace(
        "_",
        " ",
    ).title()


def _format_transaction_type(
    transaction_type: object,
) -> str:
    """
    Formats a stored organization transaction type.
    """
    return str(transaction_type).replace(
        "_",
        " ",
    ).title()


def _format_signed_amount(
    amount: object,
) -> str:
    """
    Formats a ledger amount with an explicit sign.
    """
    clean_amount = int(amount)

    if clean_amount > 0:
        return f"+{format_credits(clean_amount)}"

    if clean_amount < 0:
        return f"-{format_credits(abs(clean_amount))}"

    return format_credits(0)


def _format_actor(
    transaction: dict,
) -> str:
    """
    Formats the user responsible for the transaction.
    """
    actor_user_id = transaction.get(
        "actor_user_id"
    )
    actor_name = transaction.get(
        "actor_display_name"
    )

    if actor_user_id is None:
        return "System / ENVI"

    if actor_name is None or not str(
        actor_name
    ).strip():
        return f"Citizen `{actor_user_id}`"

    return (
        f"{str(actor_name).strip()} "
        f"(`{actor_user_id}`)"
    )


def _format_counterparty(
    transaction: dict,
) -> str:
    """
    Formats the user or organization connected to a record.
    """
    target_user_id = transaction.get(
        "target_user_id"
    )
    target_user_name = transaction.get(
        "target_display_name"
    )

    if target_user_id is not None:
        if (
            target_user_name is not None
            and str(target_user_name).strip()
        ):
            return (
                f"Citizen: "
                f"{str(target_user_name).strip()} "
                f"(`{target_user_id}`)"
            )

        return f"Citizen: `{target_user_id}`"

    target_organization_id = transaction.get(
        "target_organization_id"
    )
    target_organization_name = transaction.get(
        "target_organization_name"
    )

    if target_organization_id is not None:
        if (
            target_organization_name is not None
            and str(
                target_organization_name
            ).strip()
        ):
            return (
                "Organization: "
                f"{str(target_organization_name).strip()} "
                f"(`{target_organization_id}`)"
            )

        return (
            "Organization: "
            f"`{target_organization_id}`"
        )

    return "None recorded"


class OrganizationLedgerPaginationView(
    discord.ui.View
):
    """
    Controls a private paginated organization ledger.

    Only the user who opened the ledger may use its
    navigation buttons.
    """

    def __init__(
        self,
        *,
        organization: dict,
        transactions: list[dict],
        viewer_user_id: int,
        viewer_role: str,
    ):
        super().__init__(
            timeout=(
                ORGANIZATION_LEDGER_VIEW_TIMEOUT_SECONDS
            )
        )

        self.organization = organization
        self.transactions = transactions
        self.viewer_user_id = viewer_user_id
        self.viewer_role = viewer_role
        self.current_page = 0

        self.total_pages = max(
            1,
            math.ceil(
                len(self.transactions)
                / ORGANIZATION_LEDGER_ENTRIES_PER_PAGE
            ),
        )

        self.message = None

        self._update_button_states()

    def _get_current_page_transactions(
        self,
    ) -> list[dict]:
        """
        Returns the transactions on the current page.
        """
        start_index = (
            self.current_page
            * ORGANIZATION_LEDGER_ENTRIES_PER_PAGE
        )
        end_index = (
            start_index
            + ORGANIZATION_LEDGER_ENTRIES_PER_PAGE
        )

        return self.transactions[
            start_index:end_index
        ]

    def _update_button_states(
        self,
    ) -> None:
        """
        Disables buttons that cannot currently be used.
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
        Builds the current private ledger page.
        """
        self._update_button_states()

        organization_name = str(
            self.organization["name"]
        )
        organization_type = (
            _format_organization_type(
                self.organization[
                    "organization_type"
                ]
            )
        )

        embed = envi_embed(
            title=(
                "ENVI ORGANIZATION LEDGER — "
                f"{organization_name}"
            ),
            description=(
                f"Organization Type: "
                f"**{organization_type}**\n"
                "Organization Status: **Active**\n"
                "Your Organization Role: "
                f"**{_format_role(self.viewer_role)}**\n"
                "Current Balance: "
                f"**{format_credits(int(self.organization['balance']))}**\n\n"
                "Newest records appear first. "
                "This ledger is restricted to authorized "
                "organization owners and managers."
            ),
        )

        current_transactions = (
            self._get_current_page_transactions()
        )

        if not current_transactions:
            embed.add_field(
                name="Ledger Activity",
                value=(
                    "No organization transaction records "
                    "were found within the requested limit."
                ),
                inline=False,
            )

        for transaction in current_transactions:
            transaction_id = int(
                transaction[
                    "organization_transaction_id"
                ]
            )
            transaction_type = (
                _format_transaction_type(
                    transaction[
                        "transaction_type"
                    ]
                )
            )
            signed_amount = _format_signed_amount(
                transaction["amount"]
            )

            reason = str(
                transaction["reason"]
            ).strip()
            reason = _shorten_text(
                reason,
                LEDGER_REASON_DISPLAY_LIMIT,
            )

            reference_id = transaction.get(
                "reference_id"
            )
            reference_text = (
                f"`{reference_id}`"
                if reference_id
                else "None recorded"
            )

            created_at = transaction.get(
                "created_at"
            )
            created_text = (
                f"`{created_at}`"
                if created_at
                else "Unknown"
            )

            related_item_name = transaction.get(
                "related_item_name"
            )
            related_item_id = transaction.get(
                "related_item_id"
            )

            item_line = ""
            if related_item_id is not None:
                item_name = (
                    str(related_item_name).strip()
                    if related_item_name
                    else "Unknown item"
                )
                item_line = (
                    f"\nRelated Item: {item_name} "
                    f"(`{related_item_id}`)"
                )

            field_name = _shorten_text(
                (
                    f"#{transaction_id} · "
                    f"{transaction_type} · "
                    f"{signed_amount}"
                ),
                EMBED_FIELD_NAME_LIMIT,
            )

            field_value = _shorten_text(
                (
                    f"Actor: {_format_actor(transaction)}\n"
                    "Counterparty: "
                    f"{_format_counterparty(transaction)}\n"
                    "Balance After: "
                    f"**{format_credits(int(transaction['balance_after']))}**\n"
                    f"Reason: {reason}\n"
                    f"Reference: {reference_text}\n"
                    f"Recorded: {created_text}"
                    f"{item_line}"
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
                "ENVI Ledger v1"
                f" • Page {self.current_page + 1}"
                f" of {self.total_pages}"
                f" • {len(self.transactions)} record(s)"
                f" • {ORGANIZATION_LEDGER_ENTRIES_PER_PAGE}"
                " per page"
            )
        )

        return embed

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Prevents other users from controlling the ledger.
        """
        if (
            interaction.user.id
            == self.viewer_user_id
        ):
            return True

        await interaction.response.send_message(
            (
                "These organization ledger controls belong "
                "to the citizen who opened them. "
                "Use `/org ledger` to open your own view."
            ),
            ephemeral=True,
        )
        return False

    async def on_timeout(
        self,
    ) -> None:
        """
        Disables navigation after the view expires.
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
        """
        Moves backward by one ledger page.
        """
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
        """
        Moves forward by one ledger page.
        """
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