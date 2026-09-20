"""
Run this ONCE to create the 5 initial accounts for the challenge.
Passwords are hashed with bcrypt before being stored -- never saved as
plain text.

Edit the USERS list below with real display names, usernames, and
temporary passwords before running. Change is_admin=True for exactly
one person (yourself).
"""

from passlib.context import CryptContext

from db.connection import SessionLocal
from db.models import Profile

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# EDIT THIS before running -- replace with your real group's info.
USERS = [
    {"display_name": "Abhijit", "username": "Abhijit", "password": "abhipoondu", "is_admin": False},
    {"display_name": "Dhwarakesh", "username": "Dhwarakesh", "password": "genjaboy", "is_admin": False},
    {"display_name": "Karti", "username": "Karti", "password": "ganesh", "is_admin": False},
    {"display_name": "Hari", "username": "Hari", "password": "ultralaggy", "is_admin": False},
    {"display_name": "Anirudh", "username": "Anirudh", "password": "soulsniper", "is_admin": True},
]


def main():
    db = SessionLocal()
    try:
        for user in USERS:
            hashed = pwd_context.hash(user["password"])
            profile = Profile(
                display_name=user["display_name"],
                username=user["username"],
                password_hash=hashed,
                is_admin=user["is_admin"],
            )
            db.add(profile)
        db.commit()
        print(f"Created {len(USERS)} user accounts.")
    except Exception as e:
        db.rollback()
        print("Failed to create users:")
        print(e)
    finally:
        db.close()


if __name__ == "__main__":
    main()