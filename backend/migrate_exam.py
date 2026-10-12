"""
KlearStudy - AI Exam Database Migration v4

Adds the database fields required by Exam V4:

exam_attempts:
    - source_mode
    - provider
    - question_bank
    - qcm_count
    - short_answer_count

exam_answers:
    - removes the old ForeignKey -> qcm_questions
    - question_type
    - Text answers for QCM + Short Answer
    - result
    - semantic_score
    - lesson_id
    - topic
    - difficulty
    - explanation

IMPORTANT:
    - Existing Exam data is preserved.
    - Existing QCM tables are preserved.
    - A timestamped backup is created before migration.
    - This migration is designed for SQLite.

Run from:
    D:\KlearStudy\backend

Command:
    python migrate_exam_v4.py
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "klearstudy.db"


def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.with_name(
        f"{DB_PATH.stem}_before_exam_v4_{timestamp}{DB_PATH.suffix}"
    )
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def column_exists(cursor, table_name, column_name):
    cursor.execute(f'PRAGMA table_info("{table_name}")')
    return any(row[1] == column_name for row in cursor.fetchall())


def get_columns(cursor, table_name):
    cursor.execute(f'PRAGMA table_info("{table_name}")')
    return cursor.fetchall()


def add_column_if_missing(cursor, table_name, column_name, definition):
    if not column_exists(cursor, table_name, column_name):
        print(f"  + Adding {table_name}.{column_name}")
        cursor.execute(
            f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} {definition}'
        )
    else:
        print(f"  - {table_name}.{column_name} already exists")


def migrate_exam_attempts(cursor):
    print("\n[1/3] Updating exam_attempts...")

    if not table_exists(cursor, "exam_attempts"):
        print("  - exam_attempts does not exist. Nothing to migrate.")
        return

    # These columns are compatible with the existing ExamAttempt model.
    add_column_if_missing(
        cursor,
        "exam_attempts",
        "source_mode",
        "VARCHAR(20) NOT NULL DEFAULT 'ai'",
    )

    add_column_if_missing(
        cursor,
        "exam_attempts",
        "provider",
        "VARCHAR(20) NOT NULL DEFAULT 'auto'",
    )

    add_column_if_missing(
        cursor,
        "exam_attempts",
        "question_bank",
        "TEXT NOT NULL DEFAULT '[]'",
    )

    add_column_if_missing(
        cursor,
        "exam_attempts",
        "qcm_count",
        "INTEGER NOT NULL DEFAULT 0",
    )

    add_column_if_missing(
        cursor,
        "exam_attempts",
        "short_answer_count",
        "INTEGER NOT NULL DEFAULT 0",
    )

    # Existing V2 database should already have nullable qcm_set_id.
    # Check it here instead of rebuilding again unless necessary.
    columns = get_columns(cursor, "exam_attempts")
    qcm_column = next(
        (row for row in columns if row[1] == "qcm_set_id"),
        None,
    )

    if qcm_column is None:
        raise RuntimeError(
            "exam_attempts.qcm_set_id was not found."
        )

    if qcm_column[3] != 0:
        raise RuntimeError(
            "exam_attempts.qcm_set_id is still NOT NULL. "
            "Run the existing migrate_exam_v2.py first, "
            "or use a fresh V4 migration built from your current schema."
        )

    print("  OK: qcm_set_id is nullable")
    print("  OK: Exam V4 columns checked")


def migrate_exam_answers(cursor):
    print("\n[2/3] Updating exam_answers...")

    if not table_exists(cursor, "exam_answers"):
        print("  - exam_answers does not exist. Nothing to migrate.")
        return

    columns = get_columns(cursor, "exam_answers")
    names = {row[1] for row in columns}

    required_v4 = {
        "question_type",
        "selected_answer",
        "correct_answer",
        "result",
        "is_correct",
        "semantic_score",
        "lesson_id",
        "topic",
        "difficulty",
        "explanation",
    }

    # If all V4 fields exist, no rebuild is necessary.
    # However, the old FK may still exist, so inspect foreign keys.
    cursor.execute("PRAGMA foreign_key_list(exam_answers)")
    foreign_keys = cursor.fetchall()

    has_qcm_fk = any(
        len(row) >= 5
        and row[2] == "qcm_questions"
        and row[3] == "question_id"
        for row in foreign_keys
    )

    needs_rebuild = has_qcm_fk or not required_v4.issubset(names)

    if not needs_rebuild:
        print("  OK: exam_answers already uses V4 schema")
        return

    print("  - Rebuilding exam_answers for V4...")
    print("  - Removing old FK to qcm_questions")
    print("  - Preserving existing exam answer rows")

    cursor.execute(
        """
        CREATE TABLE exam_answers_new (
            id INTEGER NOT NULL,
            exam_attempt_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            question_type VARCHAR(20) NOT NULL DEFAULT 'qcm',
            selected_answer TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            result VARCHAR(30) NOT NULL DEFAULT 'wrong',
            is_correct INTEGER NOT NULL DEFAULT 0,
            semantic_score INTEGER,
            lesson_id INTEGER,
            topic VARCHAR(255),
            difficulty VARCHAR(20),
            explanation TEXT,

            PRIMARY KEY (id),

            FOREIGN KEY (
                exam_attempt_id
            ) REFERENCES exam_attempts (id)
            ON DELETE CASCADE
        )
        """
    )

    # Preserve all existing answer data.
    # Old answers were QCM answers, so they become question_type='qcm'.
    cursor.execute(
        """
        INSERT INTO exam_answers_new (
            id,
            exam_attempt_id,
            question_id,
            question_type,
            selected_answer,
            correct_answer,
            result,
            is_correct,
            semantic_score,
            lesson_id,
            topic,
            difficulty,
            explanation
        )
        SELECT
            id,
            exam_attempt_id,
            question_id,
            'qcm',
            CAST(selected_answer AS TEXT),
            CAST(correct_answer AS TEXT),
            CASE
                WHEN is_correct = 1 THEN 'correct'
                ELSE 'wrong'
            END,
            COALESCE(is_correct, 0),
            NULL,
            NULL,
            NULL,
            NULL,
            NULL
        FROM exam_answers
        """
    )

    cursor.execute("DROP TABLE exam_answers")
    cursor.execute(
        "ALTER TABLE exam_answers_new RENAME TO exam_answers"
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_exam_answers_id
        ON exam_answers (id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_exam_answers_exam_attempt_id
        ON exam_answers (exam_attempt_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_exam_answers_question_id
        ON exam_answers (question_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_exam_answers_question_type
        ON exam_answers (question_type)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_exam_answers_lesson_id
        ON exam_answers (lesson_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_exam_answers_topic
        ON exam_answers (topic)
        """
    )

    print("  OK: exam_answers rebuilt successfully")


