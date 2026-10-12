import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# Absolute path to the backend database.
# This prevents SQLite from opening a different database
# depending on the terminal's current working directory.
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "klearstudy.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

print("=" * 60)
print("KlearStudy Database Configuration")
print("=" * 60)
print(f"Database URL: {DATABASE_URL}")
print(f"Database Path: {DATABASE_PATH}")
print(f"Database Exists: {DATABASE_PATH.exists()}")
print("=" * 60)


# ============================================================
# DATABASE ENGINE
# ============================================================

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
    pool_pre_ping=True,
)


# ============================================================
# SESSION
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ============================================================
# BASE MODEL
# ============================================================

Base = declarative_base()


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()