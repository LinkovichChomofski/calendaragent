from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from ..database.connection import DatabaseManager
from ..database.models import Event, Participant, SyncState
from ..integrations.google_calendar import GoogleCalendarClient
from ..nlp.processor import NLPProcessor
from ..models.event_response import EventResponse
import logging
import os
from datetime import timezone as tz

logger = logging.getLogger(__name__)

class CalendarSyncService:
    def __init__(self, db_manager: DatabaseManager = None, config: dict = None):
        self.db = db_manager or DatabaseManager()
        self.google_client = GoogleCalendarClient(config=config)
        self.nlp = NLPProcessor()
        self.timezone = ZoneInfo('America/Los_Angeles')
        self.config = config or {}
        
        # Initialize database if needed
        self.db.init_database()
        
    def _get_default_calendar_id(self) -> str:
        """Get the default calendar ID from config"""
        if 'calendar_ids' in self.config:
            return self.config['calendar_ids'][0]
        return os.getenv('GOOGLE_CALENDAR_IDS', '').split(',')[0]

    def sync_calendar(self, calendar_id: str = None, time_min: datetime = None, time_max: datetime = None) -> Dict[str, Any]:
        """Sync calendar events"""
        try:
            # Get calendar ID if not provided
            if not calendar_id:
                calendar_id = self._get_default_calendar_id()
                if not calendar_id:
                    raise ValueError("No calendar ID configured")
                    
            logger.info(f"Starting calendar sync for {calendar_id}")
            
            # For service accounts, we need to try accessing the calendar through calendarList
            try:
                calendars = self.google_client.get_calendar_list()
                logger.info(f"Retrieved calendar list: {calendars}")
                calendar_info = next((cal for cal in calendars if cal['id'] == calendar_id), None)
                
                if not calendar_info:
                    logger.info(f"Calendar {calendar_id} not found in list, attempting to add it")
                    if self.google_client.add_calendar_to_list(calendar_id):
                        # Refresh calendar list
                        calendars = self.google_client.get_calendar_list()
                        calendar_info = next((cal for cal in calendars if cal['id'] == calendar_id), None)
                    
                if not calendar_info:
                    logger.error(f"Calendar {calendar_id} not found in calendar list")
                    return {
                        "new_events": 0,
                        "updated_events": 0,
                        "deleted_events": 0,
                        "errors": [f"Calendar {calendar_id} not found in calendar list. Make sure the service account has been granted access."]
                    }
                    
                logger.info(f"Found calendar in list: {calendar_info}")
            except Exception as e:
                logger.error(f"Error accessing calendar list: {str(e)}")
                return {
                    "new_events": 0,
                    "updated_events": 0,
                    "deleted_events": 0,
                    "errors": [f"Error accessing calendar list: {str(e)}"]
                }
            
            # Set default time range if not provided
            if time_min is None:
                time_min = datetime.now(self.timezone).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=180)  # Get events from 180 days ago
            if time_max is None:
                time_max = time_min + timedelta(days=365)  # Get events for the next 365 days
            
            logger.info(f"Fetching events from {time_min} to {time_max}")
            
            # Get events from Google Calendar
            events = self.google_client.get_events(
                calendar_id=calendar_id,
                time_min=time_min,
                time_max=time_max
            )
            
            # Process events
            new_events = 0
            updated_events = 0
            deleted_events = 0
            
            with self.db.get_session() as session:
                for event in events:  # events is already a list
                    try:
                        # Extract event details
                        start = event['start'].get('dateTime', event['start'].get('date'))
                        end = event['end'].get('dateTime', event['end'].get('date'))
                        
                        # Convert to datetime objects with timezone
                        if 'T' in start:  # Has time component
                            start_time = datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(self.timezone)
                        else:  # All-day event
                            start_time = datetime.strptime(start, '%Y-%m-%d').replace(tzinfo=self.timezone)
                            
                        if 'T' in end:  # Has time component
                            end_time = datetime.fromisoformat(end.replace('Z', '+00:00')).astimezone(self.timezone)
                        else:  # All-day event
                            end_time = datetime.strptime(end, '%Y-%m-%d').replace(tzinfo=self.timezone)
                        
                        # Check if event exists
                        existing = session.query(Event).filter_by(
                            calendar_id=calendar_id,
                            google_id=event['id']
                        ).first()
                        
                        # Set default event type and category if not present
                        event_type = 'default'
                        category = 'uncategorized'
                        
                        if existing:
                            # Update existing event
                            existing.title = event.get('summary', '')
                            existing.description = event.get('description')
                            existing.start_time = start_time.strftime('%Y-%m-%d %H:%M:%S.%f') if start_time else None
                            existing.end_time = end_time.strftime('%Y-%m-%d %H:%M:%S.%f') if end_time else None
                            existing.location = event.get('location')
                            existing.is_recurring = bool(event.get('recurrence', []))
                            existing.recurrence_pattern = json.dumps(event.get('recurrence', [])) if event.get('recurrence') else None
                            existing.last_synced = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S.%f')
                            existing.is_deleted = False
                            existing.event_type = event_type
                            existing.category = category
                            updated_events += 1
                        else:
                            # Create new event
                            new_event = Event(
                                google_id=event['id'],
                                title=event.get('summary', ''),
                                description=event.get('description'),
                                start_time=start_time.strftime('%Y-%m-%d %H:%M:%S.%f') if start_time else None,
                                end_time=end_time.strftime('%Y-%m-%d %H:%M:%S.%f') if end_time else None,
                                location=event.get('location'),
                                calendar_id=calendar_id,
                                event_type=event_type,
                                category=category,
                                is_recurring=bool(event.get('recurrence', [])),
                                recurrence_pattern=json.dumps(event.get('recurrence', [])) if event.get('recurrence') else None,
                                last_synced=datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S.%f'),
                                is_deleted=False
                            )
                            session.add(new_event)
                            new_events += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing event {event.get('id')}: {e}")
                        continue
                
                # Commit changes
                session.commit()
            
            return {
                'new_events': new_events,
                'updated_events': updated_events,
                'deleted_events': deleted_events,
                'errors': []
            }
            
        except Exception as e:
            logger.error(f"Error syncing calendar: {e}")
            return {
                'new_events': 0,
                'updated_events': 0,
                'deleted_events': 0,
                'errors': [str(e)]
            }
    
    def sync_all_calendars(self):
        """Sync all configured calendars"""
        results = {}
        for calendar_id in self.config.get('google', {}).get('calendar_ids', []):
            try:
                results[calendar_id] = self.sync_calendar(calendar_id)
            except Exception as e:
                logger.error(f"Failed to sync calendar {calendar_id}: {str(e)}")
        return results
    
    def _get_sync_state(self, session: Session, calendar_id: str) -> SyncState:
        """Get or create sync state for calendar"""
        stmt = select(SyncState).where(SyncState.calendar_id == calendar_id)
        sync_state = session.execute(stmt).scalar_one_or_none()
        
        if not sync_state:
            sync_state = SyncState(calendar_id=calendar_id)
            session.add(sync_state)
            session.commit()
            
        return sync_state
    
    def _process_event(self, session: Session, event_data: Dict, calendar_id: str, stats: Dict):
        """Process a single event from Google Calendar"""
        # Check if event exists
        stmt = select(Event).where(Event.google_id == event_data['id'])
        existing_event = session.execute(stmt).scalar_one_or_none()
        
        # Parse event details using NLP processor
        parsed = self._parse_event_details(event_data)
        
        if existing_event:
            self._update_event(session, existing_event, parsed, event_data, stats)
        else:
            self._create_event(session, parsed, event_data, calendar_id, stats)
    
    def _parse_event_details(self, event_data: Dict) -> Dict:
        """Parse event details using NLP processor"""
        # Create a natural language description for the NLP processor
        description = f"Event: {event_data.get('summary', '')}. "
        if event_data.get('description'):
            description += event_data['description']
            
        # Parse using NLP processor
        parsed = self.nlp.parse_command(description)
        
        # If NLP couldn't determine type/category, use defaults
        if parsed['entities']['type'] == 'OTHER':
            parsed['entities']['type'] = self._guess_event_type(event_data)
        if parsed['entities']['category'] == 'OTHER':
            parsed['entities']['category'] = 'WORK' if '@company.com' in str(event_data) else 'PERSONAL'
            
        return parsed
    
    def _guess_event_type(self, event_data: Dict) -> str:
        """Guess event type based on event data"""
        summary = event_data.get('summary', '').lower()
        
        if any(word in summary for word in ['meeting', 'sync', 'review', 'discussion']):
            return 'MEETING'
        elif any(word in summary for word in ['lunch', 'dinner', 'breakfast']):
            return 'MEAL'
        elif any(word in summary for word in ['appointment', 'doctor', 'dentist']):
            return 'APPOINTMENT'
        elif any(word in summary for word in ['reminder', 'todo', 'task']):
            return 'REMINDER'
        else:
            return 'OTHER'
    
    def _create_event(self, session: Session, event_data: dict) -> Event:
        """Create a new event in both Google Calendar and local database."""
        # Extract event details
        title = event_data['event']['title']
        start_time = event_data['start_time']
        end_time = event_data.get('end_time')
        event_type = event_data['event'].get('type', 'OTHER')
        category = event_data['event'].get('category', 'OTHER')
        description = event_data['event'].get('description')
        location = event_data.get('location')
        participants = event_data.get('participants', [])

        # Create Google Calendar event
        google_event = {
            'summary': title,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end_time if end_time else start_time,  # Default to same time if no end time
                'timeZone': 'America/Los_Angeles',
            },
        }

        # Add attendees if any
        if participants:
            google_event['attendees'] = [{'email': p} for p in participants]

        try:
            # Insert event into Google Calendar
            created_event = self.google_client.events().insert(
                calendarId='primary',
                body=google_event
            ).execute()

            # Create local database event
            db_event = Event(
                id=created_event['id'],
                calendar_id='primary',
                title=title,
                event_type=event_type,
                category=category,
                start_time=start_time.strftime('%Y-%m-%d %H:%M:%S.%f') if start_time else None,
                end_time=end_time.strftime('%Y-%m-%d %H:%M:%S.%f') if end_time else None,
                location=location,
                description=description,
                google_calendar_id=created_event['id']
            )

            # Add participants
            for participant in participants:
                db_event.participants.append(
                    Participant(name=participant)
                )

            session.add(db_event)
            session.commit()

            return db_event

        except Exception as e:
            session.rollback()
            raise Exception(f"Failed to create event: {str(e)}")
    
    def _update_event(self, session: Session, event: Event, parsed: Dict, event_data: Dict, stats: Dict):
        """Update an existing event in the database"""
        event.title = event_data.get('summary', 'Untitled Event')
        event.description = event_data.get('description')
        
        # Convert datetime objects to strings for storage
        start_time = self._parse_datetime(event_data['start'])
        end_time = self._parse_datetime(event_data['end'])
        
        event.start_time = start_time.strftime('%Y-%m-%d %H:%M:%S.%f') if start_time else None
        event.end_time = end_time.strftime('%Y-%m-%d %H:%M:%S.%f') if end_time else None
        
        event.location = event_data.get('location')
        event.event_type = parsed['entities']['type']
        event.category = parsed['entities']['category']
        event.is_recurring = bool(event_data.get('recurrence'))
        event.recurrence_pattern = json.dumps(event_data.get('recurrence', []))
        event.last_synced = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # Update participants
        event.participants = []
        for attendee in event_data.get('attendees', []):
            participant = self._get_or_create_participant(session, attendee)
            event.participants.append(participant)
            
        stats['updated_events'] += 1
    
    def _handle_deleted_event(self, session: Session, event_data: Dict, stats: Dict):
        """Mark an event as deleted in the database"""
        stmt = select(Event).where(Event.google_id == event_data['id'])
        event = session.execute(stmt).scalar_one_or_none()
        
        if event:
            event.is_deleted = True
            event.last_synced = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S.%f')
            stats['deleted_events'] += 1
    
    def _get_or_create_participant(self, session: Session, attendee: Dict) -> Participant:
        """Get or create a participant record"""
        email = attendee.get('email')
        if not email:
            return None
            
        stmt = select(Participant).where(Participant.email == email)
        participant = session.execute(stmt).scalar_one_or_none()
        
        if not participant:
            participant = Participant(
                email=email,
                name=attendee.get('displayName', email.split('@')[0]),
                response_status=attendee.get('responseStatus', 'needsAction')
            )
            session.add(participant)
            
        return participant
    
    def _parse_datetime(self, dt_data: Dict) -> datetime:
        """Parse datetime from Google Calendar format"""
        if 'dateTime' in dt_data:
            return datetime.fromisoformat(dt_data['dateTime'].replace('Z', '+00:00')).astimezone(self.timezone)
        elif 'date' in dt_data:
            # All-day event, use start of day in local timezone
            return datetime.strptime(dt_data['date'], '%Y-%m-%d').replace(tzinfo=self.timezone)
        else:
            return None
    
    def get_events_between(self, start: datetime, end: datetime) -> List[Event]:
        """Get all events between start and end dates"""
        logger.info(f"Getting events between {start} and {end}")
        
        with self.db.get_session() as session:
            # Convert to naive UTC for string comparison
            start_str = start.astimezone(tz.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
            end_str = end.astimezone(tz.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
            
            logger.info(f"Querying with start_str: {start_str}, end_str: {end_str}")
            
            calendar_id = os.getenv('GOOGLE_CALENDAR_IDS', '').split(',')[0]
            from sqlalchemy import or_
            query = session.query(Event).filter(
                Event.calendar_id == calendar_id,
                Event.is_deleted == False,
                # Event starts before range ends
                Event.start_time <= end_str,
                # Event ends after or at range starts, or has no end time
                or_(Event.end_time >= start_str, Event.end_time == None)
            ).order_by(Event.start_time)
            
            # Get raw SQL query with parameters
            sql = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
            logger.info(f"Raw SQL: {sql}")
            
            events = query.all()
            logger.info(f"Found {len(events)} events")
            
            # Convert events to response format
            response_events = []
            for event in events:
                try:
                    response_event = EventResponse(
                        id=event.id,
                        title=event.title,
                        type=event.event_type,
                        category=event.category,
                        start_time=event.start_time_local,
                        end_time=event.end_time_local,
                        location=event.location,
                        description=event.description,
                        participants=[p.name for p in event.participants]
                    )
                    response_events.append(response_event)
                except Exception as e:
                    logger.error(f"Error converting event {event.title}: {e}")
                    continue
            
            return response_events
    
    def query_events(self, session: Session, parsed: dict) -> List[Event]:
        """Query events based on natural language parsed data"""
        # Get current time in local timezone
        now = datetime.now(self.timezone)
        
        # Default to today if no time specified
        if not parsed.get('start_time'):
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        else:
            # Convert string dates to datetime objects if needed
            if isinstance(parsed['start_time'], str):
                start = datetime.fromisoformat(parsed['start_time'])
            else:
                start = parsed['start_time']
                
            if parsed.get('end_time'):
                if isinstance(parsed['end_time'], str):
                    end = datetime.fromisoformat(parsed['end_time'])
                else:
                    end = parsed['end_time']
            elif parsed.get('duration'):
                end = start + timedelta(minutes=parsed['duration'])
            else:
                # Default to 1 hour for meetings, 30 mins for other events
                duration = 60 if parsed.get('event', {}).get('type') == 'MEETING' else 30
                end = start + timedelta(minutes=duration)
        
        # Ensure timezone awareness
        if start.tzinfo is None:
            start = start.replace(tzinfo=self.timezone)
        if end.tzinfo is None:
            end = end.replace(tzinfo=self.timezone)
        
        # Query events
        stmt = select(Event).where(
            and_(
                Event.start_time >= start.strftime('%Y-%m-%d %H:%M:%S.%f'),
                Event.start_time < end.strftime('%Y-%m-%d %H:%M:%S.%f'),
                Event.is_deleted == False
            )
        )
        
        # Apply type filter if specified
        event_type = parsed.get('event', {}).get('type')
        if event_type and event_type != 'OTHER':
            stmt = stmt.where(Event.event_type == event_type)
            
        # Apply category filter if specified
        category = parsed.get('event', {}).get('category')
        if category and category != 'OTHER':
            stmt = stmt.where(Event.category == category)
            
        # Apply participant filter if specified
        if parsed.get('participants'):
            participants = parsed['participants']
            for participant in participants:
                stmt = stmt.join(Event.participants).where(
                    Participant.name.ilike(f"%{participant}%")
                )
        
        # Order by start time
        stmt = stmt.order_by(Event.start_time)
        
        return session.execute(stmt).scalars().all()
