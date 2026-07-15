from __future__ import annotations

import math

import discord

from services.shop_service import format_stock
from utils.embeds import envi_embed
from utils.formatting import format_credits


SHOP_ITEMS_PER_PAGE = 6
SHOP_VIEW_TIMEOUT_SECONDS = 120.0

EMBED_FIELD_NAME_LIMIT = 256
EMBED_FIELD_VALUE_LIMIT = 1024


def _shorten_text(text: str, limit: int) -> str:
    """
    Shortens text only when it exceeds a Discord embed-field limit.
    """

    if len(text) <= limit:
        return text

    return f"{text[: limit - 3]}..."


class ShopPaginationView(discord.ui.View):
    """
    Controls the paginated ENVI Commercial Exchange display.

    Only the user who opened the shop may operate its buttons.
    """

    def __init__(
        self,
        *,
        items: list[dict],
        user_id: int,
        category: str | None,
    ):
        super().__init__(timeout=SHOP_VIEW_TIMEOUT_SECONDS)

        self.items = items
        self.user_id = user_id
        self.category = category

        self.current_page = 0
        self.total_pages = max(
            1,
            math.ceil(len(self.items) / SHOP_ITEMS_PER_PAGE),
        )

        # This will be assigned after Discord sends the shop message.
        self.message = None

        self._update_button_states()

    def _get_current_page_items(self) -> list[dict]:
        """
        Returns only the items belonging to the current page.
        """

        start_index = self.current_page * SHOP_ITEMS_PER_PAGE
        end_index = start_index + SHOP_ITEMS_PER_PAGE

        return self.items[start_index:end_index]

    def _update_button_states(self) -> None:
        """
        Disables buttons that cannot currently be used.
        """

        self.previous_page.disabled = self.current_page <= 0
        self.next_page.disabled = (
            self.current_page >= self.total_pages - 1
        )

    def build_embed(self) -> discord.Embed:
        """
        Builds the shop embed for the current page.
        """

        self._update_button_states()

        title = "ENVI COMMERCIAL EXCHANGE"

        if self.category is not None:
            title = f"{title} — {self.category}"

        description_lines = [
            "Browse registered goods below.",
            "Use `/buy` and begin typing an item name to make a purchase.",
        ]

        if self.category is not None:
            description_lines.append(
                f"Current Filter: `{self.category}`"
            )

        embed = envi_embed(
            title=title,
            description="\n".join(description_lines),
        )

        for item in self._get_current_page_items():
            item_name = str(item["name"])
            item_price = format_credits(int(item["price"]))
            item_category = str(item["category"])
            item_rarity = str(item["rarity"])
            item_stock = format_stock(item["stock"])
            item_description = str(item["description"])

            # Organization-linked sellers do not exist yet.
            # This fallback remains compatible with that later V2 system.
            seller_name = str(
                item.get("seller_name")
                or "ENVI Commercial Exchange"
            )

            field_name = _shorten_text(
                f"{item_name} — {item_price}",
                EMBED_FIELD_NAME_LIMIT,
            )

            field_value = _shorten_text(
                (
                    f"Category: `{item_category}` | "
                    f"Rarity: `{item_rarity}`\n"
                    f"Stock: `{item_stock}` | "
                    f"Seller: **{seller_name}**\n"
                    f"{item_description}"
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
                f"Page {self.current_page + 1} of {self.total_pages}"
                f" • {len(self.items)} active item(s)"
                f" • 6 items per page"
            )
        )

        return embed

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Prevents other users from controlling this shop view.
        """

        if interaction.user.id == self.user_id:
            return True

        await interaction.response.send_message(
            (
                "These shop controls belong to the citizen who opened them. "
                "Use `/shop` to open your own exchange view."
            ),
            ephemeral=True,
        )

        return False

    async def on_timeout(self) -> None:
        """
        Disables the navigation buttons when the shop view expires.
        """

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        if self.message is None:
            return

        try:
            await self.message.edit(view=self)
        except (discord.NotFound, discord.HTTPException):
            # The message may have been deleted or become unavailable.
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
        Moves the shop backward by one page.
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
        Moves the shop forward by one page.
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