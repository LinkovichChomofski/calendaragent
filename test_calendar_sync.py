from src.services.calendar_sync_service import CalendarSyncService
from src.services.calendar_manager import CalendarManager
from src.database.connection import DatabaseManager
from src.database.models import Event, Calendar
from sqlalchemy import select
from dotenv import load_dotenv
import os
import tempfile
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.config import ConfigManager

def test_calendar_sync():
    load_dotenv()
    
    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database manager with test database
        db_manager = DatabaseManager(db_path)
        calendar_manager = CalendarManager()
        config = ConfigManager().load_config()
        sync_service = CalendarSyncService(db_manager, config=config)
        
        print("Starting calendar sync test...")
        
        # First, sync and list available calendars
        print("\nSyncing calendars...")
        with db_manager.get_session() as session:
            calendars = calendar_manager.sync_calendars(session)
            
            print("\nAvailable Calendars:")
            for cal in calendars:
                print(f"\nCalendar ID: {cal['id']}")
                print(f"Summary: {cal['summary']}")
                print(f"Access Role: {cal['accessRole']}")
                print(f"Primary: {cal['primary']}")
        
        # Sync all configured calendars
        sync_results = sync_service.sync_all_calendars()
        
        # Verify at least one calendar was synced
        assert len(sync_results) > 0, "No calendars were synced"
        
        # Now sync events for each calendar
        print("\nSyncing events for each calendar...")
        with db_manager.get_session() as session:
            for calendar in session.query(Calendar).all():
                print(f"\nSyncing calendar: {calendar.summary}")
                # Calculate time range for sync
                time_min = datetime.now(ZoneInfo('America/Los_Angeles')).replace(hour=0, minute=0, second=0, microsecond=0)
                time_max = time_min + timedelta(days=30)
                # Only sync the calendar we have access to
                if calendar.id == 'a3caeb237bc1daa251da479d61071aad8f99c636a8b232b1501c940ec774f7ca@group.calendar.google.com':
                    stats = sync_service.sync_calendar(calendar.id, time_min=time_min, time_max=time_max)
                
                    # Print sync results for this calendar
                    print(f"\nSync Results for {calendar.summary}:")
                    print(f"New events: {stats['new_events']}")
                    print(f"Updated events: {stats['updated_events']}")
                    print(f"Deleted events: {stats['deleted_events']}")
                    
                    if stats['errors']:
                        print("\nErrors encountered:")
                        for error in stats['errors']:
                            print(f"- {error}")
        
        # Print some sample events from all calendars
        print("\nSample Events from All Calendars:")
        with db_manager.get_session() as session:
            stmt = select(Event).limit(10)
            events = session.execute(stmt).scalars().all()
            
            for event in events:
                print(f"\nEvent ID: {event.id}")
                print(f"Calendar ID: {event.calendar_id}")
                print(f"Title: {event.title}")
                print(f"Type: {event.event_type}")
                print(f"Category: {event.category}")
                print(f"Start Time: {event.start_time}")
                
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        raise
    finally:
        # Clean up test database
        try:
            os.unlink(db_path)
        except:
            pass

if __name__ == "__main__":
    test_calendar_sync()
