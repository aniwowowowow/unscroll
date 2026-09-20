"""
Sets up the SQLAlchemy engine and session factory used throughout the app
to talk to the RDS Postgres database.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found -- check your .env file")

# SQLAlchemy needs to know explicitly to use the pg8000 driver rather than
# psycopg2 (its default assumption for postgres:// URLs). We do this by
# rewriting the URL's scheme from "postgresql://" to "postgresql+pg8000://".
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency: provides a database session to a route function,
    and guarantees it gets closed afterward even if an error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()