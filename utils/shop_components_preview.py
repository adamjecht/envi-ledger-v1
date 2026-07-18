from __future__ import annotations

import math

import discord

from services.shop_service import (
    format_item_seller_name,
    format_item_settlement,
    format_stock,
)
from utils.constants import ENVI_GREEN, SHOP_CATEGORIES
from utils.formatting import format_credits


SHOP_PREVIEW_ITEMS_PER_PAGE = 3
SHOP_PREVIEW_TIMEOUT_SECONDS = 300.0


RARITY_SYMBOLS: dict[str, str] = {
    "common": "◇",
    "uncommon": "◆",
    "rare": "✦",
    "luxury": "✧",
    "restricted": "⬢",
    "exordium-class": "✹",
}


RARITY_ACCENT_COLORS: dict[str, int] = {
    "common": 0x95A5A6,
    "uncommon": ENVI_GREEN,
    "rare": 0x3498DB,
    "luxury": 0x9B59B6,
    "restricted": 0xE74C3C,
    "exordium-class": 0xF1C40F,
}


CATEGORY_EMOJIS: dict[str, str] = {
    "Access Passes": "🎫",
    "Black Badge / Civic": "🛡️",
    "Collectibles": "🏺",
    "Eclipse Items": "🍸",
    "Event Items": "🎟️",
    "Food & Drink": "🥂",
    "General": "📦",
    "Luxury": "💎",
    "Obsession Items": "🌹",
    "Transit": "🚆",
}


def _shorten_text(text: str, limit: int) -> str:
    """Shorten text without exceeding Discord component limits."""

    if len(text) <= limit:
        return text

    return f"{text[: limit - 3]}..."


def _get_item_emoji(item: dict) -> str:
    """Choose a readable emoji for an item's title."""

    item_name = str(item["name"]).casefold()
    category = str(item["category"])

    if "handbook" in item_name or "journal" in item_name:
        return "📖"

    if "mug" in item_name or "tumbler" in item_name:
        return "☕"

    if "recovery kit" in item_name:
        return "🩹"

    if "candle" in item_name:
        return "🕯️"

    if "token" in item_name or "pass" in item_name or "ticket" in item_name:
        return "🎫"

    return CATEGORY_EMOJIS.get(category, "🛍️")


def _get_rarity_symbol(rarity: str) -> str:
    """Return the compact symbol assigned to one rarity."""

    return RARITY_SYMBOLS.get(rarity.casefold(), "◇")


def _get_rarity_accent_color(rarity: str) -> int:
    """Return the Container accent color assigned to one rarity."""

    return RARITY_ACCENT_COLORS.get(
        rarity.casefold(),
        0x95A5A6,
    )

def _format_preview_stock(stock: int | None) -> str:
    """Format stock for the customer-facing shop display."""

    if stock is None:
        return "∞ Unlimited"

    quantity = int(stock)
    noun = "unit" if quantity == 1 else "units"

    return f"📦 {quantity:,} {noun} remaining"


def _format_preview_settlement(item: dict) -> str:
    """Shorten internal settlement terminology for shop customers."""

    settlement = str(format_item_settlement(item))
    normalized = settlement.casefold()

    if "organization" in normalized and "revenue" in normalized:
        return "Seller Revenue"

    if "system" in normalized and "sink" in normalized:
        return "System Sink"

    return settlement

def _build_item_text(item: dict) -> str:
    """Build one compact Components V2 shop listing."""

    item_name = str(item["name"])
    item_price = format_credits(int(item["price"]))
    item_category = str(item["category"])
    item_rarity = str(item["rarity"])
    item_description = str(item["description"])

    item_emoji = _get_item_emoji(item)
    rarity_symbol = _get_rarity_symbol(item_rarity)

    stock_text = _format_preview_stock(item["stock"])
    seller_name = format_item_seller_name(item)
    settlement = _format_preview_settlement(item)

    return (
        f"### {item_emoji} {item_name}\n"
        f"💳 **{item_price}**\n"
        f"{rarity_symbol} `{item_rarity.upper()}`"
        f" · 🏷️ `{item_category.upper()}`\n"
        f"{item_description}\n\n"
        f"-# {stock_text}\n"
        f"-# 🏛️ {seller_name}\n"
        f"-# 💳 {settlement}"
    )


