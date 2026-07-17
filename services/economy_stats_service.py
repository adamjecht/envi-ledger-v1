from __future__ import annotations

import sqlite3

from db.database import get_connection

from utils.constants import (
    CITATION_STATUS_OPEN,
    CITATION_STATUS_PAID,
    CITATION_STATUS_VOID,
    ORGANIZATION_TRANSACTION_ADMIN_BALANCE_SET,
    ORGANIZATION_TRANSACTION_ADMIN_REVENUE,
    ORGANIZATION_TRANSACTION_SHOP_SALE,
    ORGANIZATION_TRANSACTION_USER_PAYMENT,
    ORGANIZATION_TYPE_BUSINESS,
    TRANSACTION_ADMIN_ADD,
    TRANSACTION_ADMIN_REMOVE,
    TRANSACTION_ADMIN_RESET,
    TRANSACTION_ADMIN_SET,
    TRANSACTION_COMMERCIAL_SHOP_PURCHASE,
    TRANSACTION_DAILY,
    TRANSACTION_FINE_COLLECTION,
    TRANSACTION_FINE_PAYMENT,
    TRANSACTION_SHOP_PURCHASE,
    TRANSACTION_TRANSFER_SENT,
    TRANSACTION_WORK,
)


PERSONAL_CREDIT_GENERATING_TYPES = (
    TRANSACTION_DAILY,
    TRANSACTION_WORK,
    TRANSACTION_ADMIN_ADD,
    TRANSACTION_ADMIN_SET,
    TRANSACTION_ADMIN_RESET,
)

PERSONAL_ADMIN_REMOVING_TYPES = (
    TRANSACTION_ADMIN_REMOVE,
    TRANSACTION_ADMIN_SET,
    TRANSACTION_ADMIN_RESET,
)


def _first_value(
    row: sqlite3.Row | None,
    default: int = 0,
) -> int:
    """
    Safely extracts the first value from a SQLite row.
    """
    if row is None:
        return default

    value = row[0]

    if value is None:
        return default

    return int(value)


def _aggregate_personal_transactions(
    *,
    connection: sqlite3.Connection,
    transaction_types: tuple[str, ...],
    positive: bool,
) -> tuple[int, int]:
    """
    Returns a transaction count and absolute credit value.

    Positive records represent generated credits.
    Negative records represent removed credits.
    """
    if not transaction_types:
        return (0, 0)

    placeholders = ",".join(
        "?"
        for _ in transaction_types
    )

    amount_condition = (
        "amount > 0"
        if positive
        else "amount < 0"
    )

    value_expression = (
        "amount"
        if positive
        else "ABS(amount)"
    )

    row = connection.execute(
        f"""
        SELECT
            COUNT(*) AS transaction_count,
            COALESCE(
                SUM({value_expression}),
                0
            ) AS credit_total
        FROM transactions
        WHERE
            type IN ({placeholders})
            AND {amount_condition}
        """,
        transaction_types,
    ).fetchone()

    return (
        int(row["transaction_count"]),
        int(row["credit_total"]),
    )


def _aggregate_organization_transactions(
    *,
    connection: sqlite3.Connection,
    transaction_types: tuple[str, ...],
    positive: bool,
) -> tuple[int, int]:
    """
    Returns organization-ledger count and credit value.

    Only explicitly generated or removed organization
    transaction types should be passed here. Transfers,
    deposits, payouts, and sales are internal circulation.
    """
    if not transaction_types:
        return (0, 0)

    placeholders = ",".join(
        "?"
        for _ in transaction_types
    )

    amount_condition = (
        "amount > 0"
        if positive
        else "amount < 0"
    )

    value_expression = (
        "amount"
        if positive
        else "ABS(amount)"
    )

    row = connection.execute(
        f"""
        SELECT
            COUNT(*) AS transaction_count,
            COALESCE(
                SUM({value_expression}),
                0
            ) AS credit_total
        FROM organization_transactions
        WHERE
            transaction_type IN ({placeholders})
            AND {amount_condition}
        """,
        transaction_types,
    ).fetchone()

    return (
        int(row["transaction_count"]),
        int(row["credit_total"]),
    )


