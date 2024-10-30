import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import framegallery.config

# base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
# SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(base_dir, 'sql_app.db')}"

print(framegallery.config.settings.db_url)

SQLALCHEMY_DATABASE_URL = framegallery.config.settings.db_url

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()