class ShopCategorySelect(discord.ui.Select):
    """Category filter belonging to one shop preview."""

    def __init__(
        self,
        shop_view: ShopComponentsPreview,
    ):
        self.shop_view = shop_view

        super().__init__(
            custom_id="envi_shop_preview_category",
            placeholder=(
                shop_view.current_category
                or "All Categories"
            ),
            options=shop_view.build_category_options(),
            min_values=1,
            max_values=1,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        selected_value = self.values[0]

        if selected_value == "all":
            self.shop_view.current_category = None
        else:
            self.shop_view.current_category = selected_value

        self.shop_view.current_page = 0
        self.shop_view.rebuild()

        await interaction.response.edit_message(
            view=self.shop_view,
        )


class ShopPreviousButton(discord.ui.Button):
    """Move one page backward."""

    def __init__(
        self,
        shop_view: ShopComponentsPreview,
        *,
        disabled: bool,
    ):
        self.shop_view = shop_view

        super().__init__(
            custom_id="envi_shop_preview_previous",
            label="Prev",
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if self.shop_view.current_page > 0:
            self.shop_view.current_page -= 1

        self.shop_view.rebuild()

        await interaction.response.edit_message(
            view=self.shop_view,
        )


class ShopNextButton(discord.ui.Button):
    """Move one page forward."""

    def __init__(
        self,
        shop_view: ShopComponentsPreview,
        *,
        disabled: bool,
    ):
        self.shop_view = shop_view

        super().__init__(
            custom_id="envi_shop_preview_next",
            label="Next",
            emoji="▶️",
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        total_pages = self.shop_view.get_total_pages()

        if self.shop_view.current_page < total_pages - 1:
            self.shop_view.current_page += 1

        self.shop_view.rebuild()

        await interaction.response.edit_message(
            view=self.shop_view,
        )


class ShopComponentsPreview(discord.ui.LayoutView):
    """
    Interactive Components V2 browsing preview.

    Category filtering and pagination are active.

    Purchasing remains intentionally disabled. This preview performs no
    purchases, inventory changes, stock changes, balance changes, or
    transaction logging.
    """

    def __init__(
        self,
        *,
        items: list[dict],
        user_id: int,
        balance: int,
        thumbnail_url: str,
    ):
        super().__init__(
            timeout=SHOP_PREVIEW_TIMEOUT_SECONDS,
        )

        self.user_id = user_id
        self.items = items
        self.balance = balance
        self.thumbnail_url = thumbnail_url

        self.current_category: str | None = None
        self.current_page = 0

        self.rebuild()

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """
        Restrict this preview to the user who opened it.

        The response is currently ephemeral, but the explicit check keeps
        the view safe if its delivery behavior changes later.
        """

        if interaction.user.id == self.user_id:
            return True

        await interaction.response.send_message(
            "This ENVI shop session belongs to another user.",
            ephemeral=True,
        )
        return False

    def get_filtered_items(self) -> list[dict]:
        """Return active items matching the selected category."""

        if self.current_category is None:
            return self.items

        return [
            item
            for item in self.items
            if str(item["category"]) == self.current_category
        ]

    def get_total_pages(self) -> int:
        """Return the number of pages in the current filter."""

        filtered_items = self.get_filtered_items()

        return max(
            1,
            math.ceil(
                len(filtered_items)
                / SHOP_PREVIEW_ITEMS_PER_PAGE
            ),
        )

    def get_visible_items(self) -> list[dict]:
        """Return the three items shown on the current page."""

        filtered_items = self.get_filtered_items()
        total_pages = self.get_total_pages()

        self.current_page = min(
            max(self.current_page, 0),
            total_pages - 1,
        )

        start_index = (
            self.current_page
            * SHOP_PREVIEW_ITEMS_PER_PAGE
        )
        end_index = (
            start_index
            + SHOP_PREVIEW_ITEMS_PER_PAGE
        )

        return filtered_items[start_index:end_index]

    def build_category_options(
        self,
    ) -> list[discord.SelectOption]:
        """Build category choices from the real active catalog."""

        present_categories = {
            str(item["category"])
            for item in self.items
        }

        ordered_categories = [
            category
            for category in SHOP_CATEGORIES
            if category in present_categories
        ]

        unknown_categories = sorted(
            present_categories
            - set(ordered_categories)
        )

        ordered_categories.extend(unknown_categories)

        options = [
            discord.SelectOption(
                label="All Categories",
                value="all",
                description="Display the complete active catalog.",
                emoji="🏷️",
                default=self.current_category is None,
            )
        ]

        for category in ordered_categories:
            options.append(
                discord.SelectOption(
                    label=_shorten_text(category, 100),
                    value=category,
                    emoji=CATEGORY_EMOJIS.get(
                        category,
                        "📦",
                    ),
                    default=(
                        category == self.current_category
                    ),
                )
            )

        return options[:25]

    def build_header_text(
        self,
        *,
        filtered_count: int,
        total_pages: int,
    ) -> str:
        """Build the current shop header and page summary."""

        if self.current_category is None:
            page_summary = (
                f"{len(self.items)} active item(s)"
                f" · Page {self.current_page + 1}"
                f" of {total_pages}"
            )
        else:
            page_summary = (
                f"{filtered_count} matching item(s)"
                f" · Page {self.current_page + 1}"
                f" of {total_pages}"
                f" · {len(self.items)} active total"
            )

        return (
            "## 🛒 ENVI COMMERCIAL EXCHANGE\n"
            "Browse registered goods.\n"
            "Select an item below to purchase **one unit**.\n"
            "Use `/buy` when purchasing multiple units.\n\n"
            f"💳 **Available Balance:** "
            f"{format_credits(self.balance)}\n"
            f"-# {page_summary}"
        )

    def rebuild(self) -> None:
        """Rebuild the complete Components V2 layout."""

        self.clear_items()

        filtered_items = self.get_filtered_items()
        total_pages = self.get_total_pages()
        visible_items = self.get_visible_items()

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    self.build_header_text(
                        filtered_count=len(filtered_items),
                        total_pages=total_pages,
                    )
                ),
                accent_color=ENVI_GREEN,
            )
        )

        self.add_item(
            discord.ui.ActionRow(
                ShopCategorySelect(self)
            )
        )

        for item in visible_items:
            item_rarity = str(item["rarity"])

            item_section = discord.ui.Section(
                discord.ui.TextDisplay(
                    _build_item_text(item)
                ),
                accessory=discord.ui.Thumbnail(
                    self.thumbnail_url,
                    description=(
                        "Temporary ENVI artwork placeholder for "
                        f"{str(item['name'])}."
                    ),
                ),
            )

            self.add_item(
                discord.ui.Container(
                    item_section,
                    accent_color=(
                        _get_rarity_accent_color(
                            item_rarity
                        )
                    ),
                )
            )

        purchase_options = [
            discord.SelectOption(
                label=_shorten_text(
                    str(item["name"]),
                    100,
                ),
                value=str(item["item_id"]),
                description=_shorten_text(
                    format_credits(
                        int(item["price"])
                    ),
                    100,
                ),
                emoji=_get_item_emoji(item),
            )
            for item in visible_items
        ]

        purchase_select = discord.ui.Select(
            custom_id="envi_shop_preview_item",
            placeholder=(
                "Choose an item — purchasing disabled"
            ),
            options=purchase_options,
            min_values=1,
            max_values=1,
            disabled=True,
        )

        self.add_item(
            discord.ui.ActionRow(purchase_select)
        )

        previous_button = ShopPreviousButton(
            self,
            disabled=self.current_page == 0,
        )

        purchase_button = discord.ui.Button(
            custom_id="envi_shop_preview_purchase",
            label="Buy 1",
            emoji="🛒",
            style=discord.ButtonStyle.success,
            disabled=True,
        )

        next_button = ShopNextButton(
            self,
            disabled=(
                self.current_page >= total_pages - 1
            ),
        )

        self.add_item(
            discord.ui.ActionRow(
                previous_button,
                purchase_button,
                next_button,
            )
        )

        self.add_item(
            discord.ui.TextDisplay(
                "-# Browsing controls are active"
                " · Buy 1 remains disabled"
                " · Use `/buy` for multiple units"
            )
        )