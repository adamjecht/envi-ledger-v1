from __future__ import annotations

from services.economy_stats_service import get_economy_stats
from utils.formatting import format_credits


DISCORD_EMBED_DESCRIPTION_LIMIT = 4096


def _format_richest_user(
    richest_user: dict | None,
) -> str:
    """
    Formats the current highest-balance citizen.
    """
    if richest_user is None:
        return "No registered citizens."

    return (
        f"**{richest_user['display_name']}** — "
        f"{format_credits(richest_user['balance'])}"
    )


def _format_richest_organization(
    richest_organization: dict | None,
) -> str:
    """
    Formats the current highest-balance organization.
    """
    if richest_organization is None:
        return "No registered organizations."

    status = (
        "Active"
        if int(richest_organization["active"]) == 1
        else "Inactive"
    )

    return (
        f"**{richest_organization['name']}** — "
        f"{format_credits(richest_organization['balance'])} "
        f"({status})"
    )


def _format_top_business(
    top_business: dict | None,
) -> str:
    """
    Formats the leading business by recorded shop sales.
    """
    if top_business is None:
        return "No commercial sales recorded."

    return (
        f"**{top_business['name']}** — "
        f"{top_business['sale_count']} sale(s), "
        f"{format_credits(top_business['sales_total'])}"
    )


def _format_signed_credits(
    amount: int,
) -> str:
    """
    Formats a signed economy difference.
    """
    if amount > 0:
        return f"+{format_credits(amount)}"

    if amount < 0:
        return f"-{format_credits(abs(amount))}"

    return format_credits(0)


def _format_net_change(
    net_change: int,
) -> str:
    """
    Adds a readable direction to net currency movement.
    """
    if net_change > 0:
        return (
            f"{format_credits(net_change)} expansion"
        )

    if net_change < 0:
        return (
            f"{format_credits(abs(net_change))} contraction"
        )

    return "neutral movement"


def _format_reconciliation(
    *,
    reconciled: bool,
    difference: int,
) -> str:
    """
    Formats one staff-safe reconciliation result.
    """
    if reconciled:
        return "Balanced"

    return (
        "Review required "
        f"({_format_signed_credits(difference)})"
    )


def _build_commerce_read(
    stats: dict,
) -> str:
    """
    Builds a concise SIN News read on commercial movement.
    """
    commercial_spending = int(
        stats["commercial_spending_total"]
    )

    institutional_payouts = int(
        stats["institutional_payout_total"]
    )

    transfer_volume = int(
        stats["transfer_volume"]
    )

    if (
        commercial_spending == 0
        and institutional_payouts == 0
        and transfer_volume == 0
    ):
        return (
            "Commercial activity remains quiet. The Exchange is open, "
            "but the city is keeping its credits close."
        )

    leading_value = max(
        commercial_spending,
        institutional_payouts,
        transfer_volume,
    )

    if leading_value == commercial_spending:
        return (
            "Commercial purchases are carrying the strongest visible "
            "movement, with business-linked goods drawing citizen spend."
        )

    if leading_value == institutional_payouts:
        return (
            "Institutional payouts are leading current movement, with "
            "organizations sending more credits back to citizens."
        )

    return (
        "Citizen transfers are carrying the strongest visible volume, "
        "suggesting private exchange is outpacing formal commerce."
    )


def _build_economic_warnings(
    stats: dict,
) -> list[str]:
    """
    Builds readable economy warnings without changing data.
    """
    warnings: list[str] = []

    if not stats["circulation_reconciled"]:
        warnings.append(
            "**Ledger Reconciliation:** Combined balances do not match "
            "recorded generation minus recorded removals."
        )

    if not stats["commercial_reconciled"]:
        warnings.append(
            "**Commercial Reconciliation:** Citizen commercial spending "
            "does not match recorded business-sale revenue."
        )

    if not stats["citation_reconciled"]:
        warnings.append(
            "**Citation Reconciliation:** Paid citation value does not "
            "match recorded fine sinks."
        )

    if int(stats["citation_open_count"]) > 0:
        warnings.append(
            "**Black Badge Exposure:** "
            f"{stats['citation_open_count']} open citation(s) remain, "
            f"valued at {format_credits(stats['citation_open_value'])}."
        )

    if int(stats["sold_out_items"]) > 0:
        warnings.append(
            "**Supply Pressure:** "
            f"{stats['sold_out_items']} active item(s) are sold out."
        )

    generated = int(
        stats["credits_generated"]
    )

    removed = int(
        stats["credits_removed"]
    )

    if generated > 0 and removed == 0:
        warnings.append(
            "**Inflation Watch:** Credits have entered circulation, but "
            "no recorded sink has removed currency yet."
        )

    elif (
        removed > 0
        and generated > removed * 2
    ):
        warnings.append(
            "**Inflation Watch:** Recorded generation is more than twice "
            "recorded removal."
        )

    if not warnings:
        warnings.append(
            "No immediate ledger, citation, commerce, or supply warnings "
            "were detected."
        )

    return warnings


def _build_stock_read(
    stats: dict,
) -> str:
    """
    Builds a short read on limited inventory pressure.
    """
    limited_stock_items = int(
        stats["limited_stock_items"]
    )

    sold_out_items = int(
        stats["sold_out_items"]
    )

    if limited_stock_items == 0:
        return (
            "No limited-stock items are currently active."
        )

    if sold_out_items == 0:
        return (
            f"{limited_stock_items} limited-stock item(s) are active, "
            "with no current sellouts."
        )

    return (
        f"{limited_stock_items} limited-stock item(s) are active, "
        f"and {sold_out_items} are already sold out."
    )