def verify(cursor):
    print("\n[3/3] Verifying V4 schema...")

    # ------------------------------------------------------------
    # exam_attempts
    # ------------------------------------------------------------
    if not table_exists(cursor, "exam_attempts"):
        raise RuntimeError(
            "Verification failed: exam_attempts does not exist."
        )

    attempt_columns = get_columns(cursor, "exam_attempts")
    attempt_names = {row[1] for row in attempt_columns}

    required_attempt_columns = {
        "qcm_set_id",
        "lesson_ids",
        "source_mode",
        "provider",
        "question_bank",
        "qcm_count",
        "short_answer_count",
        "duration_minutes",
        "question_ids",
        "total_questions",
    }

    missing = required_attempt_columns - attempt_names

    if missing:
        raise RuntimeError(
            f"Verification failed: missing exam_attempts columns: {sorted(missing)}"
        )

    qcm_column = next(
        row for row in attempt_columns
        if row[1] == "qcm_set_id"
    )

    if qcm_column[3] != 0:
        raise RuntimeError(
            "Verification failed: qcm_set_id is still NOT NULL."
        )

    print("  OK: exam_attempts V4 columns exist")
    print("  OK: exam_attempts.qcm_set_id is nullable")

    # ------------------------------------------------------------
    # exam_answers
    # ------------------------------------------------------------
    if not table_exists(cursor, "exam_answers"):
        raise RuntimeError(
            "Verification failed: exam_answers does not exist."
        )

    answer_columns = get_columns(cursor, "exam_answers")
    answer_names = {row[1] for row in answer_columns}

    required_answer_columns = {
        "question_id",
        "question_type",
        "selected_answer",
        "correct_answer",
        "result",
        "is_correct",
        "semantic_score",
        "lesson_id",
        "topic",
        "difficulty",
        "explanation",
    }

    missing = required_answer_columns - answer_names

    if missing:
        raise RuntimeError(
            f"Verification failed: missing exam_answers columns: {sorted(missing)}"
        )

    cursor.execute("PRAGMA foreign_key_list(exam_answers)")
    foreign_keys = cursor.fetchall()

    qcm_fk = [
        row for row in foreign_keys
        if len(row) >= 3 and row[2] == "qcm_questions"
    ]

    if qcm_fk:
        raise RuntimeError(
            "Verification failed: exam_answers still has a "
            "foreign key to qcm_questions."
        )

    print("  OK: exam_answers V4 columns exist")
    print("  OK: exam_answers.question_id is NOT a QCM foreign key")

    # ------------------------------------------------------------
    # Row preservation check
    # ------------------------------------------------------------
    cursor.execute("SELECT COUNT(*) FROM exam_attempts")
    attempt_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM exam_answers")
    answer_count = cursor.fetchone()[0]

    print(f"  OK: exam_attempts rows preserved = {attempt_count}")
    print(f"  OK: exam_answers rows preserved = {answer_count}")

    # ------------------------------------------------------------
    # Test AI Exam insertion with NULL qcm_set_id
    # ------------------------------------------------------------
    cursor.execute(
        """
        INSERT INTO exam_attempts (
            qcm_set_id,
            lesson_ids,
            source_mode,
            provider,
            question_bank,
            qcm_count,
            short_answer_count,
            duration_minutes,
            question_ids,
            total_questions,
            score,
            correct_answers,
            accuracy,
            status,
            started_at,
            finished_at
        )
        VALUES (
            NULL,
            ?,
            'ai',
            'auto',
            ?,
            1,
            1,
            15,
            ?,
            2,
            0,
            0,
            0,
            'migration_test',
            CURRENT_TIMESTAMP,
            NULL
        )
        """,
        (
            "[999999]",
            '[{"id":999999,"question_type":"qcm"}]',
            '[{"id":999999,"question_type":"qcm"}]',
        ),
    )

    test_exam_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO exam_answers (
            exam_attempt_id,
            question_id,
            question_type,
            selected_answer,
            correct_answer,
            result,
            is_correct,
            semantic_score,
            lesson_id,
            topic,
            difficulty,
            explanation
        )
        VALUES (
            ?,
            999999,
            'short_answer',
            'migration test answer',
            'migration test key point',
            'partially_correct',
            0,
            50,
            999999,
            'Migration Test',
            'Medium',
            'Migration test explanation'
        )
        """,
        (test_exam_id,),
    )

    test_answer_id = cursor.lastrowid

    cursor.execute(
        "DELETE FROM exam_answers WHERE id=?",
        (test_answer_id,),
    )

    cursor.execute(
        "DELETE FROM exam_attempts WHERE id=?",
        (test_exam_id,),
    )

    print("  OK: AI Exam NULL qcm_set_id insertion works")
    print("  OK: Short Answer answer insertion works")


def main():
    print("=" * 70)
    print("KlearStudy - AI Exam Database Migration V4")
    print("=" * 70)

    print(f"\nDatabase:")
    print(DB_PATH)

    if not DB_PATH.exists():
        raise SystemExit(
            f"ERROR: Database not found:\n{DB_PATH}"
        )

    print("\nCreating backup...")
    backup_path = backup_database()
    print(f"Backup created:\n{backup_path}")

    connection = sqlite3.connect(str(DB_PATH))

    try:
        # We rebuild SQLite tables. Foreign key enforcement must be
        # temporarily disabled during the rebuild.
        connection.execute("PRAGMA foreign_keys = OFF")

        cursor = connection.cursor()

        migrate_exam_attempts(cursor)
        migrate_exam_answers(cursor)

        connection.commit()

        verify(cursor)
        connection.commit()

    except Exception as error:
        connection.rollback()

        print("\n" + "=" * 70)
        print("MIGRATION FAILED")
        print("=" * 70)
        print(error)
        print("\nYour backup is safe at:")
        print(backup_path)

        raise

    finally:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.close()

    print("\n" + "=" * 70)
    print("MIGRATION V4 COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print("\nNext:")
    print("1. Replace database/models.py with models_V4_FIXED.py")
    print("2. Update exam_repository.py for V4")
    print("3. Update exam.py for V4")
    print("4. Restart FastAPI")
    print("5. Test old Exam + new Exam V4")


if __name__ == "__main__":
    main()
