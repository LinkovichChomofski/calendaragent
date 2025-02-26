from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from src.models.base import Base

class Calendar(Base):
    __tablename__ = 'calendars'

    id = Column(String, primary_key=True)
    google_id = Column(String, unique=True)
    name = Column(String, nullable=False)
    owner_email = Column(String, nullable=False)
    last_synced = Column(DateTime(timezone=True))
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    events = relationship("CalendarEvent", back_populates="calendar", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'google_id': self.google_id,
            'name': self.name,
            'owner_email': self.owner_email,
            'last_synced': self.last_synced,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
