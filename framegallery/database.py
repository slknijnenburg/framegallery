from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import framegallery.config

SQLALCHEMY_DATABASE_URL = framegallery.config.settings.db_url

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
