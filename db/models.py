"""
SQLAlchemy models -- these Python classes define the database tables.
Running the code at the bottom of this file (or importing Base.metadata
elsewhere) will create matching tables in Postgres if they don't exist yet.
"""

import uuid
from datetime import datetime, date

from sqlalchemy import Column, String, Integer, Boolean, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.connection import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    active = Column(Boolean, default=True)  # supports removing/deactivating a user later
    created_at = Column(DateTime, default=datetime.utcnow)

    entries = relationship("Entry", back_populates="profile")


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (
        # one entry per person per day -- prevents accidental double uploads
        UniqueConstraint("user_id", "entry_date", name="uq_user_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    entry_date = Column(Date, nullable=False, default=date.today)

    total_screenshot_url = Column(String, nullable=True)
    apps_screenshot_url = Column(String, nullable=True)

    total_minutes = Column(Integer, nullable=True)   # null until OCR'd/confirmed
    social_minutes = Column(Integer, nullable=True)

    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="entries")


class WeeklyResult(Base):
    __tablename__ = "weekly_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_number = Column(Integer, nullable=False)
    loser_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    forfeit_description = Column(String, nullable=True)
    completed = Column(Boolean, default=False)

    loser = relationship("Profile", foreign_keys=[loser_id])


class ChallengeSummary(Base):
    __tablename__ = "challenge_summary"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loser_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    total_score = Column(Integer, nullable=True)
    major_forfeit = Column(String, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    loser = relationship("Profile", foreign_keys=[loser_id])