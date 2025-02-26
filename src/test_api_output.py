import requests
import json
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_today_events():
    """Test the /events/today endpoint"""
    try:
        response = requests.get("http://localhost:8000/events/today")
        if response.status_code == 200:
            events = response.json()
            logger.info(f"Today's events response: {json.dumps(events, indent=2)}")
            logger.info(f"Number of events returned: {len(events)}")
            
            # Check structure of the first event if there are any
            if events:
                first_event = events[0]
                logger.info(f"First event structure: {json.dumps(first_event, indent=2)}")
                logger.info(f"First event keys: {list(first_event.keys())}")
            else:
                logger.info("No events returned")
        else:
            logger.error(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

def test_week_events():
    """Test the /events/week endpoint"""
    try:
        response = requests.get("http://localhost:8000/events/week")
        if response.status_code == 200:
            events = response.json()
            logger.info(f"Week's events response: {json.dumps(events, indent=2)}")
            logger.info(f"Number of events returned: {len(events)}")
            
            # Check structure of the first event if there are any
            if events:
                first_event = events[0]
                logger.info(f"First event structure: {json.dumps(first_event, indent=2)}")
                logger.info(f"First event keys: {list(first_event.keys())}")
            else:
                logger.info("No events returned")
        else:
            logger.error(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

def test_month_events():
    """Test the /events/month endpoint"""
    try:
        response = requests.get("http://localhost:8000/events/month")
        if response.status_code == 200:
            events = response.json()
            logger.info(f"Month's events response: {json.dumps(events, indent=2)}")
            logger.info(f"Number of events returned: {len(events)}")
            
            # Check structure of the first event if there are any
            if events:
                first_event = events[0]
                logger.info(f"First event structure: {json.dumps(first_event, indent=2)}")
                logger.info(f"First event keys: {list(first_event.keys())}")
            else:
                logger.info("No events returned")
        else:
            logger.error(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

if __name__ == "__main__":
    logger.info("Testing Today's Events:")
    test_today_events()
    
    logger.info("\nTesting Week's Events:")
    test_week_events()
    
    logger.info("\nTesting Month's Events:")
    test_month_events()