def build_economy_report() -> dict:
    """
    Builds the V2 SIN News Financial Pulse.

    The report uses the same statistics dictionary as
    `/admin economy`, so its totals remain aligned with
    the staff economy snapshot.
    """
    stats = get_economy_stats()

    richest_user_text = _format_richest_user(
        stats["richest_user"]
    )

    richest_organization_text = (
        _format_richest_organization(
            stats["richest_organization"]
        )
    )

    top_business_text = _format_top_business(
        stats["top_business"]
    )

    net_change_text = _format_net_change(
        int(stats["net_change"])
    )

    circulation_reconciliation = (
        _format_reconciliation(
            reconciled=bool(
                stats["circulation_reconciled"]
            ),
            difference=int(
                stats[
                    "circulation_reconciliation_difference"
                ]
            ),
        )
    )

    commercial_reconciliation = (
        _format_reconciliation(
            reconciled=bool(
                stats["commercial_reconciled"]
            ),
            difference=int(
                stats[
                    "commercial_reconciliation_difference"
                ]
            ),
        )
    )

    citation_reconciliation = (
        _format_reconciliation(
            reconciled=bool(
                stats["citation_reconciled"]
            ),
            difference=int(
                stats[
                    "citation_reconciliation_difference"
                ]
            ),
        )
    )

    commerce_read = _build_commerce_read(
        stats
    )

    stock_read = _build_stock_read(
        stats
    )

    warnings = _build_economic_warnings(
        stats
    )

    warning_text = "\n".join(
        f"• {warning}"
        for warning in warnings
    )

    description = (
        "**SIN News Financial Pulse**\n"
        "Presented by ENVI Ledger, courtesy of the Endless Reserve.\n\n"

        "**Headline Ledger**\n"
        f"Registered Citizens: **{stats['total_users']}**\n"
        f"Registered Organizations: **{stats['total_organizations']}**\n"
        "Citizen Balances: "
        f"**{format_credits(stats['citizen_balance_total'])}**\n"
        "Organization Balances: "
        f"**{format_credits(stats['organization_balance_total'])}**\n"
        "Total Circulation: "
        f"**{format_credits(stats['total_circulation'])}**\n\n"

        "**Market Leaders**\n"
        f"Highest Citizen Balance: {richest_user_text}\n"
        "Highest Organization Balance: "
        f"{richest_organization_text}\n"
        f"Top-Selling Business: {top_business_text}\n\n"

        "**Circulation Change**\n"
        "Credits Generated: "
        f"**{format_credits(stats['credits_generated'])}**\n"
        "Credits Removed: "
        f"**{format_credits(stats['credits_removed'])}**\n"
        f"Net Circulation Change: **{net_change_text}**\n"
        "Ledger Reconciliation: "
        f"**{circulation_reconciliation}**\n\n"

        "**Institutional & Commercial Activity**\n"
        "Commercial Purchases: "
        f"**{stats['commercial_purchase_count']}** totaling "
        f"**{format_credits(stats['commercial_spending_total'])}**\n"
        "Business Sales: "
        f"**{stats['business_sale_count']}** totaling "
        f"**{format_credits(stats['business_sales_total'])}**\n"
        "Institutional Payouts to Citizens: "
        f"**{stats['institutional_payout_count']}** totaling "
        f"**{format_credits(stats['institutional_payout_total'])}**\n"
        "System-Shop Spending: "
        f"**{format_credits(stats['system_shop_spending_total'])}**\n"
        "Citizen Transfers: "
        f"**{stats['transfer_count']}** totaling "
        f"**{format_credits(stats['transfer_volume'])}**\n"
        "Commercial Reconciliation: "
        f"**{commercial_reconciliation}**\n\n"
        f"{commerce_read}\n\n"
        "_Commercial purchases, business sales, citizen transfers, "
        "organization deposits and payments, and institutional payouts "
        "move existing credits. They are not counted as new currency._\n\n"

        "**Black Badge Collections**\n"
        "Total Citations: "
        f"**{stats['citation_total_count']}** valued at "
        f"**{format_credits(stats['citation_total_value'])}**\n"
        "Open Citations: "
        f"**{stats['citation_open_count']}** valued at "
        f"**{format_credits(stats['citation_open_value'])}**\n"
        "Fine Payments: "
        f"**{stats['fine_payment_count']}** totaling "
        f"**{format_credits(stats['fine_payment_total'])}**\n"
        "Administrative Collections: "
        f"**{stats['fine_collection_count']}** totaling "
        f"**{format_credits(stats['fine_collection_total'])}**\n"
        "Paid Citation Value: "
        f"**{format_credits(stats['citation_paid_value'])}**\n"
        "Citation Reconciliation: "
        f"**{citation_reconciliation}**\n\n"

        "**Exchange Inventory**\n"
        f"Active Shop Items: **{stats['active_shop_items']}**\n"
        f"Limited Stock Items: **{stats['limited_stock_items']}**\n"
        f"Sold Out Items: **{stats['sold_out_items']}**\n"
        "Items Held By Citizens: "
        f"**{stats['inventory_quantity_total']}**\n\n"
        f"{stock_read}\n\n"

        "**ENVI Warning Desk**\n"
        f"{warning_text}\n\n"

        "**Anchor Copy**\n"
        "The Endless Reserve reminds citizens that every indulgence has "
        "a receipt, every institution has a ledger, and every unpaid "
        "obligation eventually becomes somebody's headline."
    )

    if (
        len(description)
        > DISCORD_EMBED_DESCRIPTION_LIMIT
    ):
        raise RuntimeError(
            "The SIN News Financial Pulse exceeds "
            "Discord's embed-description limit."
        )

    return {
        "title": "SIN NEWS FINANCIAL PULSE",
        "description": description,
        "description_length": len(
            description
        ),
        "warnings": tuple(
            warnings
        ),
        "stats": stats,
    }