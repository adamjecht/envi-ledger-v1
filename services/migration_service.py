from db.database import get_connection


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    """
    Checks whether a column already exists on a table.

    This prevents migrations from trying to add the same column twice.
    """

    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    return any(column["name"] == column_name for column in columns)


def add_column_if_missing(
    cursor,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> bool:
    """
    Adds a column only if it does not already exist.

    Returns True if the column was added.
    Returns False if the column already existed.
    """

    if column_exists(cursor, table_name, column_name):
        return False

    cursor.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
    )
    return True


def run_database_migrations() -> None:
    """
    Runs safe database migrations for ENVI Ledger.

    These migrations do not wipe existing data.
    They only add missing columns needed by newer versions.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        add_column_if_missing(
            cursor=cursor,
            table_name="shop_items",
            column_name="category",
            column_definition="TEXT NOT NULL DEFAULT 'General'",
        )

        add_column_if_missing(
            cursor=cursor,
            table_name="shop_items",
            column_name="rarity",
            column_definition="TEXT NOT NULL DEFAULT 'Common'",
        )

        add_column_if_missing(
            cursor=cursor,
            table_name="shop_items",
            column_name="usable",
            column_definition="INTEGER NOT NULL DEFAULT 0",
        )

        add_column_if_missing(
            cursor=cursor,
            table_name="shop_items",
            column_name="consumable",
            column_definition="INTEGER NOT NULL DEFAULT 0",
        )

        add_column_if_missing(
            cursor=cursor,
            table_name="shop_items",
            column_name="use_message",
            column_definition="TEXT",
        )

        add_column_if_missing(
            cursor=cursor,
            table_name="shop_items",
            column_name="stock",
            column_definition="INTEGER",
        )

        connection.commit()