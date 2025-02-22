from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.sql import func

Base = declarative_base()

# Association table for event participants
event_participants = Table(
    'event_participants',
    Base.metadata,
    Column('event_id', Integer, ForeignKey('events.id')),
    Column('participant_id', Integer, ForeignKey('participants.id'))
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
    
    events = relationship("Event", back_populates="calendar", cascade="all, delete-orphan")

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

class Event(Base):
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True)
    google_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    start_time = Column(String, nullable=False)  
    end_time = Column(String)  
    location = Column(String)
    calendar_id = Column(String, ForeignKey('calendars.id'), nullable=False)
    event_type = Column(String, nullable=False)
    category = Column(String, nullable=False)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String)
    last_synced = Column(String, default=lambda: datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M:%S.%f'))
    is_deleted = Column(Boolean, default=False)
    
    calendar = relationship("Calendar", back_populates="events")
    participants = relationship("Participant", back_populates="event", cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        # Convert datetime objects to strings for SQLite storage
        if 'start_time' in kwargs and isinstance(kwargs['start_time'], datetime):
            if kwargs['start_time'].tzinfo is None:
                kwargs['start_time'] = kwargs['start_time'].replace(tzinfo=ZoneInfo('America/Los_Angeles'))
            kwargs['start_time'] = kwargs['start_time'].strftime('%Y-%m-%d %H:%M:%S.%f')
            
        if 'end_time' in kwargs and kwargs['end_time']:
            if isinstance(kwargs['end_time'], datetime):
                if kwargs['end_time'].tzinfo is None:
                    kwargs['end_time'] = kwargs['end_time'].replace(tzinfo=ZoneInfo('America/Los_Angeles'))
                kwargs['end_time'] = kwargs['end_time'].strftime('%Y-%m-%d %H:%M:%S.%f')
                
        super().__init__(**kwargs)
    
    @property
    def start_time_local(self):
        """Get start time in local timezone"""
        if self.start_time:
            dt = datetime.strptime(self.start_time, '%Y-%m-%d %H:%M:%S.%f')
            return dt.replace(tzinfo=ZoneInfo('America/Los_Angeles'))
        return None
    
    @property
    def end_time_local(self):
        """Get end time in local timezone"""
        if self.end_time:
            dt = datetime.strptime(self.end_time, '%Y-%m-%d %H:%M:%S.%f')
            return dt.replace(tzinfo=ZoneInfo('America/Los_Angeles'))
        return None

class Participant(Base):
    __tablename__ = 'participants'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String)
    
    event = relationship("Event", back_populates="participants")

class SyncState(Base):
    __tablename__ = 'sync_state'
    
    id = Column(Integer, primary_key=True)
    calendar_id = Column(String, nullable=False, unique=True)
    last_sync_token = Column(String)
    last_synced = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo('America/Los_Angeles')))
    full_sync_needed = Column(Boolean, default=True)