def _account_summary(
    row: sqlite3.Row | None,
) -> dict | None:
    """
    Converts one richest-citizen row into a dictionary.
    """
    if row is None:
        return None

    return {
        "user_id": int(
            row["user_id"]
        ),
        "display_name": str(
            row["display_name"]
        ),
        "balance": int(
            row["balance"]
        ),
    }


def _organization_summary(
    row: sqlite3.Row | None,
) -> dict | None:
    """
    Converts one organization metric row into a dictionary.
    """
    if row is None:
        return None

    result = {
        "organization_id": int(
            row["organization_id"]
        ),
        "name": str(
            row["name"]
        ),
        "organization_type": str(
            row["organization_type"]
        ),
        "balance": int(
            row["balance"]
        ),
        "active": int(
            row["active"]
        ),
    }

    if "sale_count" in row.keys():
        result["sale_count"] = int(
            row["sale_count"]
        )

    if "sales_total" in row.keys():
        result["sales_total"] = int(
            row["sales_total"]
        )

    return result


def get_economy_stats() -> dict:
    """
    Builds a complete staff-facing economy snapshot.

    External generation and removal are separated from
    internal circulation:

    External generation:
    - Daily and work rewards
    - Personal administrative additions/corrections
    - Organization administrative revenue
    - Positive organization balance corrections

    External removal:
    - System-owned shop purchases
    - Personal administrative removals/corrections
    - Fine payments and administrative collections
    - Negative organization balance corrections

    Internal circulation:
    - User transfers
    - Organization deposits
    - Organization payments
    - Organization-to-organization transfers
    - Commercial shop purchases and business sales
    """
    with get_connection() as connection:
        # --------------------------------------------------
        # Citizen and organization account balances
        # --------------------------------------------------

        total_users = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM users
                """
            ).fetchone()
        )

        citizen_balance_total = _first_value(
            connection.execute(
                """
                SELECT COALESCE(
                    SUM(balance),
                    0
                )
                FROM users
                """
            ).fetchone()
        )

        richest_user_row = connection.execute(
            """
            SELECT
                user_id,
                display_name,
                balance
            FROM users
            ORDER BY
                balance DESC,
                display_name COLLATE NOCASE ASC,
                user_id ASC
            LIMIT 1
            """
        ).fetchone()

        total_organizations = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM organizations
                """
            ).fetchone()
        )

        active_organizations = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM organizations
                WHERE active = 1
                """
            ).fetchone()
        )

        inactive_organizations = (
            total_organizations
            - active_organizations
        )

        business_organizations = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM organizations
                WHERE organization_type = ?
                """,
                (
                    ORGANIZATION_TYPE_BUSINESS,
                ),
            ).fetchone()
        )

        organization_balance_total = _first_value(
            connection.execute(
                """
                SELECT COALESCE(
                    SUM(balance),
                    0
                )
                FROM organizations
                """
            ).fetchone()
        )

        richest_organization_row = (
            connection.execute(
                """
                SELECT
                    organization_id,
                    name,
                    organization_type,
                    balance,
                    active
                FROM organizations
                ORDER BY
                    balance DESC,
                    name COLLATE NOCASE ASC,
                    organization_id ASC
                LIMIT 1
                """
            ).fetchone()
        )

        total_circulation = (
            citizen_balance_total
            + organization_balance_total
        )

        # --------------------------------------------------
        # External credit generation
        # --------------------------------------------------

        (
            personal_generation_count,
            personal_credits_generated,
        ) = _aggregate_personal_transactions(
            connection=connection,
            transaction_types=(
                PERSONAL_CREDIT_GENERATING_TYPES
            ),
            positive=True,
        )

        (
            organization_revenue_count,
            organization_revenue_generated,
        ) = _aggregate_organization_transactions(
            connection=connection,
            transaction_types=(
                ORGANIZATION_TRANSACTION_ADMIN_REVENUE,
            ),
            positive=True,
        )

        (
            organization_balance_generation_count,
            organization_balance_generated,
        ) = _aggregate_organization_transactions(
            connection=connection,
            transaction_types=(
                ORGANIZATION_TRANSACTION_ADMIN_BALANCE_SET,
            ),
            positive=True,
        )

        organization_generation_count = (
            organization_revenue_count
            + organization_balance_generation_count
        )

        organization_credits_generated = (
            organization_revenue_generated
            + organization_balance_generated
        )

        total_generation_count = (
            personal_generation_count
            + organization_generation_count
        )

        total_credits_generated = (
            personal_credits_generated
            + organization_credits_generated
        )

        # --------------------------------------------------
        # External credit removal
        # --------------------------------------------------

        (
            system_shop_sink_count,
            system_shop_sink_total,
        ) = _aggregate_personal_transactions(
            connection=connection,
            transaction_types=(
                TRANSACTION_SHOP_PURCHASE,
            ),
            positive=False,
        )

        (
            personal_admin_removal_count,
            personal_admin_removal_total,
        ) = _aggregate_personal_transactions(
            connection=connection,
            transaction_types=(
                PERSONAL_ADMIN_REMOVING_TYPES
            ),
            positive=False,
        )

        (
            fine_payment_count,
            fine_payment_total,
        ) = _aggregate_personal_transactions(
            connection=connection,
            transaction_types=(
                TRANSACTION_FINE_PAYMENT,
            ),
            positive=False,
        )

        (
            fine_collection_count,
            fine_collection_total,
        ) = _aggregate_personal_transactions(
            connection=connection,
            transaction_types=(
                TRANSACTION_FINE_COLLECTION,
            ),
            positive=False,
        )

        fine_sink_count = (
            fine_payment_count
            + fine_collection_count
        )

        fine_sink_total = (
            fine_payment_total
            + fine_collection_total
        )

        personal_removal_count = (
            system_shop_sink_count
            + personal_admin_removal_count
            + fine_sink_count
        )

        personal_credits_removed = (
            system_shop_sink_total
            + personal_admin_removal_total
            + fine_sink_total
        )

        (
            organization_removal_count,
            organization_credits_removed,
        ) = _aggregate_organization_transactions(
            connection=connection,
            transaction_types=(
                ORGANIZATION_TRANSACTION_ADMIN_BALANCE_SET,
            ),
            positive=False,
        )

        total_removal_count = (
            personal_removal_count
            + organization_removal_count
        )

        total_credits_removed = (
            personal_credits_removed
            + organization_credits_removed
        )

        net_change = (
            total_credits_generated
            - total_credits_removed
        )

        circulation_reconciliation_difference = (
            total_circulation
            - net_change
        )

        # --------------------------------------------------
        # Commerce
        # --------------------------------------------------

        (
            commercial_purchase_count,
            commercial_spending_total,
        ) = _aggregate_personal_transactions(
            connection=connection,
            transaction_types=(
                TRANSACTION_COMMERCIAL_SHOP_PURCHASE,
            ),
            positive=False,
        )

        (
            business_sale_count,
            business_sales_total,
        ) = _aggregate_organization_transactions(
            connection=connection,
            transaction_types=(
                ORGANIZATION_TRANSACTION_SHOP_SALE,
            ),
            positive=True,
        )

        (
            institutional_payout_count,
            institutional_payout_total,
        ) = _aggregate_organization_transactions(
            connection=connection,
            transaction_types=(
                ORGANIZATION_TRANSACTION_USER_PAYMENT,
            ),
            positive=False,
        )

        top_business_row = connection.execute(
            """
            SELECT
                organization.organization_id,
                organization.name,
                organization.organization_type,
                organization.balance,
                organization.active,
                COUNT(
                    sale.organization_transaction_id
                ) AS sale_count,
                COALESCE(
                    SUM(sale.amount),
                    0
                ) AS sales_total
            FROM organizations
                AS organization
            LEFT JOIN organization_transactions
                AS sale
                ON sale.organization_id
                    = organization.organization_id
                AND sale.transaction_type = ?
                AND sale.amount > 0
            WHERE
                organization.organization_type = ?
            GROUP BY
                organization.organization_id,
                organization.name,
                organization.organization_type,
                organization.balance,
                organization.active
            HAVING
                COUNT(
                    sale.organization_transaction_id
                ) > 0
            ORDER BY
                sales_total DESC,
                sale_count DESC,
                organization.balance DESC,
                organization.name
                    COLLATE NOCASE ASC
            LIMIT 1
            """,
            (
                ORGANIZATION_TRANSACTION_SHOP_SALE,
                ORGANIZATION_TYPE_BUSINESS,
            ),
        ).fetchone()

        commercial_reconciliation_difference = (
            commercial_spending_total
            - business_sales_total
        )

        shop_purchase_count = (
            system_shop_sink_count
            + commercial_purchase_count
        )

        shop_spending_total = (
            system_shop_sink_total
            + commercial_spending_total
        )

        # --------------------------------------------------
        # Citizen transfers
        # --------------------------------------------------

        (
            transfer_count,
            transfer_volume,
        ) = _aggregate_personal_transactions(
            connection=connection,
            transaction_types=(
                TRANSACTION_TRANSFER_SENT,
            ),
            positive=False,
        )

        # --------------------------------------------------
        # Citation ledger
        # --------------------------------------------------

        citation_row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_count,
                COALESCE(
                    SUM(amount),
                    0
                ) AS total_value,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = ?
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS open_count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = ?
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS open_value,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = ?
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS paid_count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = ?
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS paid_value,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = ?
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS void_count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN status = ?
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS void_value
            FROM citations
            """,
            (
                CITATION_STATUS_OPEN,
                CITATION_STATUS_OPEN,
                CITATION_STATUS_PAID,
                CITATION_STATUS_PAID,
                CITATION_STATUS_VOID,
                CITATION_STATUS_VOID,
            ),
        ).fetchone()

        citation_total_count = int(
            citation_row["total_count"]
        )

        citation_total_value = int(
            citation_row["total_value"]
        )

        citation_open_count = int(
            citation_row["open_count"]
        )

        citation_open_value = int(
            citation_row["open_value"]
        )

        citation_paid_count = int(
            citation_row["paid_count"]
        )

        citation_paid_value = int(
            citation_row["paid_value"]
        )

        citation_void_count = int(
            citation_row["void_count"]
        )

        citation_void_value = int(
            citation_row["void_value"]
        )

        citation_reconciliation_difference = (
            citation_paid_value
            - fine_sink_total
        )

        # --------------------------------------------------
        # Shop and citizen inventory
        # --------------------------------------------------

        active_shop_items = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM shop_items
                WHERE active = 1
                """
            ).fetchone()
        )

        limited_stock_items = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM shop_items
                WHERE
                    active = 1
                    AND stock IS NOT NULL
                """
            ).fetchone()
        )

        sold_out_items = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM shop_items
                WHERE
                    active = 1
                    AND stock = 0
                """
            ).fetchone()
        )

        inventory_quantity_total = _first_value(
            connection.execute(
                """
                SELECT COALESCE(
                    SUM(quantity),
                    0
                )
                FROM inventory
                """
            ).fetchone()
        )

    richest_user = _account_summary(
        richest_user_row
    )

    richest_organization = (
        _organization_summary(
            richest_organization_row
        )
    )

    top_business = _organization_summary(
        top_business_row
    )

    return {
        # Citizen accounts
        "total_users": total_users,
        "citizen_balance_total": (
            citizen_balance_total
        ),
        "richest_user": richest_user,

        # Organization accounts
        "total_organizations": (
            total_organizations
        ),
        "active_organizations": (
            active_organizations
        ),
        "inactive_organizations": (
            inactive_organizations
        ),
        "business_organizations": (
            business_organizations
        ),
        "organization_balance_total": (
            organization_balance_total
        ),
        "richest_organization": (
            richest_organization
        ),
        "top_business": top_business,

        # Complete circulation
        "total_circulation": total_circulation,
        "total_credits": total_circulation,

        # Generation
        "personal_generation_count": (
            personal_generation_count
        ),
        "personal_credits_generated": (
            personal_credits_generated
        ),
        "organization_revenue_count": (
            organization_revenue_count
        ),
        "organization_revenue_generated": (
            organization_revenue_generated
        ),
        "organization_balance_generation_count": (
            organization_balance_generation_count
        ),
        "organization_balance_generated": (
            organization_balance_generated
        ),
        "organization_generation_count": (
            organization_generation_count
        ),
        "organization_credits_generated": (
            organization_credits_generated
        ),
        "total_generation_count": (
            total_generation_count
        ),
        "credits_generated": (
            total_credits_generated
        ),

        # Removal
        "system_shop_sink_count": (
            system_shop_sink_count
        ),
        "system_shop_sink_total": (
            system_shop_sink_total
        ),
        "personal_admin_removal_count": (
            personal_admin_removal_count
        ),
        "personal_admin_removal_total": (
            personal_admin_removal_total
        ),
        "fine_payment_count": (
            fine_payment_count
        ),
        "fine_payment_total": (
            fine_payment_total
        ),
        "fine_collection_count": (
            fine_collection_count
        ),
        "fine_collection_total": (
            fine_collection_total
        ),
        "fine_sink_count": fine_sink_count,
        "fine_sink_total": fine_sink_total,
        "personal_removal_count": (
            personal_removal_count
        ),
        "personal_credits_removed": (
            personal_credits_removed
        ),
        "organization_removal_count": (
            organization_removal_count
        ),
        "organization_credits_removed": (
            organization_credits_removed
        ),
        "total_removal_count": (
            total_removal_count
        ),
        "credits_removed": (
            total_credits_removed
        ),
        "net_change": net_change,

        # Reconciliation
        "circulation_reconciliation_difference": (
            circulation_reconciliation_difference
        ),
        "circulation_reconciled": (
            circulation_reconciliation_difference
            == 0
        ),

        # Commerce
        "system_shop_purchase_count": (
            system_shop_sink_count
        ),
        "system_shop_spending_total": (
            system_shop_sink_total
        ),
        "commercial_purchase_count": (
            commercial_purchase_count
        ),
        "commercial_spending_total": (
            commercial_spending_total
        ),
        "business_sale_count": (
            business_sale_count
        ),
        "business_sales_total": (
            business_sales_total
        ),
        "institutional_payout_count": (
            institutional_payout_count
        ),
        "institutional_payout_total": (
            institutional_payout_total
        ),
        "commercial_reconciliation_difference": (
            commercial_reconciliation_difference
        ),
        "commercial_reconciled": (
            commercial_reconciliation_difference
            == 0
        ),
        "shop_purchase_count": (
            shop_purchase_count
        ),
        "shop_spending_total": (
            shop_spending_total
        ),

        # Transfers
        "transfer_count": transfer_count,
        "transfer_volume": transfer_volume,

        # Citations
        "citation_total_count": (
            citation_total_count
        ),
        "citation_total_value": (
            citation_total_value
        ),
        "citation_open_count": (
            citation_open_count
        ),
        "citation_open_value": (
            citation_open_value
        ),
        "citation_paid_count": (
            citation_paid_count
        ),
        "citation_paid_value": (
            citation_paid_value
        ),
        "citation_void_count": (
            citation_void_count
        ),
        "citation_void_value": (
            citation_void_value
        ),
        "citation_reconciliation_difference": (
            citation_reconciliation_difference
        ),
        "citation_reconciled": (
            citation_reconciliation_difference
            == 0
        ),

        # Inventory
        "active_shop_items": (
            active_shop_items
        ),
        "limited_stock_items": (
            limited_stock_items
        ),
        "sold_out_items": sold_out_items,
        "inventory_quantity_total": (
            inventory_quantity_total
        ),
    }