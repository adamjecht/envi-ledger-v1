from services.economy_stats_service import get_economy_stats
from utils.formatting import format_credits


def _format_richest_user(richest_user: dict | None) -> str:
    """
    Formats the current highest-balance citizen for report text.
    """

    if richest_user is None:
        return "No registered citizens yet."

    return (
        f"{richest_user['display_name']} "
        f"with {format_credits(richest_user['balance'])}"
    )


def _format_net_change(net_change: int) -> str:
    """
    Adds a readable direction label to net economy movement.
    """

    if net_change > 0:
        return f"{format_credits(net_change)} expansion"

    if net_change < 0:
        return f"{format_credits(abs(net_change))} contraction"

    return "neutral movement"


def _build_commerce_read(stats: dict) -> str:
    """
    Builds a short SIN News-style read on shop and transfer activity.
    """

    if stats["shop_purchase_count"] == 0 and stats["transfer_count"] == 0:
        return (
            "Commercial activity remains quiet, with citizens still watching "
            "the exchange before committing their credits."
        )

    if stats["shop_spending_total"] > stats["transfer_volume"]:
        return (
            "The Commercial Exchange is currently driving more visible money "
            "movement than citizen-to-citizen transfers."
        )

    if stats["transfer_volume"] > stats["shop_spending_total"]:
        return (
            "Citizen transfers are carrying more volume than direct shop "
            "spending, suggesting private deals and social payments are active."
        )

    return (
        "Shop spending and citizen transfers are moving at a similar pace, "
        "keeping the ledger balanced between public commerce and private exchange."
    )


def _build_stock_read(stats: dict) -> str:
    """
    Builds a short read on limited stock and sold-out items.
    """

    if stats["limited_stock_items"] == 0:
        return (
            "No limited-stock items are currently active, leaving the exchange "
            "open and stable."
        )

    if stats["sold_out_items"] == 0:
        return (
            f"{stats['limited_stock_items']} limited-stock item(s) are active, "
            "but none have sold out yet."
        )

    return (
        f"{stats['limited_stock_items']} limited-stock item(s) are active, "
        f"with {stats['sold_out_items']} already sold out."
    )


def build_economy_report() -> dict:
    """
    Builds a SIN News Financial Pulse report from current economy stats.
    """

    stats = get_economy_stats()

    richest_text = _format_richest_user(stats["richest_user"])
    net_change_text = _format_net_change(stats["net_change"])
    commerce_read = _build_commerce_read(stats)
    stock_read = _build_stock_read(stats)

    description = (
        "**SIN News Financial Pulse**\n"
        "Presented by ENVI Ledger, courtesy of the Endless Reserve.\n\n"
        "**Top Line**\n"
        f"The Nexus economy currently tracks **{stats['total_users']}** "
        f"registered citizen account(s), with "
        f"**{format_credits(stats['total_credits'])}** in circulation.\n\n"
        "**Highest Balance**\n"
        f"The current highest recorded balance belongs to **{richest_text}**.\n\n"
        "**Credit Flow**\n"
        f"Credits Generated: **{format_credits(stats['credits_generated'])}**\n"
        f"Credits Removed: **{format_credits(stats['credits_removed'])}**\n"
        f"Net Movement: **{net_change_text}**\n\n"
        "**Commerce Watch**\n"
        f"Shop Purchases: **{stats['shop_purchase_count']}**\n"
        f"Shop Spending: **{format_credits(stats['shop_spending_total'])}**\n"
        f"Citizen Transfers: **{stats['transfer_count']}**\n"
        f"Transfer Volume: **{format_credits(stats['transfer_volume'])}**\n\n"
        f"{commerce_read}\n\n"
        "**Exchange Inventory**\n"
        f"Active Shop Items: **{stats['active_shop_items']}**\n"
        f"Limited Stock Items: **{stats['limited_stock_items']}**\n"
        f"Sold Out Items: **{stats['sold_out_items']}**\n"
        f"Items Held By Citizens: **{stats['inventory_quantity_total']}**\n\n"
        f"{stock_read}\n\n"
        "**Anchor Copy**\n"
        "The Endless Reserve reminds citizens that every indulgence has a "
        "receipt, every receipt has a ledger entry, and ENVI is always very, "
        "very good at counting."
    )

    return {
        "title": "SIN NEWS FINANCIAL PULSE",
        "description": description,
        "stats": stats,
    }