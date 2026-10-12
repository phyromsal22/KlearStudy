from database.database import engine


def column_exists(
    connection,
    table_name: str,
    column_name: str,
) -> bool:

    result = connection.exec_driver_sql(
        f"PRAGMA table_info({table_name})"
    )

    columns = result.fetchall()

    for column in columns:

        # SQLite PRAGMA table_info:
        # (cid, name, type, notnull, dflt_value, pk)

        if column[1] == column_name:
            return True

    return False


def main():

    print("=" * 60)
    print("KlearStudy STEP 16 Database Migration")
    print("=" * 60)

    print()
    print("Database table: qcm_questions")
    print()

    with engine.begin() as connection:

        # ==================================================
        # CHECK TOPIC
        # ==================================================

        if column_exists(
            connection,
            "qcm_questions",
            "topic",
        ):

            print(
                "ℹ️ topic column already exists."
            )

        else:

            print(
                "➕ Adding topic column..."
            )

            connection.exec_driver_sql(
                """
                ALTER TABLE qcm_questions
                ADD COLUMN topic VARCHAR(255)
                """
            )

            print(
                "✅ topic column added."
            )

        # ==================================================
        # CHECK DIFFICULTY
        # ==================================================

        if column_exists(
            connection,
            "qcm_questions",
            "difficulty",
        ):

            print(
                "ℹ️ difficulty column already exists."
            )

        else:

            print(
                "➕ Adding difficulty column..."
            )

            connection.exec_driver_sql(
                """
                ALTER TABLE qcm_questions
                ADD COLUMN difficulty VARCHAR(20)
                """
            )

            print(
                "✅ difficulty column added."
            )

    # ==================================================
    # VERIFY
    # ==================================================

    print()
    print("Verifying database...")
    print()

    with engine.connect() as connection:

        result = connection.exec_driver_sql(
            "PRAGMA table_info(qcm_questions)"
        )

        columns = result.fetchall()

        print(
            "qcm_questions columns:"
        )

        for column in columns:

            print(
                f"  - {column[1]} "
                f"({column[2]})"
            )

        topic_exists = column_exists(
            connection,
            "qcm_questions",
            "topic",
        )

        difficulty_exists = column_exists(
            connection,
            "qcm_questions",
            "difficulty",
        )

    print()

    if (
        topic_exists
        and difficulty_exists
    ):

        print(
            "✅ MIGRATION SUCCESSFUL"
        )

        print(
            "✅ topic column exists"
        )

        print(
            "✅ difficulty column exists"
        )

    else:

        print(
            "❌ MIGRATION FAILED"
        )

        if not topic_exists:
            print(
                "❌ topic column is missing"
            )

        if not difficulty_exists:
            print(
                "❌ difficulty column is missing"
            )

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()