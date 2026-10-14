import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# 1. ព្យាយាមអាន DATABASE_URL ពី Environment Variable ជាមុនសិន
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # 2. កែសម្រួល URL ពី postgres:// ទៅជា postgresql:// (សម្រាប់ SQLAlchemy)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    print("=" * 60)
    print("KlearStudy Database Configuration (PostgreSQL)")
    print("=" * 60)
    print("Database URL: [HIDDEN FOR SECURITY]")
    print("=" * 60)
else:
    # 3. បើគ្មាន Environment Variable ទេ ប្រើ SQLite សម្រាប់ការអភិវឌ្ឍន៍ក្នុងតំបន់
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATABASE_PATH = BASE_DIR / "klearstudy.db"
    DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

    print("=" * 60)
    print("KlearStudy Database Configuration (SQLite)")
    print("=" * 60)
    print(f"Database URL: {DATABASE_URL}")
    print(f"Database Path: {DATABASE_PATH}")
    print(f"Database Exists: {DATABASE_PATH.exists()}")
    print("=" * 60)


# ============================================================
# DATABASE ENGINE
# ============================================================

if DATABASE_URL.startswith("sqlite"):
    # ការកំណត់ពិសេសសម្រាប់ SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },
        pool_pre_ping=True,
    )
else:
    # ការកំណត់សម្រាប់ PostgreSQL
    engine = create_engine(
        DATABASE_URL,
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