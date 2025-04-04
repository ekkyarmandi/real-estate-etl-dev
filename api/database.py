"""
Database connection setup (Synchronous).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from decouple import config

DATABASE_URL = config("DB_URL", default=None)
if not DATABASE_URL:
    raise ValueError("DB_URL environment variable not set or empty.")


def get_db() -> Session:
    """
    Dependency function that yields a synchronous Session.
    Ensures the session is closed afterwards.
    """
    engine = create_engine(DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_checker_db() -> Session:
    """
    Dependency function that yields a synchronous Session.
    Ensures the session is closed afterwards.
    """
    engine = create_engine(
        "postgresql://postgres:QelXrdrXWKwzVdkPRoHiDAAMHoGdPDkb@autorack.proxy.rlwy.net:33614/railway",
        echo=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
