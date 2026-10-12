from database.database import engine
from sqlalchemy import inspect

print("=" * 60)
print("KlearStudy Database Diagnostic")
print("=" * 60)

print(f"Database URL: {engine.url}")

inspector = inspect(engine)
tables = inspector.get_table_names()

print("\nTables found:")
for table in tables:
    print(f"- {table}")

if "exam_attempts" not in tables:
    print("\nERROR: exam_attempts table not found.")
else:
    columns = inspector.get_columns("exam_attempts")

    print("\nexam_attempts columns:")
    for column in columns:
        print(f"- {column['name']} ({column['type']})")

    has_user_id = any(
        column["name"] == "user_id"
        for column in columns
    )

    print(f"\nuser_id exists: {has_user_id}")
    