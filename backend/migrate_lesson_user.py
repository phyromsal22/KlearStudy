from pathlib import Path
from datetime import datetime
import shutil
import sqlite3


# ============================================================
# KlearStudy
# LESSON USER OWNERSHIP MIGRATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "klearstudy.db"

BACKUP_NAME = (
    f"klearstudy_before_lesson_user_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
)

BACKUP_PATH = BASE_DIR / BACKUP_NAME


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = cursor.fetchall()

    return any(
        column[1] == column_name
        for column in columns
    )


def main():

    print("=" * 70)
    print("KlearStudy - Lesson User Ownership Migration")
    print("=" * 70)

    print()
    print(f"Database: {DB_PATH}")

    # ========================================================
    # CHECK DATABASE
    # ========================================================

    if not DB_PATH.exists():
        print()
        print("ERROR: klearstudy.db was not found.")
        return

    # ========================================================
    # BACKUP
    # ========================================================

    print()
    print("[1/5] Creating database backup...")

    shutil.copy2(
        DB_PATH,
        BACKUP_PATH,
    )

    print(f"Backup created:")
    print(BACKUP_PATH)

    # ========================================================
    # CONNECT
    # ========================================================

    connection = sqlite3.connect(
        DB_PATH
    )

    cursor = connection.cursor()

    try:

        # ====================================================
        # CHECK LESSON TABLE
        # ====================================================

        print()
        print("[2/5] Checking lessons table...")

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name='lessons'
            """
        )

        if cursor.fetchone() is None:

            raise RuntimeError(
                "lessons table does not exist."
            )

        print("OK - lessons table exists.")

        # ====================================================
        # CHECK USER TABLE
        # ====================================================

        print()
        print("[3/5] Checking users table...")

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name='users'
            """
        )

        if cursor.fetchone() is None:

            raise RuntimeError(
                "users table does not exist."
            )

        print("OK - users table exists.")

        # ====================================================
        # CHECK EXISTING COLUMN
        # ====================================================

        print()
        print("[4/5] Checking Lesson.user_id...")

        if column_exists(
            cursor,
            "lessons",
            "user_id",
        ):

            print(
                "OK - lessons.user_id already exists."
            )

        else:

            print(
                "Adding lessons.user_id..."
            )

            cursor.execute(
                """
                ALTER TABLE lessons
                ADD COLUMN user_id INTEGER
                """
            )

            connection.commit()

            print(
                "OK - lessons.user_id added."
            )

        # ====================================================
        # VERIFY
        # ====================================================

        print()
        print("[5/5] Verifying migration...")

        cursor.execute(
            "PRAGMA table_info(lessons)"
        )

        columns = cursor.fetchall()

        user_column = None

        for column in columns:

            if column[1] == "user_id":
                user_column = column
                break

        if user_column is None:

            raise RuntimeError(
                "Migration verification failed."
            )

        print()
        print("Lesson.user_id:")
        print(f"  column name : {user_column[1]}")
        print(f"  type        : {user_column[2]}")
        print(f"  nullable    : {'YES' if user_column[3] == 0 else 'NO'}")

        # ====================================================
        # COUNT LESSONS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM lessons
            """
        )

        lesson_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM lessons
            WHERE user_id IS NULL
            """
        )

        unassigned_count = cursor.fetchone()[0]

        print()
        print("Lesson statistics:")
        print(f"  Total lessons      : {lesson_count}")
        print(f"  Without user_id    : {unassigned_count}")

        # ====================================================
        # FINAL
        # ====================================================

        print()
        print("=" * 70)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print()
        print("IMPORTANT:")
        print(
            "Existing lessons were NOT assigned to any user."
        )
        print(
            "They remain user_id = NULL until we decide"
        )
        print(
            "which user should own them."
        )

        print()
        print(f"Backup:")
        print(BACKUP_PATH)

    except Exception as error:

        connection.rollback()

        print()
        print("=" * 70)
        print("MIGRATION FAILED")
        print("=" * 70)

        print()
        print(f"Error: {error}")

        print()
        print("Your original database backup is available at:")
        print(BACKUP_PATH)

        raise

    finally:

        connection.close()


if __name__ == "__main__":
    main()