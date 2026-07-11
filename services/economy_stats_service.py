from db.database import get_connection
from utils.constants import (
    TRANSACTION_ADMIN_ADD,
    TRANSACTION_ADMIN_REMOVE,
    TRANSACTION_ADMIN_RESET,
    TRANSACTION_ADMIN_SET,
    TRANSACTION_DAILY,
    TRANSACTION_SHOP_PURCHASE,
    TRANSACTION_TRANSFER_SENT,
    TRANSACTION_WORK,
)


CREDIT_GENERATING_TYPES = (
    TRANSACTION_DAILY,
    TRANSACTION_WORK,
    TRANSACTION_ADMIN_ADD,
    TRANSACTION_ADMIN_SET,
    TRANSACTION_ADMIN_RESET,
)

CREDIT_REMOVING_TYPES = (
    TRANSACTION_SHOP_PURCHASE,
    TRANSACTION_ADMIN_REMOVE,
    TRANSACTION_ADMIN_SET,
    TRANSACTION_ADMIN_RESET,
)


def _first_value(row, default=0):
    """
    Safely extracts the first value from a SQLite row.
    """

    if row is None:
        return default

    value = row[0]

    if value is None:
        return default

    return value


def get_economy_stats() -> dict:
    """
    Builds a staff-facing economy snapshot.

    Transfers are counted separately because they move existing credits
    between users instead of creating or removing credits.
    """

    with get_connection() as connection:
        total_users = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM users
                """
            ).fetchone()
        )

        total_credits = _first_value(
            connection.execute(
                """
                SELECT COALESCE(SUM(balance), 0)
                FROM users
                """
            ).fetchone()
        )

        richest_user = connection.execute(
            """
            SELECT
                user_id,
                display_name,
                balance
            FROM users
            ORDER BY balance DESC, display_name ASC
            LIMIT 1
            """
        ).fetchone()

        credits_generated = _first_value(
            connection.execute(
                f"""
                SELECT COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE
                    type IN ({",".join("?" for _ in CREDIT_GENERATING_TYPES)})
                    AND amount > 0
                """,
                CREDIT_GENERATING_TYPES,
            ).fetchone()
        )

        credits_removed = _first_value(
            connection.execute(
                f"""
                SELECT COALESCE(SUM(ABS(amount)), 0)
                FROM transactions
                WHERE
                    type IN ({",".join("?" for _ in CREDIT_REMOVING_TYPES)})
                    AND amount < 0
                """,
                CREDIT_REMOVING_TYPES,
            ).fetchone()
        )

        shop_purchase_count = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM transactions
                WHERE type = ?
                """,
                (TRANSACTION_SHOP_PURCHASE,),
            ).fetchone()
        )

        shop_spending_total = _first_value(
            connection.execute(
                """
                SELECT COALESCE(SUM(ABS(amount)), 0)
                FROM transactions
                WHERE type = ? AND amount < 0
                """,
                (TRANSACTION_SHOP_PURCHASE,),
            ).fetchone()
        )

        transfer_count = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM transactions
                WHERE type = ?
                """,
                (TRANSACTION_TRANSFER_SENT,),
            ).fetchone()
        )

        transfer_volume = _first_value(
            connection.execute(
                """
                SELECT COALESCE(SUM(ABS(amount)), 0)
                FROM transactions
                WHERE type = ? AND amount < 0
                """,
                (TRANSACTION_TRANSFER_SENT,),
            ).fetchone()
        )

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
                WHERE active = 1 AND stock IS NOT NULL
                """
            ).fetchone()
        )

        sold_out_items = _first_value(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM shop_items
                WHERE active = 1 AND stock = 0
                """
            ).fetchone()
        )

        inventory_quantity_total = _first_value(
            connection.execute(
                """
                SELECT COALESCE(SUM(quantity), 0)
                FROM inventory
                """
            ).fetchone()
        )

    richest_user_data = None

    if richest_user is not None:
        richest_user_data = {
            "user_id": richest_user["user_id"],
            "display_name": richest_user["display_name"],
            "balance": int(richest_user["balance"]),
        }

    return {
        "total_users": int(total_users),
        "total_credits": int(total_credits),
        "richest_user": richest_user_data,
        "credits_generated": int(credits_generated),
        "credits_removed": int(credits_removed),
        "net_change": int(credits_generated) - int(credits_removed),
        "shop_purchase_count": int(shop_purchase_count),
        "shop_spending_total": int(shop_spending_total),
        "transfer_count": int(transfer_count),
        "transfer_volume": int(transfer_volume),
        "active_shop_items": int(active_shop_items),
        "limited_stock_items": int(limited_stock_items),
        "sold_out_items": int(sold_out_items),
        "inventory_quantity_total": int(inventory_quantity_total),
    }