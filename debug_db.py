#!/usr/bin/env python3
"""
Script to debug database issues
"""
import os
import sys
import logging
from sqlalchemy import inspect, select
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models and database connection
from src.models.base import Base
from src.database.models import Calendar, CalendarEvent
from src.database.connection import DatabaseManager

def debug_database():
    """Debug database issues"""
    logger.info("Debugging database...")
    
    # Create database manager
    db_path = os.path.join(project_root, 'calendar.db')
    logger.info(f"Database path: {db_path}")
    
    # Check if database file exists
    if os.path.exists(db_path):
        logger.info(f"Database file exists: {db_path}")
        logger.info(f"File size: {os.path.getsize(db_path)} bytes")
    else:
        logger.error(f"Database file does not exist: {db_path}")
        return
    
    # Create database manager
    db_manager = DatabaseManager(db_path)
    
    # Verify tables
    inspector = inspect(db_manager.engine)
    tables = inspector.get_table_names()
    logger.info(f"Tables in database: {tables}")
    
    # Check columns in tables
    for table in tables:
        columns = [col['name'] for col in inspector.get_columns(table)]
        logger.info(f"Columns in {table}: {columns}")
    
    # Try to insert a test event
    with db_manager.get_session() as session:
        try:
            # Check if we have any events
            events = session.execute(select(CalendarEvent)).scalars().all()
            logger.info(f"Found {len(events)} events in database")
            
            # Insert a test event
            test_event = CalendarEvent(
                id=str(uuid.uuid4()),
                google_id="test_event_" + str(uuid.uuid4()),
                title="Test Event",
                description="This is a test event",
                start=datetime.now(ZoneInfo('America/Los_Angeles')),
                end=datetime.now(ZoneInfo('America/Los_Angeles')),
                location="Test Location",
                calendar_id="test_calendar",
                source="test",
                is_recurring=False,
                last_synced=datetime.now(ZoneInfo('America/Los_Angeles')),
                is_deleted=False
            )
            session.add(test_event)
            session.commit()
            logger.info(f"Inserted test event with ID: {test_event.id}")
            
            # Verify the event was inserted
            events = session.execute(select(CalendarEvent)).scalars().all()
            logger.info(f"Found {len(events)} events in database after insert")
            
            # Print the first event
            if events:
                logger.info(f"First event: {events[0].to_dict()}")
        except Exception as e:
            logger.error(f"Error working with database: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            session.rollback()

if __name__ == "__main__":
    debug_database()
