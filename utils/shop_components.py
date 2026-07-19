from __future__ import annotations
from collections.abc import Awaitable, Callable

import asyncio
import math

import discord

from services.shop_service import (
    format_item_seller_name,
    format_item_settlement,
)
from utils.constants import ENVI_GREEN, SHOP_CATEGORIES
from utils.formatting import format_credits

ShopPurchaseCallback = Callable[
    [discord.Interaction, dict],
    Awaitable[dict],
]

SHOP_ITEMS_PER_PAGE = 3
SHOP_SESSION_TIMEOUT_SECONDS = 300.0


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

PURCHASE_DENIED_ACCENT_COLOR = 0xED4245

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

def _format_shop_stock(
    stock: int | None,
) -> str:
    """Format stock for the customer-facing shop display."""

    if stock is None:
        return "∞ Unlimited"

    quantity = int(stock)

    if quantity <= 0:
        return "⛔ Sold Out"

    noun = "unit" if quantity == 1 else "units"

    return f"📦 {quantity:,} {noun} remaining"


def _format_shop_settlement(item: dict) -> str:
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

    stock_text = _format_shop_stock(item["stock"])
    seller_name = format_item_seller_name(item)
    settlement = _format_shop_settlement(item)

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
        shop_view: ShopComponentsView,
    ):
        self.shop_view = shop_view

        super().__init__(
            custom_id="envi_shop_category",
            placeholder=(
                shop_view.current_category
                or "All Categories"
            ),
            options=shop_view.build_category_options(),
            min_values=1,
            max_values=1,
            disabled=(
                shop_view.session_expired
                or shop_view.purchase_in_progress
            ),
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
        self.shop_view.clear_selection()
        self.shop_view.rebuild()

        await interaction.response.edit_message(
            view=self.shop_view,
        )


class ShopPreviousButton(discord.ui.Button):
    """Move one page backward."""

    def __init__(
        self,
        shop_view: ShopComponentsView,
        *,
        disabled: bool,
    ):
        self.shop_view = shop_view

        super().__init__(
            custom_id="envi_shop_previous",
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

        self.shop_view.clear_selection()
        self.shop_view.rebuild()

        await interaction.response.edit_message(
            view=self.shop_view,
        )


class ShopNextButton(discord.ui.Button):
    """Move one page forward."""

    def __init__(
        self,
        shop_view: ShopComponentsView,
        *,
        disabled: bool,
    ):
        self.shop_view = shop_view

        super().__init__(
            custom_id="envi_shop_next",
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

        self.shop_view.clear_selection()
        self.shop_view.rebuild()

        await interaction.response.edit_message(
            view=self.shop_view,
        )

class ShopItemSelect(discord.ui.Select):
    """Select one visible item for a purchase dry run."""

    def __init__(
        self,
        shop_view: ShopComponentsView,
        *,
        visible_items: list[dict],
    ):
        self.shop_view = shop_view

        purchasable_items = [
            item
            for item in visible_items
            if (
                item.get("stock") is None
                or int(item["stock"]) > 0
            )
        ]

        options = [
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
                default=(
                    shop_view.selected_item_id
                    == int(item["item_id"])
                ),
            )
            for item in purchasable_items
        ]

        if not options:
            options = [
                discord.SelectOption(
                    label="No purchasable items",
                    value="none",
                    description=(
                        "Every item on this page is sold out."
                    ),
                )
            ]

        super().__init__(
            custom_id="envi_shop_item",
            placeholder="Choose one visible item",
            options=options,
            min_values=1,
            max_values=1,
            disabled=(
                not purchasable_items
                or shop_view.session_expired
                or shop_view.purchase_in_progress
            ),
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        selected_value = self.values[0]

        if selected_value == "none":
            await interaction.response.send_message(
                "No purchasable item is available on this page.",
                ephemeral=True,
            )
            return

        self.shop_view.selected_item_id = int(
            selected_value
        )
        self.shop_view.purchase_result_text = None
        self.shop_view.purchase_result_accent_color = None
        self.shop_view.rebuild()

        await interaction.response.edit_message(
            view=self.shop_view,
        )

class ShopPurchaseButton(discord.ui.Button):
    """Purchase one selected item through the shared economy pipeline."""

    def __init__(
        self,
        shop_view: ShopComponentsView,
        *,
        disabled: bool,
    ):
        self.shop_view = shop_view

        super().__init__(
            custom_id="envi_shop_purchase",
            label="Buy 1",
            emoji="🛒",
            style=discord.ButtonStyle.success,
            disabled=disabled,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        selected_item = self.shop_view.get_selected_item()

        if selected_item is None:
            await interaction.response.send_message(
                "Select one visible shop item first.",
                ephemeral=True,
            )
            return

        if self.shop_view.session_expired:
            await interaction.response.send_message(
                "This ENVI shop session has expired. "
                "Run `/shop` to open a new one.",
                ephemeral=True,
            )
            return

        if self.shop_view.purchase_lock.locked():
            await interaction.response.send_message(
                "ENVI is already processing this purchase.",
                ephemeral=True,
            )
            return

        selected_snapshot = dict(selected_item)

        async with self.shop_view.purchase_lock:
            self.shop_view.purchase_in_progress = True
            self.shop_view.rebuild()

            await interaction.response.edit_message(
                view=self.shop_view,
            )

            try:
                outcome = (
                    await self.shop_view.purchase_callback(
                        interaction,
                        selected_snapshot,
                    )
                )
            except Exception:
                self.shop_view.purchase_in_progress = False
                self.shop_view.selected_item_id = None
                self.shop_view.purchase_result_text = (
                    "### ⚠️ PURCHASE ERROR\n"
                    "An unexpected error interrupted the "
                    "storefront response. Verify your balance "
                    "and inventory before trying again.\n\n"
                    "-# The purchase service may have completed"
                    " · Check ENVI staff logs"
                )
                self.shop_view.purchase_result_accent_color = (
                    PURCHASE_DENIED_ACCENT_COLOR
                )
                self.shop_view.rebuild()

                await interaction.edit_original_response(
                    view=self.shop_view,
                )
                raise

            self.shop_view.purchase_in_progress = False
            self.shop_view.apply_purchase_outcome(
                outcome
            )
            self.shop_view.rebuild()

            await interaction.edit_original_response(
                view=self.shop_view,
            )

class ShopComponentsView(discord.ui.LayoutView):
    """
    Interactive Components V2 storefront for the ENVI shop.

    The view supports category filtering, pagination, one-unit
    purchases, refreshed catalog state, session ownership, duplicate
    purchase protection, and session expiration.
    """

    def __init__(
        self,
        *,
        items: list[dict],
        user_id: int,
        balance: int,
        thumbnail_url: str,
        purchase_callback: ShopPurchaseCallback,
    ):
        super().__init__(
            timeout=SHOP_SESSION_TIMEOUT_SECONDS,
        )

        self.user_id = user_id
        self.items = items
        self.balance = balance
        self.thumbnail_url = thumbnail_url
        self.purchase_callback = purchase_callback

        self.current_category: str | None = None
        self.current_page = 0
        self.selected_item_id: int | None = None
        self.purchase_result_text: str | None = None
        self.purchase_result_accent_color: int | None = None
        self.purchase_in_progress = False
        self.purchase_lock = asyncio.Lock()
        self.session_expired = False
        self.message = None

        self.rebuild()

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        """Restrict the shop session to its owner."""

        if self.session_expired:
            await interaction.response.send_message(
                "This ENVI shop session has expired. "
                "Run `/shop` to open a new one.",
                ephemeral=True,
            )
            return False

        if interaction.user.id == self.user_id:
            return True

        await interaction.response.send_message(
            "This ENVI shop session belongs to another user.",
            ephemeral=True,
        )
        return False

    async def on_timeout(self) -> None:
        """Expire the session and disable its controls."""

        self.session_expired = True
        self.purchase_in_progress = False
        self.selected_item_id = None
        self.rebuild()

        if self.message is None:
            return

        try:
            await self.message.edit(
                view=self,
            )
        except discord.HTTPException:
            pass

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
                / SHOP_ITEMS_PER_PAGE
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
            * SHOP_ITEMS_PER_PAGE
        )
        end_index = (
            start_index
            + SHOP_ITEMS_PER_PAGE
        )

        return filtered_items[start_index:end_index]

    def clear_selection(self) -> None:
        """Clear the selected item and purchase result."""

        self.selected_item_id = None
        self.purchase_result_text = None
        self.purchase_result_accent_color = None

    def refresh_catalog_state(
        self,
        *,
        items: list[dict],
        balance: int,
    ) -> None:
        """Apply fresh post-purchase catalog and balance data."""

        self.items = list(items)
        self.balance = int(balance)

        present_categories = {
            str(item["category"])
            for item in self.items
        }

        if (
            self.current_category is not None
            and self.current_category
            not in present_categories
        ):
            self.current_category = None
            self.current_page = 0

        self.current_page = min(
            self.current_page,
            self.get_total_pages() - 1,
        )

    def build_purchase_success_text(
        self,
        result: dict,
    ) -> str:
        """Build the customer-facing successful purchase result."""

        item = result["item"]
        seller_name = format_item_seller_name(item)
        settlement = _format_shop_settlement(item)
        remaining_stock = _format_shop_stock(
            result["remaining_stock"]
        )

        return (
            "### ✅ PURCHASE CONFIRMED\n"
            f"**Item:** {item['name']}\n"
            f"**Total:** "
            f"{format_credits(result['total_price'])}\n"
            f"**Seller:** {seller_name}\n"
            f"**Settlement:** {settlement}\n"
            f"**Updated Balance:** "
            f"{format_credits(result['user']['balance'])}\n"
            f"**Inventory Quantity:** "
            f"{result['inventory_quantity']}\n"
            f"**Stock Remaining:** {remaining_stock}\n"
            f"**Reference:** `{result['reference_id']}`\n\n"
            "-# One unit purchased"
            " · Multiple quantities: `/buy`"
        )

    def build_purchase_denied_text(
        self,
        message: str,
    ) -> str:
        """Build the customer-facing purchase denial result."""

        return (
            "### ⛔ PURCHASE DENIED\n"
            f"{message}\n\n"
            "-# No successful purchase was returned"
        )

    def apply_purchase_outcome(
        self,
        outcome: dict,
    ) -> None:
        """Apply refreshed state and render a purchase result."""

        self.refresh_catalog_state(
            items=outcome["items"],
            balance=int(outcome["balance"]),
        )

        self.selected_item_id = None

        if bool(outcome["success"]):
            self.purchase_result_text = (
                self.build_purchase_success_text(
                    outcome["result"]
                )
            )
            self.purchase_result_accent_color = (
                ENVI_GREEN
            )
            return

        self.purchase_result_text = (
            self.build_purchase_denied_text(
                str(outcome["message"])
            )
        )
        self.purchase_result_accent_color = (
            PURCHASE_DENIED_ACCENT_COLOR
        )

    def get_selected_item(self) -> dict | None:
        """Return the selected item if it is still visible."""

        if self.selected_item_id is None:
            return None

        for item in self.get_visible_items():
            if (
                int(item["item_id"])
                == self.selected_item_id
            ):
                return item

        return None


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

        purchase_select = ShopItemSelect(
            self,
            visible_items=visible_items,
        )

        self.add_item(
            discord.ui.ActionRow(
                purchase_select
            )
        )

        selected_item = self.get_selected_item()

        previous_button = ShopPreviousButton(
            self,
            disabled=(
                self.current_page == 0
                or self.session_expired
                or self.purchase_in_progress
            ),
        )

        purchase_button = ShopPurchaseButton(
            self,
            disabled=(
                selected_item is None
                or self.session_expired
                or self.purchase_in_progress
            ),
        )

        next_button = ShopNextButton(
            self,
            disabled=(
                self.current_page
                >= total_pages - 1
                or self.session_expired
                or self.purchase_in_progress
            ),
        )

        self.add_item(
            discord.ui.ActionRow(
                previous_button,
                purchase_button,
                next_button,
            )
        )

        if self.purchase_result_text is not None:
            self.add_item(
                discord.ui.Container(
                    discord.ui.TextDisplay(
                        self.purchase_result_text
                    ),
                    accent_color=(
                        self.purchase_result_accent_color
                        or ENVI_GREEN
                    ),
                )
            )

        if self.session_expired:
            footer_text = (
                "-# Shop session expired"
                " · Run `/shop` to reopen"
            )
        elif self.purchase_in_progress:
            footer_text = (
                "-# ENVI is processing your purchase"
                " · Controls are temporarily locked"
            )
        else:
            footer_text = (
                "-# Browsing active"
                " · Buy 1 purchases immediately"
                " · Multiple units: `/buy`"
            )

        self.add_item(
            discord.ui.TextDisplay(
                footer_text
            )
        )