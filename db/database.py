from multiprocessing import connection
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "data" / "envi_ledger.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"


def get_connection():
    """
    Opens a connection to the ENVI Ledger database.
    """
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """
    Creates the database tables if they do not already exist.
    """
    with get_connection() as connection:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
            connection.executescript(schema_file.read())

        connection.commit()


if __name__ == "__main__":
    initialize_database()
    print("ENVI Ledger database initialized successfully.")