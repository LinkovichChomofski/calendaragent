from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from src.models.calendar import Calendar
from src.integrations.google_calendar import GoogleCalendarClient
import logging

logger = logging.getLogger(__name__)

class CalendarManager:
    def __init__(self):
        self.google_client = GoogleCalendarClient()

    def sync_calendars(self, session: Session) -> List[Dict]:
        """Sync calendars from Google Calendar to local database."""
        try:
            # Get calendars from Google
            google_calendars = self.google_client.get_calendar_list()
            
            # Update local database
            for cal_data in google_calendars:
                calendar = session.query(Calendar).filter(Calendar.id == cal_data['id']).first()
                
                if calendar:
                    # Update existing calendar
                    calendar.summary = cal_data['summary']
                    calendar.description = cal_data.get('description')
                    calendar.time_zone = cal_data['timeZone']
                    calendar.background_color = cal_data.get('backgroundColor')
                    calendar.foreground_color = cal_data.get('foregroundColor')
                    calendar.access_role = cal_data['accessRole']
                    calendar.is_primary = cal_data.get('primary', False)
                else:
                    # Create new calendar
                    calendar = Calendar(
                        id=cal_data['id'],
                        summary=cal_data['summary'],
                        description=cal_data.get('description'),
                        time_zone=cal_data['timeZone'],
                        background_color=cal_data.get('backgroundColor'),
                        foreground_color=cal_data.get('foregroundColor'),
                        access_role=cal_data['accessRole'],
                        is_primary=cal_data.get('primary', False)
                    )
                    session.add(calendar)
            
            session.commit()
            return [cal.to_dict() for cal in session.query(Calendar).all()]
            
        except Exception as e:
            logger.error(f"Error syncing calendars: {str(e)}")
            session.rollback()
            raise

    def get_calendars(self, session: Session) -> List[Dict]:
        """Get all calendars from local database."""
        try:
            calendars = session.query(Calendar).all()
            return [cal.to_dict() for cal in calendars]
        except Exception as e:
            logger.error(f"Error getting calendars: {str(e)}")
            raise

    def get_calendar(self, session: Session, calendar_id: str) -> Optional[Dict]:
        """Get a specific calendar from local database."""
        try:
            calendar = session.query(Calendar).filter(Calendar.id == calendar_id).first()
            return calendar.to_dict() if calendar else None
        except Exception as e:
            logger.error(f"Error getting calendar {calendar_id}: {str(e)}")
            raise

    def add_calendar(self, session: Session, calendar_id: str) -> Dict:
        """Add a new calendar to both Google Calendar and local database."""
        try:
            # Add to Google Calendar
            google_calendar = self.google_client.add_calendar(calendar_id)
            
            # Add to local database
            calendar = Calendar(
                id=google_calendar['id'],
                summary=google_calendar['summary'],
                description=google_calendar.get('description'),
                time_zone=google_calendar['timeZone'],
                background_color=google_calendar.get('backgroundColor'),
                foreground_color=google_calendar.get('foregroundColor'),
                access_role=google_calendar['accessRole'],
                is_primary=google_calendar.get('primary', False)
            )
            
            session.add(calendar)
            session.commit()
            
            return calendar.to_dict()
        except Exception as e:
            logger.error(f"Error adding calendar {calendar_id}: {str(e)}")
            session.rollback()
            raise

    def remove_calendar(self, session: Session, calendar_id: str) -> bool:
        """Remove a calendar from both Google Calendar and local database."""
        try:
            # Remove from Google Calendar
            self.google_client.remove_calendar(calendar_id)
            
            # Remove from local database
            calendar = session.query(Calendar).filter(Calendar.id == calendar_id).first()
            if calendar:
                session.delete(calendar)
                session.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error removing calendar {calendar_id}: {str(e)}")
            session.rollback()
            raise

    def update_calendar_colors(self, session: Session, calendar_id: str, 
                             background_color: str = None, foreground_color: str = None) -> Dict:
        """Update calendar colors in both Google Calendar and local database."""
        try:
            # Update in Google Calendar
            google_calendar = self.google_client.update_calendar_colors(
                calendar_id, background_color, foreground_color
            )
            
            # Update in local database
            calendar = session.query(Calendar).filter(Calendar.id == calendar_id).first()
            if calendar:
                if background_color:
                    calendar.background_color = background_color
                if foreground_color:
                    calendar.foreground_color = foreground_color
                session.commit()
                
            return calendar.to_dict() if calendar else None
        except Exception as e:
            logger.error(f"Error updating calendar colors for {calendar_id}: {str(e)}")
            session.rollback()
            raise
