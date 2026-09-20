"""
Run this once to create all tables in the connected Postgres database,
based on the models defined in db/models.py.
"""

from db.connection import engine, Base
from db import models  # noqa: F401 -- must be imported so Base knows about these tables

Base.metadata.create_all(bind=engine)
print("Tables created (or already existed).")