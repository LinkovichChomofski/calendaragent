from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from zoneinfo import ZoneInfo

from src.models.base import Base

class CalendarEvent(Base):
    """SQLAlchemy model for calendar events"""
    __tablename__ = 'calendar_events'

    id = Column(String, primary_key=True)
    google_id = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start = Column(DateTime(timezone=True), nullable=False)
    end = Column(DateTime(timezone=True), nullable=False)
    location = Column(String, nullable=True)
    source = Column(String, nullable=False)  # google/outlook
    calendar_id = Column(String, ForeignKey('calendars.id'), nullable=False)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String, nullable=True)
    last_synced = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Los_Angeles')))
    is_deleted = Column(Boolean, default=False)

    calendar = relationship("Calendar", back_populates="events")

    def to_dict(self):
        return {
            'id': self.id,
            'google_id': self.google_id,
            'title': self.title,
            'start': self.start.isoformat() if self.start else None,
            'end': self.end.isoformat() if self.end else None,
            'description': self.description,
            'location': self.location,
            'source': self.source,
            'calendar_id': self.calendar_id,
            'is_recurring': self.is_recurring,
            'recurrence_pattern': self.recurrence_pattern,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None,
            'is_deleted': self.is_deleted
        }

class CalendarEventPydantic(BaseModel):
    """Pydantic model for API request/response validation"""
    id: Optional[str]
    title: str
    start: datetime
    end: datetime
    description: Optional[str]
    location: Optional[str]
    attendees: List[str]
    source: str  # google/outlook
    is_recurring: Optional[bool] = False
    recurrence_pattern: Optional[str] = None
    last_synced: Optional[datetime] = None
    is_deleted: Optional[bool] = False
    
    def to_json(self):
        return self.json()

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'start': self.start,
            'end': self.end,
            'description': self.description,
            'location': self.location,
            'attendees': self.attendees,
            'source': self.source,
            'is_recurring': self.is_recurring,
            'recurrence_pattern': self.recurrence_pattern,
            'last_synced': self.last_synced,
            'is_deleted': self.is_deleted
        }
