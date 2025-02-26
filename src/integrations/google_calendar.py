import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import socket
from typing import Optional, List, Dict, Any
import logging
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
import time
import base64
from src.config.manager import ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleCalendarClient:
    def __init__(self, config: dict = None):
        self.service = None
        self.scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events.readonly'
        ]
        
        # Load config if not provided
        if not config:
            config_manager = ConfigManager()
            self.config = config_manager._load_google_config()
        else:
            self.config = config
            
        logger.info(f"Service account config keys: {self.config.keys()}")
        
        # Initialize service
        try:
            self._get_service()
        except Exception as e:
            logger.error(f"Error in service account authentication process: {str(e)}")
            logger.error(f"Service account config: {self.config}")
            raise
            
    def _get_service(self):
        """Initialize the Google Calendar service with service account credentials"""
        try:
            # Create credentials directly from service account info
            credentials = service_account.Credentials.from_service_account_info(
                self.config,
                scopes=self.scopes
            )
            self.service = build('calendar', 'v3', credentials=credentials)
            logger.info("Successfully initialized Google Calendar service")
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {str(e)}")
            logger.error(f"Config: {self.config}")
            raise
            
    def _get_available_port(self, start_port: int = 8080, max_attempts: int = 10) -> Optional[int]:
        """Find an available port starting from start_port"""
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    return port
                except socket.error:
                    continue
        return None
        
    def get_calendar_list(self) -> List[Dict[str, Any]]:
        """Get list of calendars"""
        try:
            calendar_list = self.service.calendarList().list().execute()
            logger.info(f"Retrieved calendar list: {calendar_list}")
            return calendar_list.get('items', [])
        except Exception as e:
            logger.error(f"Error fetching calendar list: {str(e)}")
            return []
            
    def add_calendar_to_list(self, calendar_id: str) -> bool:
        """Add a calendar to the service account's calendar list"""
        try:
            logger.info(f"Attempting to add calendar {calendar_id} to list")
            calendar_list_entry = {
                'id': calendar_id,
                'selected': True,
                'backgroundColor': '#9fe1e7',
                'foregroundColor': '#000000'
            }
            self.service.calendarList().insert(body=calendar_list_entry).execute()
            logger.info(f"Successfully added calendar {calendar_id} to list")
            return True
        except Exception as e:
            logger.error(f"Error adding calendar {calendar_id} to list: {str(e)}")
            return False
            
    def get_calendar(self, calendar_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific calendar"""
        try:
            return self.service.calendars().get(calendarId=calendar_id).execute()
        except Exception as e:
            logger.error(f"Error getting calendar {calendar_id}: {str(e)}")
            return None

    def get_events(self, calendar_id: str, time_min: datetime = None, time_max: datetime = None) -> List[Dict[str, Any]]:
        """Get events from a calendar"""
        try:
            # Default to retrieving events from 6 months ago to 6 months in the future if not specified
            if not time_min:
                time_min = datetime.now() - timedelta(days=180)
            if not time_max:
                time_max = datetime.now() + timedelta(days=180)
                
            # Convert datetime objects to RFC3339 timestamps
            # Check if the input is already a string
            if isinstance(time_min, str):
                time_min_str = time_min
            else:
                time_min_str = time_min.isoformat() + 'Z' if time_min and not time_min.tzinfo else None
                
            if isinstance(time_max, str):
                time_max_str = time_max
            else:
                time_max_str = time_max.isoformat() + 'Z' if time_max and not time_max.tzinfo else None
            
            logger.info(f"Fetching events for calendar {calendar_id} from {time_min_str} to {time_max_str}")
            
            # Build request
            request = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min_str,
                timeMax=time_max_str,
                singleEvents=True,
                maxResults=2500,  # Fetch more events at once
                orderBy='startTime'
            )
            
            events = []
            while request is not None:
                response = request.execute()
                events.extend(response.get('items', []))
                request = self.service.events().list_next(request, response)
                
            return events
        except Exception as e:
            logger.error(f"Error getting events for calendar {calendar_id}: {str(e)}")
            return []

    def create_event(self, calendar_id: str, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new event in the calendar"""
        try:
            return self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
        except Exception as e:
            logger.error(f"Error creating event in calendar {calendar_id}: {str(e)}")
            return None

    def update_event(self, calendar_id: str, event_id: str, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing event"""
        try:
            return self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
        except Exception as e:
            logger.error(f"Error updating event {event_id} in calendar {calendar_id}: {str(e)}")
            return None

    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Delete an event from the calendar"""
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting event {event_id} from calendar {calendar_id}: {str(e)}")
            return False

    def list_calendars(self):
        return self.get_calendar_list()
