from db.database import get_connection
from services.economy_service import utc_now


def log_transaction(
    user_id: int,
    transaction_type: str,
    amount: int,
    reason: str,
    target_user_id: int | None = None,
) -> None:
    """
    Records a money-related action in the transactions table.

    This does not change balances.
    It only records what happened.
    """
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO transactions (
                user_id,
                target_user_id,
                type,
                amount,
                reason,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                target_user_id,
                transaction_type,
                amount,
                reason,
                utc_now(),
            ),
        )

        connection.commit()


def get_recent_transactions(user_id: int, limit: int = 10) -> list[dict]:
    """
    Gets recent transactions for one user.
    """
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                transaction_id,
                user_id,
                target_user_id,
                type,
                amount,
                reason,
                created_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY transaction_id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [dict(row) for row in rows]