from db.database import get_connection


V15_MIGRATION_VERSION = 150
V15_MIGRATION_NAME = "verify_v1_5_item_schema"


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


def ensure_migration_table(cursor) -> None:
    """
    Creates the migration-history table if it does not already exist.

    This table records which database migrations have been completed.
    """

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def migration_has_been_applied(cursor, version: int) -> bool:
    """
    Returns True when the requested migration version is already recorded.
    """

    cursor.execute(
        """
        SELECT 1
        FROM schema_migrations
        WHERE version = ?
        LIMIT 1
        """,
        (version,),
    )

    return cursor.fetchone() is not None


def record_migration(cursor, version: int, name: str) -> None:
    """
    Records a completed migration in the migration-history table.
    """

    cursor.execute(
        """
        INSERT INTO schema_migrations (
            version,
            name
        )
        VALUES (?, ?)
        """,
        (
            version,
            name,
        ),
    )


def apply_v15_item_migration(cursor) -> None:
    """
    Adds or verifies all shop-item fields introduced in ENVI Ledger V1.5.

    Existing fields are left untouched.
    Missing fields are added safely.
    """

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


def run_database_migrations() -> None:
    """
    Runs pending database migrations for ENVI Ledger.

    Completed migration versions are recorded so they do not run again.
    Existing user data is preserved.
    """

    with get_connection() as connection:
        cursor = connection.cursor()

        try:
            ensure_migration_table(cursor)

            if migration_has_been_applied(
                cursor,
                V15_MIGRATION_VERSION,
            ):
                print(
                    "Skipping migration "
                    f"{V15_MIGRATION_VERSION}: "
                    f"{V15_MIGRATION_NAME}"
                )
                connection.commit()
                return

            print(
                "Applying migration "
                f"{V15_MIGRATION_VERSION}: "
                f"{V15_MIGRATION_NAME}"
            )

            apply_v15_item_migration(cursor)

            record_migration(
                cursor=cursor,
                version=V15_MIGRATION_VERSION,
                name=V15_MIGRATION_NAME,
            )

            connection.commit()

            print(
                "Migration "
                f"{V15_MIGRATION_VERSION} completed: "
                f"{V15_MIGRATION_NAME}"
            )

        except Exception:
            connection.rollback()

            print(
                "Migration "
                f"{V15_MIGRATION_VERSION} failed: "
                f"{V15_MIGRATION_NAME}"
            )

            raise