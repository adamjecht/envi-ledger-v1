from datetime import datetime, timezone

from db.database import get_connection
from services.economy_service import utc_now


def parse_utc_datetime(timestamp: str) -> datetime:
    """
    Converts stored timestamp text back into a datetime object.
    """
    value = datetime.fromisoformat(timestamp)

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value


def get_last_used(user_id: int, command_name: str) -> str | None:
    """
    Gets the last time a user used a cooldown-tracked command.
    """
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT last_used
            FROM cooldowns
            WHERE user_id = ? AND command_name = ?
            """,
            (user_id, command_name),
        ).fetchone()

    if row is None:
        return None

    return str(row["last_used"])


def get_remaining_cooldown(
    user_id: int,
    command_name: str,
    cooldown_seconds: int,
) -> int:
    """
    Returns how many seconds are left on a command cooldown.

    If the command is ready, returns 0.
    """
    last_used = get_last_used(user_id, command_name)

    if last_used is None:
        return 0

    last_used_time = parse_utc_datetime(last_used)
    now = datetime.now(timezone.utc)

    elapsed_seconds = int((now - last_used_time).total_seconds())
    remaining_seconds = cooldown_seconds - elapsed_seconds

    if remaining_seconds <= 0:
        return 0

    return remaining_seconds


def set_cooldown(user_id: int, command_name: str) -> None:
    """
    Saves the current time as the user's latest use of a command.
    """
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO cooldowns (
                user_id,
                command_name,
                last_used
            )
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, command_name)
            DO UPDATE SET last_used = excluded.last_used
            """,
            (user_id, command_name, utc_now()),
        )

        connection.commit()