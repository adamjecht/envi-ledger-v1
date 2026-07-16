from __future__ import annotations

import math

import discord

from utils.embeds import envi_embed


ORGANIZATION_MEMBERS_PER_PAGE = 10
ORGANIZATION_MEMBER_VIEW_TIMEOUT_SECONDS = 120.0

EMBED_FIELD_NAME_LIMIT = 256
EMBED_FIELD_VALUE_LIMIT = 1024


def _shorten_text(
    text: str,
    limit: int,
) -> str:
    """
    Shortens text only when it exceeds a Discord embed limit.
    """

    if len(text) <= limit:
        return text

    return f"{text[: limit - 3]}..."


def _format_role(
    role: object,
) -> str:
    """
    Formats an organization role for public display.
    """

    return str(role).replace(
        "_",
        " ",
    ).title()


class OrganizationMembersPaginationView(
    discord.ui.View
):
    """
    Controls a private paginated organization roster.

    Only the user who opened the roster may use its buttons.
    """

    def __init__(
        self,
        *,
        organization: dict,
        members: list[dict],
        viewer_user_id: int,
        viewer_role: str,
    ):
        super().__init__(
            timeout=(
                ORGANIZATION_MEMBER_VIEW_TIMEOUT_SECONDS
            )
        )

        self.organization = organization
        self.members = members
        self.viewer_user_id = viewer_user_id
        self.viewer_role = viewer_role
        self.current_page = 0

        self.total_pages = max(
            1,
            math.ceil(
                len(self.members)
                / ORGANIZATION_MEMBERS_PER_PAGE
            ),
        )

        self.message = None
        self._update_button_states()

    def _get_current_page_members(
        self,
    ) -> list[dict]:
        """
        Returns only the members belonging to the current page.
        """

        start_index = (
            self.current_page
            * ORGANIZATION_MEMBERS_PER_PAGE
        )

        end_index = (
            start_index
            + ORGANIZATION_MEMBERS_PER_PAGE
        )

        return self.members[
            start_index:end_index
        ]

    def _update_button_states(self) -> None:
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

    def build_embed(self) -> discord.Embed:
        """
        Builds the organization roster embed.
        """

        self._update_button_states()

        organization_name = str(
            self.organization["name"]
        )

        organization_type = str(
            self.organization["organization_type"]
        ).replace(
            "_",
            " ",
        ).title()

        embed = envi_embed(
            title=(
                "ENVI ORGANIZATION MEMBERS — "
                f"{organization_name}"
            ),
            description=(
                f"Organization Type: "
                f"**{organization_type}**\n"
                "Organization Status: **Active**\n"
                "Your Organization Role: "
                f"**{_format_role(self.viewer_role)}**\n\n"
                "Active membership records are ordered "
                "by authority."
            ),
        )

        current_members = (
            self._get_current_page_members()
        )

        if not current_members:
            embed.add_field(
                name="Membership",
                value=(
                    "No active organization members "
                    "are currently registered."
                ),
                inline=False,
            )

        start_number = (
            self.current_page
            * ORGANIZATION_MEMBERS_PER_PAGE
        ) + 1

        for offset, member in enumerate(
            current_members
        ):
            member_number = start_number + offset

            display_name = str(
                member["display_name"]
            ).strip()

            if not display_name:
                display_name = (
                    f"Citizen {member['user_id']}"
                )

            role = _format_role(
                member["role"]
            )

            joined_at = (
                str(member["joined_at"])
                if member["joined_at"] is not None
                else "Unknown"
            )

            field_name = _shorten_text(
                f"{member_number}. {display_name}",
                EMBED_FIELD_NAME_LIMIT,
            )

            field_value = _shorten_text(
                (
                    f"Role: **{role}**\n"
                    "Membership Status: **Active**\n"
                    f"Joined: `{joined_at}`"
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
                f" • {len(self.members)} active member(s)"
                f" • {ORGANIZATION_MEMBERS_PER_PAGE}"
                " per page"
            )
        )

        return embed

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Prevents other users from controlling the roster.
        """

        if (
            interaction.user.id
            == self.viewer_user_id
        ):
            return True

        await interaction.response.send_message(
            (
                "These organization roster controls "
                "belong to the citizen who opened them. "
                "Use `/org members` to open your own view."
            ),
            ephemeral=True,
        )

        return False

    async def on_timeout(self) -> None:
        """
        Disables navigation when the roster view expires.
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
        Moves the roster backward by one page.
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
        Moves the roster forward by one page.
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