from datetime import datetime, timezone

from db.database import get_connection
from utils.constants import STARTING_BALANCE


def utc_now() -> str:
    """
    Returns the current UTC time as text for database storage.
    """
    return datetime.now(timezone.utc).isoformat()


def ensure_user(user_id: int, display_name: str) -> None:
    """
    Makes sure a user has an ENVI Ledger account.

    If the account does not exist, create it.
    If the account already exists, update the display name.
    """
    now = utc_now()

    with get_connection() as connection:
        existing_user = connection.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

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
                (user_id, display_name, STARTING_BALANCE, now, now),
            )
        else:
            connection.execute(
                """
                UPDATE users
                SET display_name = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (display_name, now, user_id),
            )

        connection.commit()


def get_balance(user_id: int) -> int:
    """
    Gets a user's balance.

    If the user is missing somehow, return 0.
    """
    with get_connection() as connection:
        user = connection.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if user is None:
        return 0

    return int(user["balance"])


def add_credits(user_id: int, amount: int) -> int:
    """
    Adds credits to a user's balance.

    Returns the new balance.
    """
    if amount <= 0:
        raise ValueError("Amount must be greater than 0.")

    current_balance = get_balance(user_id)
    new_balance = current_balance + amount

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET balance = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (new_balance, utc_now(), user_id),
        )
        connection.commit()

    return new_balance


def remove_credits(user_id: int, amount: int) -> int:
    """
    Removes credits from a user's balance.

    Balance cannot go below 0.

    Returns the new balance.
    """
    if amount <= 0:
        raise ValueError("Amount must be greater than 0.")

    current_balance = get_balance(user_id)

    if current_balance < amount:
        raise ValueError("Insufficient Nexus Credits.")

    new_balance = current_balance - amount

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET balance = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (new_balance, utc_now(), user_id),
        )
        connection.commit()

    return new_balance


def set_balance(user_id: int, amount: int) -> int:
    """
    Sets a user's balance to an exact amount.

    Returns the new balance.
    """
    if amount < 0:
        raise ValueError("Balance cannot be negative.")

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET balance = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (amount, utc_now(), user_id),
        )
        connection.commit()

    return amount

def get_top_balances(limit: int = 10) -> list[dict]:
    """
    Gets the top users by balance.
    """
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                user_id,
                display_name,
                balance
            FROM users
            ORDER BY balance DESC, display_name ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]