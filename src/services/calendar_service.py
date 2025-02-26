from datetime import datetime
from typing import List, Optional
from src.models.calendar import Calendar
from src.models.event import CalendarEvent
from src.nlp.processor import NLPProcessor

class CalendarService:
    def __init__(self, db_manager, nlp_processor: NLPProcessor):
        self.db_manager = db_manager
        self.nlp_processor = nlp_processor

    async def get_calendar(self, calendar_id: str) -> Optional[Calendar]:
        """Get a calendar by ID"""
        with self.db_manager.get_session() as session:
            return session.query(Calendar).filter_by(id=calendar_id).first()

    async def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get an event by ID"""
        with self.db_manager.get_session() as session:
            return session.query(CalendarEvent).filter_by(id=event_id).first()

    async def create_event(self, event_data: dict) -> CalendarEvent:
        """Create a new calendar event"""
        with self.db_manager.get_session() as session:
            event = CalendarEvent(**event_data)
            session.add(event)
            session.commit()
            session.refresh(event)
            return event

    async def update_event(self, event_id: str, event_data: dict) -> Optional[CalendarEvent]:
        """Update an existing calendar event"""
        with self.db_manager.get_session() as session:
            event = session.query(CalendarEvent).filter_by(id=event_id).first()
            if not event:
                return None

            for key, value in event_data.items():
                setattr(event, key, value)

            session.commit()
            session.refresh(event)
            return event

    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event"""
        with self.db_manager.get_session() as session:
            event = session.query(CalendarEvent).filter_by(id=event_id).first()
            if not event:
                return False

            session.delete(event)
            session.commit()
            return True
