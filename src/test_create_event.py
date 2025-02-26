#!/usr/bin/env python
# Test script to create a test event in Google Calendar

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Add project directory to Python path
project_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(project_dir))

from src.integrations.google_calendar import GoogleCalendarClient
from src.config.manager import ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_event():
    """Create a test event in the Google Calendar."""
    try:
        # Initialize ConfigManager to get calendar IDs
        config_manager = ConfigManager()
        config = config_manager._load_google_config()
        
        # Initialize GoogleCalendarClient
        client = GoogleCalendarClient(config)
        
        # Get calendar ID from config
        calendar_ids = config.get('calendar_ids', [])
        if not calendar_ids:
            logger.error("No calendar IDs found in configuration")
            return False
            
        calendar_id = calendar_ids[0]
        logger.info(f"Using calendar ID: {calendar_id}")
        
        # Create an event starting tomorrow
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        # Format times to RFC3339 strings
        start_str = start_time.isoformat() + 'Z'
        end_str = end_time.isoformat() + 'Z'
        
        # Event details
        event = {
            'summary': 'Test Event from CalendarAgent',
            'location': 'Remote',
            'description': 'This is a test event created to verify calendar sync functionality.',
            'start': {
                'dateTime': start_str,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end_str,
                'timeZone': 'America/Los_Angeles',
            },
            'reminders': {
                'useDefault': True,
            },
        }
        
        # Create the event
        created_event = client.create_event(calendar_id, event)
        
        if created_event:
            event_id = created_event.get('id')
            logger.info(f"Successfully created test event with ID: {event_id}")
            logger.info(f"Event details: {created_event}")
            return True
        else:
            logger.error("Failed to create test event")
            return False
            
    except Exception as e:
        logger.error(f"Error creating test event: {str(e)}")
        return False

if __name__ == "__main__":
    success = create_test_event()
    print(f"Test event creation {'succeeded' if success else 'failed'}")
    sys.exit(0 if success else 1)
