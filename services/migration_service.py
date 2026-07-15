from __future__ import annotations

import sqlite3
from collections.abc import Callable

from db.database import get_connection


V15_MIGRATION_VERSION = 150
V15_MIGRATION_NAME = "verify_v1_5_item_schema"

V2_ORGANIZATION_MIGRATION_VERSION = 200
V2_ORGANIZATION_MIGRATION_NAME = (
    "create_v2_organization_schema"
)


MigrationFunction = Callable[[sqlite3.Cursor], None]


def column_exists(
    cursor: sqlite3.Cursor,
    table_name: str,
    column_name: str,
) -> bool:
    """
    Checks whether a column already exists on a table.
    """

    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = cursor.fetchall()

    return any(
        column["name"] == column_name
        for column in columns
    )


def add_column_if_missing(
    cursor: sqlite3.Cursor,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> bool:
    """
    Adds a column only when it does not already exist.

    Returns True when the column was added.
    Returns False when it already existed.
    """

    if column_exists(
        cursor,
        table_name,
        column_name,
    ):
        return False

    cursor.execute(
        f"""
        ALTER TABLE {table_name}
        ADD COLUMN {column_name} {column_definition}
        """
    )

    return True


def ensure_migration_table(
    cursor: sqlite3.Cursor,
) -> None:
    """
    Creates the migration-history table when needed.
    """

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def migration_has_been_applied(
    cursor: sqlite3.Cursor,
    version: int,
) -> bool:
    """
    Returns True when a migration is already recorded.
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


def record_migration(
    cursor: sqlite3.Cursor,
    version: int,
    name: str,
) -> None:
    """
    Records a successfully completed migration.
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


def apply_v15_item_migration(
    cursor: sqlite3.Cursor,
) -> None:
    """
    Adds or verifies the item fields introduced in V1.5.
    """

    add_column_if_missing(
        cursor=cursor,
        table_name="shop_items",
        column_name="category",
        column_definition=(
            "TEXT NOT NULL DEFAULT 'General'"
        ),
    )

    add_column_if_missing(
        cursor=cursor,
        table_name="shop_items",
        column_name="rarity",
        column_definition=(
            "TEXT NOT NULL DEFAULT 'Common'"
        ),
    )

    add_column_if_missing(
        cursor=cursor,
        table_name="shop_items",
        column_name="usable",
        column_definition=(
            "INTEGER NOT NULL DEFAULT 0"
        ),
    )

    add_column_if_missing(
        cursor=cursor,
        table_name="shop_items",
        column_name="consumable",
        column_definition=(
            "INTEGER NOT NULL DEFAULT 0"
        ),
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


def apply_v2_organization_migration(
    cursor: sqlite3.Cursor,
) -> None:
    """
    Creates the V2 organization foundation.

    The statements are idempotent so an interrupted or repeated
    startup will not duplicate tables or indexes.
    """

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS organizations (
            organization_id INTEGER
                PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
                COLLATE NOCASE
                UNIQUE,
            organization_type TEXT NOT NULL
                CHECK (
                    organization_type IN (
                        'BUSINESS',
                        'INSTITUTION',
                        'GOVERNMENT',
                        'FACTION'
                    )
                ),
            description TEXT NOT NULL DEFAULT '',
            balance INTEGER NOT NULL DEFAULT 0
                CHECK (balance >= 0),
            active INTEGER NOT NULL DEFAULT 1
                CHECK (active IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS organization_members (
            organization_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL
                CHECK (
                    role IN (
                        'OWNER',
                        'MANAGER',
                        'MEMBER'
                    )
                ),
            active INTEGER NOT NULL DEFAULT 1
                CHECK (active IN (0, 1)),
            joined_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            removed_at TEXT,
            PRIMARY KEY (
                organization_id,
                user_id
            ),
            FOREIGN KEY (organization_id)
                REFERENCES organizations(organization_id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
            FOREIGN KEY (user_id)
                REFERENCES users(user_id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS organization_transactions (
            organization_transaction_id INTEGER
                PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            actor_user_id INTEGER,
            target_user_id INTEGER,
            target_organization_id INTEGER,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL
                CHECK (amount != 0),
            balance_after INTEGER NOT NULL
                CHECK (balance_after >= 0),
            reason TEXT NOT NULL,
            related_item_id INTEGER,
            reference_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (organization_id)
                REFERENCES organizations(organization_id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
            FOREIGN KEY (actor_user_id)
                REFERENCES users(user_id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
            FOREIGN KEY (target_user_id)
                REFERENCES users(user_id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
            FOREIGN KEY (target_organization_id)
                REFERENCES organizations(organization_id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,
            FOREIGN KEY (related_item_id)
                REFERENCES shop_items(item_id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_organizations_type_active
        ON organizations (
            organization_type,
            active
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_organization_members_user_active
        ON organization_members (
            user_id,
            active
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_organization_members_org_role_active
        ON organization_members (
            organization_id,
            role,
            active
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_organization_transactions_org_created
        ON organization_transactions (
            organization_id,
            created_at DESC
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_organization_transactions_actor
        ON organization_transactions (
            actor_user_id
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_organization_transactions_target_user
        ON organization_transactions (
            target_user_id
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_organization_transactions_target_org
        ON organization_transactions (
            target_organization_id
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_organization_transactions_type_created
        ON organization_transactions (
            transaction_type,
            created_at DESC
        )
        """
    )


MIGRATIONS: tuple[
    tuple[
        int,
        str,
        MigrationFunction,
    ],
    ...,
] = (
    (
        V15_MIGRATION_VERSION,
        V15_MIGRATION_NAME,
        apply_v15_item_migration,
    ),
    (
        V2_ORGANIZATION_MIGRATION_VERSION,
        V2_ORGANIZATION_MIGRATION_NAME,
        apply_v2_organization_migration,
    ),
)


def run_migrations_on_connection(
    connection: sqlite3.Connection,
) -> None:
    """
    Runs every pending migration on a supplied connection.

    Exposing this function allows migrations to be tested against
    copied databases without touching the active ENVI database.
    """

    connection.execute("PRAGMA foreign_keys = ON")

    cursor = connection.cursor()

    ensure_migration_table(cursor)
    connection.commit()

    for version, name, migration_function in MIGRATIONS:
        if migration_has_been_applied(
            cursor,
            version,
        ):
            print(
                f"Skipping migration {version}: {name}"
            )
            continue

        print(
            f"Applying migration {version}: {name}"
        )

        try:
            migration_function(cursor)

            record_migration(
                cursor=cursor,
                version=version,
                name=name,
            )

            connection.commit()

            print(
                f"Migration {version} completed: {name}"
            )

        except Exception:
            connection.rollback()

            print(
                f"Migration {version} failed: {name}"
            )

            raise


def run_database_migrations() -> None:
    """
    Runs all pending migrations against the active database.
    """

    with get_connection() as connection:
        run_migrations_on_connection(connection)