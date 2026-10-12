import os
import sqlite3


# ============================================================
# STEP 35.2.2 — SAFE MIGRATION
# Create lesson_analyses table
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "klearstudy.db")


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS lesson_analyses (
    id INTEGER PRIMARY KEY,
    lesson_id INTEGER NOT NULL UNIQUE,
    main_title TEXT,
    main_topic TEXT,
    sections TEXT NOT NULL DEFAULT '[]',
    important_concepts TEXT NOT NULL DEFAULT '[]',
    technical_terms TEXT NOT NULL DEFAULT '[]',
    qcm_topics TEXT NOT NULL DEFAULT '[]',
    exam_topics TEXT NOT NULL DEFAULT '[]',
    explain_topics TEXT NOT NULL DEFAULT '[]',
    ask_ai_topics TEXT NOT NULL DEFAULT '[]',
    source_warnings TEXT NOT NULL DEFAULT '[]',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (lesson_id)
        REFERENCES lessons(id)
        ON DELETE CASCADE
);
"""


CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS ix_lesson_analyses_id
ON lesson_analyses(id);
"""


CREATE_LESSON_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS
ix_lesson_analyses_lesson_id
ON lesson_analyses(lesson_id);
"""


def main():
    print("=" * 70)
    print("STEP 35.2.2 — LESSON ANALYSIS MIGRATION")
    print("=" * 70)

    print()
    print(f"Database:")
    print(f"  {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print()
        print("❌ Database not found.")
        print("   Make sure you run this from the backend folder.")
        return

    print()
    print("Connecting to SQLite...")

    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()

        # ----------------------------------------------------
        # Check existing tables
        # ----------------------------------------------------
        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name='lessons'
            """
        )

        lessons_exists = cursor.fetchone()

        if not lessons_exists:
            print()
            print("❌ lessons table does not exist.")
            print("   Start the backend first so the database is initialized.")
            return

        print("  ✓ lessons table exists")

        # ----------------------------------------------------
        # Check lesson_analyses table
        # ----------------------------------------------------
        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name='lesson_analyses'
            """
        )

        analysis_exists = cursor.fetchone()

        if analysis_exists:
            print()
            print("✓ lesson_analyses table already exists.")
            print("  No destructive changes will be made.")

        else:
            print()
            print("➕ Creating lesson_analyses table...")

            cursor.execute(CREATE_TABLE_SQL)

            print("  ✅ lesson_analyses table created")

        # ----------------------------------------------------
        # Indexes
        # ----------------------------------------------------
        print()
        print("Checking indexes...")

        cursor.execute(CREATE_INDEX_SQL)
        print("  ✓ ix_lesson_analyses_id")

        cursor.execute(CREATE_LESSON_INDEX_SQL)
        print("  ✓ ix_lesson_analyses_lesson_id")

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------
        connection.commit()

        # ----------------------------------------------------
        # Verification
        # ----------------------------------------------------
        print()
        print("Verification:")

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name='lesson_analyses'
            """
        )

        if cursor.fetchone():
            print("  ✅ lesson_analyses")

        else:
            print("  ❌ lesson_analyses")

        # Show columns
        print()
        print("Columns:")

        cursor.execute(
            """
            PRAGMA table_info(lesson_analyses)
            """
        )

        columns = cursor.fetchall()

        for column in columns:
            column_id = column[0]
            column_name = column[1]
            column_type = column[2]

            print(
                f"  {column_id:2d}. "
                f"{column_name:<25} "
                f"{column_type}"
            )

        print()
        print("=" * 70)
        print("✅ MIGRATION COMPLETE")
        print("=" * 70)
        print()
        print("Database was NOT deleted.")
        print("Existing data was NOT modified.")

    except Exception as error:
        connection.rollback()

        print()
        print("=" * 70)
        print("❌ MIGRATION FAILED")
        print("=" * 70)
        print()
        print(str(error))

        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()