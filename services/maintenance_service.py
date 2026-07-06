from db.database import get_connection
from services.economy_service import utc_now
from utils.constants import STARTING_BALANCE


def clear_user_cooldowns(user_id: int) -> int:
    """
    Clears all cooldown records for one user.

    Returns how many cooldown records were deleted.
    """
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM cooldowns
            WHERE user_id = ?
            """,
            (user_id,),
        )

        connection.commit()

    return cursor.rowcount


def reset_user_data(user_id: int, display_name: str) -> dict:
    """
    Resets one user's ENVI Ledger data.

    This clears:
    - inventory
    - cooldowns
    - that user's transaction records

    It also resets their balance to STARTING_BALANCE.

    It does not delete the user account itself.
    """
    now = utc_now()

    with get_connection() as connection:
        existing_user = connection.execute(
            """
            SELECT balance
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        old_balance = 0

        if existing_user is not None:
            old_balance = int(existing_user["balance"])

        inventory_cursor = connection.execute(
            """
            DELETE FROM inventory
            WHERE user_id = ?
            """,
            (user_id,),
        )

        cooldown_cursor = connection.execute(
            """
            DELETE FROM cooldowns
            WHERE user_id = ?
            """,
            (user_id,),
        )

        transaction_cursor = connection.execute(
            """
            DELETE FROM transactions
            WHERE user_id = ?
            """,
            (user_id,),
        )

        if existing_user is None:
            connection.execute(
                """
                INSERT INTO users (
                    user_id,
                    display_name,
                    balance,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    display_name,
                    STARTING_BALANCE,
                    now,
                    now,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE users
                SET display_name = ?,
                    balance = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (
                    display_name,
                    STARTING_BALANCE,
                    now,
                    user_id,
                ),
            )

        connection.commit()

    return {
        "old_balance": old_balance,
        "new_balance": STARTING_BALANCE,
        "inventory_deleted": inventory_cursor.rowcount,
        "cooldowns_deleted": cooldown_cursor.rowcount,
        "transactions_deleted": transaction_cursor.rowcount,
    }