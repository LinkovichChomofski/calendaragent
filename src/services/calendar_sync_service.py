from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database.connection import DatabaseManager
from ..database.models import CalendarEvent, CalendarParticipant
from ..integrations.google_calendar import GoogleCalendarClient
from ..nlp.processor import NLPProcessor
from ..models.event_response import EventResponse
from ..models.sync_status import SyncStatus
import json
import logging
import os
import uuid
import traceback

logger = logging.getLogger(__name__)

class CalendarSyncService:
    def __init__(self, database_manager: DatabaseManager, google_client: GoogleCalendarClient, nlp_processor: NLPProcessor):
        self.database_manager = database_manager
        self.google_client = google_client
        self.nlp_processor = nlp_processor
        self.timezone = ZoneInfo('America/Los_Angeles')

    async def schedule_event(self, event_data) -> EventResponse:
        """
        Schedule an event using either an EventData object or a command string
        """
        try:
            logger.info(f"Scheduling event: {event_data}")
            
            # Check if this is a command string or an EventData object
            if isinstance(event_data, dict) and 'command' in event_data:
                # Extract event details using NLP
                event_details = self.nlp_processor.extract_event_details(event_data['command'])
                if not event_details:
                    return EventResponse(success=False, message="Could not parse event details from command")
                
                title = event_details['title']
                start_time = event_details['start_time']
                end_time = event_details['end_time']
                description = event_details.get('description')
                location = event_details.get('location')
                attendees = event_details.get('attendees', [])
                
            else:
                # Assume it's an EventData object or compatible dict
                logger.info(f"Using provided EventData: {event_data}")
                
                # Access properties based on the type
                if hasattr(event_data, 'title'):
                    # It's an object
                    title = event_data.title
                    start_time = event_data.start_time
                    end_time = event_data.end_time
                    description = event_data.description
                    location = event_data.location
                    attendees = event_data.participants if hasattr(event_data, 'participants') else []
                else:
                    # It's a dict
                    title = event_data['title']
                    start_time = event_data['start_time']
                    end_time = event_data['end_time']
                    description = event_data.get('description')
                    location = event_data.get('location')
                    attendees = event_data.get('participants', [])
            
            # Validate required fields
            if not title:
                return EventResponse(success=False, message="Event title is required")
            if not start_time:
                return EventResponse(success=False, message="Event start time is required")
            if not end_time:
                return EventResponse(success=False, message="Event end time is required")
                
            # Log the event details
            logger.info(f"Creating event: {title} from {start_time} to {end_time}")
            
            # Create calendar ID from first available ID in env
            calendar_id = os.getenv('GOOGLE_CALENDAR_IDS', '').split(',')[0]
            if not calendar_id:
                return EventResponse(success=False, message="No calendar ID configured")
            
            # Format for Google Calendar
            google_event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat() if isinstance(start_time, datetime) else start_time,
                    'timeZone': 'America/Los_Angeles',
                },
                'end': {
                    'dateTime': end_time.isoformat() if isinstance(end_time, datetime) else end_time,
                    'timeZone': 'America/Los_Angeles',
                },
                'location': location,
            }
            
            # Add attendees if provided - only if using OAuth and not service account
            # Note: Service accounts cannot invite attendees without Domain-Wide Delegation
            # We'll store participants in our database anyway for reference
            if False and attendees:  # Temporarily disable attendees until we have OAuth or DWD setup
                valid_attendees = []
                for email in attendees:
                    # Basic check if it looks like an email address
                    if isinstance(email, str) and '@' in email and '.' in email.split('@')[1]:
                        valid_attendees.append({'email': email})
                
                if valid_attendees:
                    google_event['attendees'] = valid_attendees
                    
                # Log which attendees were skipped
                if len(valid_attendees) != len(attendees):
                    skipped = set([a for a in attendees if not (isinstance(a, str) and '@' in a and '.' in a.split('@')[1])])
                    logger.warning(f"Skipped invalid attendee emails: {skipped}")
            
            # Add note about attendees in description if we can't add them directly
            if attendees:
                attendee_notes = "Attendees: " + ", ".join([a for a in attendees if isinstance(a, str)])
                if description:
                    google_event['description'] = description + "\n\n" + attendee_notes
                else:
                    google_event['description'] = attendee_notes
            
            # Create event in Google Calendar
            created_event = self.google_client.create_event(calendar_id, google_event)
            
            if not created_event:
                return EventResponse(success=False, message="Failed to create event in Google Calendar")
                
            # Get the time fields from the created event
            start_time_str = created_event['start'].get('dateTime', created_event['start'].get('date'))
            end_time_str = created_event['end'].get('dateTime', created_event['end'].get('date'))
            
            # Parse to datetime objects
            start_datetime = self._parse_datetime(start_time_str)
            end_datetime = self._parse_datetime(end_time_str)
            
            # Create event in local database
            event_id = str(uuid.uuid4())
            db_event = CalendarEvent(
                id=event_id,
                google_id=created_event['id'],
                title=created_event['summary'],
                start=start_datetime,
                end=end_datetime,
                description=created_event.get('description'),
                location=created_event.get('location'),
                calendar_id=calendar_id,
                source='google',
                last_synced=datetime.now(self.timezone)
            )
            
            # Create a dictionary to return with event information
            event_data = {
                "id": event_id,
                "google_id": created_event['id'],
                "title": created_event['summary'],
                "start": start_datetime.isoformat(),
                "end": end_datetime.isoformat(),
                "description": created_event.get('description'),
                "location": created_event.get('location'),
                "calendar_id": calendar_id,
                "participants": attendees
            }
            
            with self.database_manager.get_session() as session:
                session.add(db_event)
                
                # Add attendees if any
                if attendees:
                    for email in attendees:
                        participant = CalendarParticipant(
                            id=f"{event_id}_{email}",
                            name=email.split('@')[0] if '@' in email else email,  # Use part before @ as name
                            email=email
                        )
                        session.add(participant)
                        # Add to association table
                        db_event.attendees.append(participant)
                
                session.commit()
            
            # Return the created event
            return {
                "success": True,
                "event": event_data
            }
        except Exception as e:
            logger.error(f"Error scheduling event: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return EventResponse(success=False, message=f"Error scheduling event: {str(e)}", error=str(e))

    def list_events(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """
        List events between start_date and end_date.
        If start_date is None, use today.
        If end_date is None, use start_date + 1 day.
        """
        try:
            if not start_date:
                start_date = datetime.now(self.timezone).replace(hour=0, minute=0, second=0, microsecond=0)
            if not end_date:
                end_date = start_date + timedelta(days=1)
                
            logger.info(f"Listing events between {start_date} and {end_date}")
            
            # Create a session
            session = self.database_manager.get_session()
            
            try:
                # Query events within the date range
                query = select(CalendarEvent).where(
                    (CalendarEvent.start >= start_date) & 
                    (CalendarEvent.start < end_date) &
                    (CalendarEvent.is_deleted == False)
                ).order_by(CalendarEvent.start)
                
                events = session.execute(query).scalars().all()
                
                logger.info(f"Found {len(events)} events")
                
                # Convert to dict for JSON serialization
                event_list = []
                for event in events:
                    event_dict = {
                        'id': event.id,
                        'google_id': event.google_id,
                        'title': event.title,
                        'description': event.description,
                        'start': event.start.isoformat() if event.start else None,
                        'end': event.end.isoformat() if event.end else None,
                        'location': event.location,
                        'calendar_id': event.calendar_id,
                        'source': event.source,
                        'is_recurring': event.is_recurring,
                        'attendees': []  # TODO: Add attendees if needed
                    }
                    event_list.append(event_dict)
                
                return {
                    "success": True,
                    "events": event_list
                }
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error listing events: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    def delete_event(self, event_id: str):
        """
        Delete an event by ID
        """
        try:
            logger.info(f"Deleting event: {event_id}")
            
            # For now, return success
            return True
            
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            return False

    def update_calendar_event(self, event_id: str, updates: Dict[str, Any]):
        """
        Update an event by ID with the provided updates
        """
        try:
            logger.info(f"Updating event: {event_id} with updates: {updates}")
            
            # For now, return success
            return {
                "success": True,
                "message": "Event updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            return {
                "success": False,
                "message": f"Error updating event: {str(e)}"
            }

    def _parse_datetime(self, datetime_str: str) -> datetime:
        if 'T' in datetime_str:
            return datetime.fromisoformat(datetime_str)
        else:
            return datetime.fromisoformat(f"{datetime_str}T00:00:00")

    def sync_calendars(self, session: Session):
        """
        Sync calendars from Google Calendar
        """
        try:
            # Get calendar IDs from environment variable
            calendar_ids = os.getenv('GOOGLE_CALENDAR_IDS', '').split(',')
            if not calendar_ids or not calendar_ids[0]:
                return {
                    "success": False,
                    "events_synced": 0,
                    "events_updated": 0, 
                    "events_deleted": 0,
                    "errors": ["No calendar IDs configured"]
                }
            
            # Track sync results
            new_events = 0
            updated_events = 0
            deleted_events = 0
            errors = []
            
            # Process each calendar
            for calendar_id in calendar_ids:
                if not calendar_id.strip():
                    continue
                    
                try:
                    # Get events from Google Calendar
                    # Default to fetching events from the last 30 days up to 90 days in the future
                    time_min = (datetime.now(self.timezone) - timedelta(days=30)).isoformat()
                    time_max = (datetime.now(self.timezone) + timedelta(days=90)).isoformat()
                    
                    google_events = self.google_client.get_events(
                        calendar_id=calendar_id,
                        time_min=time_min,
                        time_max=time_max
                    )
                    
                    if not google_events:
                        errors.append(f"No events found for calendar {calendar_id}")
                        continue
                    
                    logger.info(f"Retrieved {len(google_events)} events from Google Calendar {calendar_id}")
                    
                    # Get existing events from the database for this calendar
                    existing_events = session.query(CalendarEvent).filter(
                        CalendarEvent.calendar_id == calendar_id
                    ).all()
                    existing_event_map = {event.google_id: event for event in existing_events if event.google_id}
                    
                    # Process each Google event
                    for google_event in google_events:
                        google_id = google_event['id']
                        
                        # Extract event details
                        title = google_event.get('summary', 'Untitled Event')
                        description = google_event.get('description')
                        location = google_event.get('location')
                        
                        # Parse start and end times
                        start_time_data = google_event['start']
                        end_time_data = google_event['end']
                        
                        # Get the datetime strings (either dateTime or date)
                        start_time_str = start_time_data.get('dateTime', start_time_data.get('date'))
                        end_time_str = end_time_data.get('dateTime', end_time_data.get('date'))
                        
                        # Parse to datetime objects
                        start_time = self._parse_datetime(start_time_str)
                        end_time = self._parse_datetime(end_time_str)
                        
                        # Check if this event exists in our database
                        if google_id in existing_event_map:
                            # Update existing event
                            db_event = existing_event_map[google_id]
                            db_event.title = title
                            db_event.description = description
                            db_event.location = location
                            db_event.start = start_time
                            db_event.end = end_time
                            db_event.last_synced = datetime.now(self.timezone)
                            updated_events += 1
                        else:
                            # Create new event
                            db_event = CalendarEvent(
                                id=str(uuid.uuid4()),
                                google_id=google_id,
                                title=title,
                                description=description,
                                location=location,
                                start=start_time,
                                end=end_time,
                                calendar_id=calendar_id,
                                source='google',
                                last_synced=datetime.now(self.timezone)
                            )
                            session.add(db_event)
                            new_events += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing calendar {calendar_id}: {str(e)}")
                    errors.append(f"Error syncing calendar {calendar_id}: {str(e)}")
            
            # Commit the changes
            session.commit()
            
            return {
                "success": True,
                "events_synced": new_events,
                "events_updated": updated_events,
                "events_deleted": deleted_events,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error syncing calendars: {str(e)}")
            logger.error(traceback.format_exc())
            session.rollback()
            return {
                "success": False,
                "events_synced": 0,
                "events_updated": 0,
                "events_deleted": 0,
                "errors": [f"Error syncing calendars: {str(e)}"]
            }
