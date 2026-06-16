import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DEFAULT_DB_PATH = PROJECT_DIR / "data" / "enterprise.db"


def connect(db_path=None):
    path = Path(db_path or DEFAULT_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path=None):
    db_file = Path(db_path or DEFAULT_DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    schema = (BASE_DIR / "schema.sql").read_text(encoding="utf-8")

    with connect(db_file) as connection:
        connection.executescript(schema)
        existing_user = connection.execute("SELECT id FROM users LIMIT 1").fetchone()
        if existing_user is None:
            from .seed import seed_database

            seed_database(connection)
        connection.commit()

    return db_file


def row_to_dict(row):
    return dict(row) if row is not None else None


def rows_to_list(rows):
    return [dict(row) for row in rows]
