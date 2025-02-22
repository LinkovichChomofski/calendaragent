from typing import Dict, Any, Optional
import os
import json
from openai import OpenAI
from datetime import datetime, timedelta
import pytz
from zoneinfo import ZoneInfo
import re
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
from ..services.holiday_service import HolidayService
from ..config.manager import ConfigManager

class OpenAIProcessor:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.client = OpenAI(api_key=config.get_openai_key())
        self.local_timezone = ZoneInfo('America/Los_Angeles')
        self.holiday_service = HolidayService()
        
    def parse_command(self, text: str) -> Dict[str, Any]:
        """Parse natural language command using OpenAI"""
        current_time = datetime.now(self.local_timezone)
        
        system_prompt = f"""You are a calendar management AI that helps parse natural language commands into structured data.
        Current time: {current_time.strftime('%Y-%m-%d %H:%M %Z')}
        
        Parse commands into a JSON object with this exact structure:
        {{
            "intent": "SCHEDULE|CANCEL|QUERY|UPDATE",
            "event": {{
                "title": "clear and descriptive event title",
                "type": "MEETING|LUNCH|CALL|APPOINTMENT|REMINDER|OTHER",
                "category": "WORK|PERSONAL|SOCIAL|HEALTH|OTHER",
                "description": "optional longer description"
            }},
            "start_time": "ISO timestamp with timezone",
            "end_time": "ISO timestamp with timezone or null",
            "duration": "duration in minutes or null",
            "participants": ["list", "of", "names"],
            "location": "place name or null",
            "recurrence": {{
                "frequency": "DAILY|WEEKLY|MONTHLY|YEARLY",
                "interval": number,
                "days": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
                "monthDay": number (1-31),
                "weekNumber": number (1-5 for first-fifth),
                "until": "ISO timestamp or null",
                "count": number or null,
                "skip_holidays": true|false,
                "skip_weekends": true|false
            }} or null
        }}

        Title Guidelines:
        1. Make titles clear and descriptive but concise
        2. Include key context (team name, project, purpose)
        3. Use proper capitalization
        4. Remove unnecessary words (a, the, etc.)
        5. Include participant names for social events
        6. Use standard prefixes for common event types:
           - "Team Sync:" for regular team meetings
           - "1:1:" for one-on-one meetings
           - "Review:" for review meetings
           - "Planning:" for planning sessions
           
        Examples:
        1. "Show my events for today"
        {{
            "intent": "QUERY",
            "event": {{
                "title": null,
                "type": "OTHER",
                "category": "OTHER",
                "description": null
            }},
            "start_time": "2025-02-17T00:00:00-08:00",
            "end_time": "2025-02-18T00:00:00-08:00",
            "duration": null,
            "participants": [],
            "location": null,
            "recurrence": null
        }}
        
        2. "Schedule a team meeting tomorrow at 2pm"
        {{
            "intent": "SCHEDULE",
            "event": {{
                "title": "Team Meeting",
                "type": "MEETING",
                "category": "WORK",
                "description": "Regular team meeting"
            }},
            "start_time": "2025-02-18T14:00:00-08:00",
            "end_time": null,
            "duration": 60,
            "participants": [],
            "location": null,
            "recurrence": null
        }}
        """
        
        user_prompt = f"Parse this calendar command: {text}"
        
        model = self.config.get('openai.model', 'gpt-4-turbo-preview')
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            print(f"OpenAI Response: {response.choices[0].message.content}")  # Debug line
            
            parsed = json.loads(response.choices[0].message.content)
            
            # Ensure required fields exist
            if 'event' not in parsed:
                parsed['event'] = {
                    "title": None,
                    "type": "OTHER",
                    "category": "OTHER",
                    "description": None
                }
                
            # Set defaults for missing fields
            parsed.setdefault('intent', 'QUERY')
            parsed.setdefault('start_time', None)
            parsed.setdefault('end_time', None)
            parsed.setdefault('duration', None)
            parsed.setdefault('participants', [])
            parsed.setdefault('location', None)
            parsed.setdefault('recurrence', None)
            
            normalized = self._normalize_temporal_data(parsed, current_time)
            return normalized
            
        except Exception as e:
            print(f"Error parsing OpenAI response: {e}")
            result = self._get_empty_result()
            result['start_time'] = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['end_time'] = result['start_time'] + timedelta(days=1)
            return result
            
    def _normalize_temporal_data(self, parsed: Dict, current_time: datetime) -> Dict:
        """Normalize and validate temporal data"""
        try:
            # Set default start and end time
            start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)

            # Parse start_time if provided
            if parsed.get('start_time'):
                if isinstance(parsed['start_time'], str):
                    try:
                        start_time = datetime.fromisoformat(parsed['start_time'])
                    except ValueError:
                        print(f"Error parsing start_time: {parsed['start_time']}")
                else:
                    start_time = parsed['start_time']

            # Parse end_time if provided
            if parsed.get('end_time'):
                if isinstance(parsed['end_time'], str):
                    try:
                        end_time = datetime.fromisoformat(parsed['end_time'])
                    except ValueError:
                        print(f"Error parsing end_time: {parsed['end_time']}")
                        end_time = start_time + timedelta(days=1)
                else:
                    end_time = parsed['end_time']
            else:
                # Default end time is start time + 1 day for queries
                if parsed.get('intent') == 'QUERY':
                    end_time = start_time + timedelta(days=1)
                else:
                    # For other intents, use duration if specified
                    if parsed.get('duration'):
                        end_time = start_time + timedelta(minutes=parsed['duration'])
                    else:
                        # Default duration based on event type
                        duration = 60 if parsed.get('event', {}).get('type') == 'MEETING' else 30
                        end_time = start_time + timedelta(minutes=duration)

            # Ensure timezone awareness
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=self.local_timezone)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=self.local_timezone)

            # Validate and swap if needed
            if start_time > end_time:
                start_time, end_time = end_time, start_time

            # Update the parsed data
            parsed['start_time'] = start_time.isoformat()
            parsed['end_time'] = end_time.isoformat()

            return parsed
        except Exception as e:
            print(f"Error normalizing temporal data: {e}")
            print(f"Input data: {parsed}")
            # Return safe defaults
            default_start = current_time.replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=self.local_timezone
            )
            default_end = default_start + timedelta(days=1)
            parsed['start_time'] = default_start.isoformat()
            parsed['end_time'] = default_end.isoformat()
            return parsed
    
    def _parse_time_range(self, time_range: str, current_time: datetime) -> tuple:
        """Parse time range expressions like 'next week', 'tomorrow', etc."""
        if time_range == "next week":
            # Start from next Monday
            start = current_time + relativedelta(weekday=MO(+1))
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            return start, end
        elif time_range == "tomorrow":
            start = current_time + timedelta(days=1)
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=23, minutes=59, seconds=59)
            return start, end
        elif time_range == "today":
            start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=23, minutes=59, seconds=59)
            return start, end
        else:
            raise ValueError(f"Unsupported time range: {time_range}")
    
    def _normalize_recurrence(self, recurrence: Dict) -> Dict:
        """Normalize recurrence pattern with enhanced support for complex patterns"""
        if not isinstance(recurrence, dict):
            return None
            
        normalized = {
            "frequency": recurrence.get("frequency", "").upper(),
            "interval": recurrence.get("interval", 1),
            "until": None,
            "count": None,
            "exceptions": []
        }
        
        # Handle week days for weekly recurrence
        if normalized["frequency"] == "WEEKLY" and "days" in recurrence:
            normalized["days"] = [day.upper() for day in recurrence["days"]]
        
        # Handle weekday-only recurrence
        if recurrence.get("weekdays"):
            if normalized["frequency"] == "DAILY":
                normalized["days"] = ["MON", "TUE", "WED", "THU", "FRI"]
            
        # Handle monthly recurrence patterns
        if normalized["frequency"] == "MONTHLY":
            # Day of month (e.g., "15th of each month")
            if "monthDay" in recurrence:
                normalized["monthDay"] = min(max(1, recurrence["monthDay"]), 31)
                
            # Week number (e.g., "first Monday")
            if "weekNumber" in recurrence:
                normalized["weekNumber"] = min(max(1, recurrence["weekNumber"]), 5)
                
            # Both week number and days must be present for "first Monday" type patterns
            if "weekNumber" in normalized and "days" in recurrence:
                normalized["days"] = [day.upper() for day in recurrence["days"]]
        
        # Handle recurrence limits
        if "until" in recurrence:
            try:
                until = parse(recurrence["until"])
                if not until.tzinfo:
                    until = until.replace(tzinfo=self.local_timezone)
                normalized["until"] = until.isoformat()
            except Exception as e:
                print(f"Error parsing until date: {e}")
                
        if "count" in recurrence:
            try:
                normalized["count"] = int(recurrence["count"])
            except Exception as e:
                print(f"Error parsing count: {e}")
        
        # Handle exceptions (specific dates to skip)
        if "exceptions" in recurrence:
            try:
                normalized["exceptions"] = [
                    parse(date).replace(tzinfo=self.local_timezone).isoformat()
                    for date in recurrence["exceptions"]
                ]
            except Exception as e:
                print(f"Error parsing exceptions: {e}")
                
        return normalized

    def _normalize_title(self, event_data: Dict) -> str:
        """Normalize and validate event title"""
        if not event_data or not event_data.get("title"):
            return None
            
        title = event_data["title"].strip()
        
        # Apply standard formatting
        title = " ".join(word.capitalize() for word in title.split())
        
        # Add type prefix if needed
        event_type = event_data.get("type", "").upper()
        if event_type == "MEETING" and not any(prefix in title for prefix in ["Team Sync:", "1:1:", "Review:", "Planning:"]):
            if "team" in title.lower() and "sync" in title.lower():
                title = f"Team Sync: {title}"
            elif len(event_data.get("participants", [])) == 1:
                title = f"1:1: {title}"
            elif "review" in title.lower():
                title = f"Review: {title}"
            elif "planning" in title.lower() or "plan" in title.lower():
                title = f"Planning: {title}"
                
        return title

    def get_event_summary(self, event_data: Dict[str, Any]) -> str:
        """Generate a natural language summary of an event"""
        current_time = datetime.now(self.local_timezone)
        
        prompt = f"""Current time: {current_time.strftime('%Y-%m-%d %H:%M %Z')}
        
        Generate a natural, conversational summary of this calendar event:
        {json.dumps(event_data, indent=2)}
        
        Include:
        1. What the event is
        2. When it's happening (in a natural way, like "tomorrow at 2pm" or "next Monday")
        3. Who's involved
        4. Where it's happening
        5. Any recurring pattern
        
        Make it sound friendly and concise. If certain details are missing, acknowledge that.
        """
        
        response = self.client.chat.completions.create(
            model=self.config.get('openai.model', 'gpt-4-turbo-preview'),
            messages=[
                {"role": "system", "content": "You are a helpful calendar assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content.strip()

    def _get_empty_result(self) -> Dict:
        """Get empty result structure"""
        return {
            "intent": "QUERY",
            "event": {
                "title": None,
                "type": "OTHER",
                "category": "OTHER",
                "description": None
            },
            "start_time": None,
            "end_time": None,
            "duration": None,
            "participants": [],
            "location": None,
            "recurrence": None
        }
