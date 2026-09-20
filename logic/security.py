"""
Shared password hashing utilities -- used by both create_users.py (when
creating accounts) and the login route (when checking a submitted
password). Keeping this in one place means both always agree on exactly
how passwords are hashed and checked.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)