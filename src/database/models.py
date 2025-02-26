from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.sql import func
from .base import Base

# Association table for event participants
calendar_event_participants = Table('calendar_event_participants', Base.metadata,
    Column('event_id', String, ForeignKey('calendar_events.id')),
    Column('participant_id', String, ForeignKey('calendar_participants.id'))
)

class Calendar(Base):
    __tablename__ = 'calendars'

    id = Column(String, primary_key=True)
    summary = Column(String)
    description = Column(String, nullable=True)
    time_zone = Column(String)
    background_color = Column(String, nullable=True)
    foreground_color = Column(String, nullable=True)
    access_role = Column(String)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    events = relationship("CalendarEvent", back_populates="calendar", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'summary': self.summary,
            'description': self.description,
            'timeZone': self.time_zone,
            'backgroundColor': self.background_color,
            'foregroundColor': self.foreground_color,
            'accessRole': self.access_role,
            'primary': self.is_primary,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

class CalendarEvent(Base):
    __tablename__ = 'calendar_events'
    
    id = Column(String, primary_key=True)
    google_id = Column(String, unique=True, nullable=True)  # Only set for Google Calendar events
    title = Column(String, nullable=False)
    description = Column(String)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    location = Column(String)
    calendar_id = Column(String, ForeignKey('calendars.id'), nullable=True)  # Optional calendar association
    source = Column(String, nullable=False)  # 'google', 'outlook', etc.
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String)
    last_synced = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Los_Angeles')))
    is_deleted = Column(Boolean, default=False)
    
    calendar = relationship("Calendar", back_populates="events")
    attendees = relationship("CalendarParticipant", secondary=calendar_event_participants)
    
    def to_dict(self):
        return {
            'id': self.id,
            'google_id': self.google_id,
            'title': self.title,
            'description': self.description,
            'start': self.start.isoformat() if self.start else None,
            'end': self.end.isoformat() if self.end else None,
            'location': self.location,
            'calendar_id': self.calendar_id,
            'source': self.source,
            'is_recurring': self.is_recurring,
            'recurrence_pattern': self.recurrence_pattern,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None,
            'is_deleted': self.is_deleted,
            'attendees': [a.to_dict() for a in self.attendees] if self.attendees else []
        }

class CalendarParticipant(Base):
    __tablename__ = 'calendar_participants'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email
        }

class SyncState(Base):
    __tablename__ = 'sync_state'

    id = Column(Integer, primary_key=True)
    calendar_id = Column(String, nullable=False, unique=True)
    last_sync_token = Column(String)
    last_synced = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Los_Angeles')))
    full_sync_needed = Column(Boolean, default=True)
