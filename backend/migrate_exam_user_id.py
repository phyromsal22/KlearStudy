import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "klearstudy.db"


def main():
    print("=" * 60)
    print("KlearStudy - Exam User ID Migration")
    print("=" * 60)
    print(f"Database: {DB_PATH}")

    if not DB_PATH.exists():
        print("ERROR: Database file was not found.")
        return

    connection = sqlite3.connect(str(DB_PATH))

    try:
        cursor = connection.cursor()

        # Inspect the existing schema.
        cursor.execute("PRAGMA table_info(exam_attempts)")
        columns = {
            row[1] for row in cursor.fetchall()
        }

        if not columns:
            print("ERROR: Table exam_attempts was not found.")
            return

        print("Existing columns:", sorted(columns))

        if "user_id" not in columns:
            cursor.execute(
                "ALTER TABLE exam_attempts ADD COLUMN user_id INTEGER"
            )
            print("Added column: user_id")
        else:
            print("Column user_id already exists.")

        # Index improves owner-filtered exam queries.
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            ix_exam_attempts_user_id
            ON exam_attempts(user_id)
            """
        )

        connection.commit()

        cursor.execute("PRAGMA table_info(exam_attempts)")
        updated_columns = {
            row[1] for row in cursor.fetchall()
        }

        if "user_id" not in updated_columns:
            raise RuntimeError(
                "Migration verification failed: user_id is missing."
            )

        print("\nSUCCESS: Migration completed.")
        print("Verified column: user_id")
        print("Existing exam records were preserved.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()