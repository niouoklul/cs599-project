from pathlib import Path

from app.database import DEFAULT_DB_PATH, initialize_database


def main():
    db_path = Path(DEFAULT_DB_PATH)
    if db_path.exists():
        db_path.unlink()
    initialize_database(db_path)
    print(f"Demo database reset: {db_path}")


if __name__ == "__main__":
    main()
