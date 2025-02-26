#!/usr/bin/env python
# Test script to list events from the database

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging
import json

# Add project directory to Python path
project_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(project_dir))

from src.database.models import CalendarEvent
from src.database.connection import get_db, db_manager
from src.config.manager import ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_events():
    """List all events from the database."""
    try:
        # Get a database session
        session = db_manager.get_session()
        
        # Query all events
        events = session.query(CalendarEvent).all()
        
        if not events:
            logger.info("No events found in the database.")
            return
            
        logger.info(f"Found {len(events)} events in the database:")
        
        # Print each event
        for i, event in enumerate(events):
            # Convert SQLAlchemy object to dict for cleaner printing
            event_dict = {
                'id': event.id,
                'google_id': event.google_id,
                'title': event.title,
                'description': event.description,
                'location': event.location,
                'start': str(event.start) if event.start else None,
                'end': str(event.end) if event.end else None,
                'last_synced': str(event.last_synced) if event.last_synced else None,
                'source': event.source,
                'is_deleted': event.is_deleted
            }
            
            logger.info(f"Event {i+1}: {json.dumps(event_dict, indent=2)}")
            
        # Close the session
        session.close()
    except Exception as e:
        logger.error(f"Error listing events: {str(e)}")

if __name__ == "__main__":
    list_events()
    sys.exit(0)
