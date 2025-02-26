from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import Base

class CalendarEvent(Base):
    __tablename__ = 'calendar_events'

    id = Column(String, primary_key=True)
    google_id = Column(String)
    title = Column(String, nullable=False)
    description = Column(String)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    location = Column(String)
    calendar_id = Column(String, ForeignKey('calendars.id'), nullable=False)
    source = Column(String, nullable=False)  # google/outlook
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String)
    last_synced = Column(DateTime)
    is_deleted = Column(Boolean, default=False)

    calendar = relationship("Calendar", back_populates="events")
