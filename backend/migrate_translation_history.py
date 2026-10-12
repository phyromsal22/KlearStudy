from sqlalchemy import text

from database.database import engine


def migrate_translation_history():
    print("=" * 60)
    print("STEP 39.2 — TRANSLATION HISTORY MIGRATION")
    print("=" * 60)

    with engine.begin() as conn:

        # Check existing columns
        result = conn.execute(
            text("PRAGMA table_info(translation_history)")
        )

        columns = [row[1] for row in result.fetchall()]

        print("\nExisting columns:")
        for column in columns:
            print(f"  - {column}")

        # Add translation_type
        if "translation_type" not in columns:
            print("\nAdding translation_type...")

            conn.execute(
                text(
                    """
                    ALTER TABLE translation_history
                    ADD COLUMN translation_type
                    VARCHAR(20)
                    NOT NULL
                    DEFAULT 'text'
                    """
                )
            )

            print("✅ translation_type added")
        else:
            print("\n✅ translation_type already exists")

        # Add lesson_id
        if "lesson_id" not in columns:
            print("\nAdding lesson_id...")

            conn.execute(
                text(
                    """
                    ALTER TABLE translation_history
                    ADD COLUMN lesson_id
                    INTEGER
                    """
                )
            )

            print("✅ lesson_id added")
        else:
            print("\n✅ lesson_id already exists")

        # Verify
        result = conn.execute(
            text("PRAGMA table_info(translation_history)")
        )

        final_columns = [row[1] for row in result.fetchall()]

        print("\nFinal columns:")

        for column in final_columns:
            print(f"  - {column}")

    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    migrate_translation_history()