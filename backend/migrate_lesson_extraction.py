from sqlalchemy import inspect, text

from database.database import engine


# ============================================================
# KlearStudy — STEP 34C Database Migration
# ============================================================
#
# Adds extraction metadata columns to existing lessons table.
#
# IMPORTANT:
# This script DOES NOT delete the database.
# It only adds missing columns.
#
# ============================================================


TABLE_NAME = "lessons"


COLUMNS = {
    "extraction_method": (
        "ALTER TABLE lessons "
        "ADD COLUMN extraction_method VARCHAR(30)"
    ),

    "ocr_used": (
        "ALTER TABLE lessons "
        "ADD COLUMN ocr_used INTEGER NOT NULL DEFAULT 0"
    ),

    "extraction_pypdf_score": (
        "ALTER TABLE lessons "
        "ADD COLUMN extraction_pypdf_score INTEGER"
    ),

    "extraction_ocr_score": (
        "ALTER TABLE lessons "
        "ADD COLUMN extraction_ocr_score INTEGER"
    ),
}


def main():

    print("")
    print("=" * 70)
    print(
        "KlearStudy — STEP 34C Database Migration"
    )
    print("=" * 70)

    inspector = inspect(engine)

    tables = inspector.get_table_names()

    if TABLE_NAME not in tables:

        print("")
        print(
            "❌ Table 'lessons' was not found."
        )

        print(
            "Make sure KlearStudy database exists "
            "and the backend has been initialized."
        )

        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns(
            TABLE_NAME
        )
    }

    print("")
    print(
        "Existing lessons columns:"
    )

    for column in sorted(
        existing_columns
    ):

        print(
            f"  ✓ {column}"
        )

    added = 0
    skipped = 0

    print("")
    print(
        "Checking extraction metadata columns..."
    )

    with engine.begin() as connection:

        for column_name, sql in COLUMNS.items():

            if column_name in existing_columns:

                print(
                    f"  ⏭️ {column_name} "
                    f"already exists."
                )

                skipped += 1

                continue

            print(
                f"  ➕ Adding {column_name}..."
            )

            connection.execute(
                text(sql)
            )

            print(
                f"  ✅ Added {column_name}"
            )

            added += 1

    print("")
    print("=" * 70)

    print(
        f"Migration complete. "
        f"Added: {added}, "
        f"Skipped: {skipped}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    inspector = inspect(engine)

    final_columns = {
        column["name"]
        for column in inspector.get_columns(
            TABLE_NAME
        )
    }

    print("")
    print(
        "Verification:"
    )

    for column_name in COLUMNS:

        if column_name in final_columns:

            print(
                f"  ✅ {column_name}"
            )

        else:

            print(
                f"  ❌ {column_name} "
                f"NOT FOUND"
            )

    print("")
    print(
        "Database was NOT deleted."
    )


if __name__ == "__main__":
    main()