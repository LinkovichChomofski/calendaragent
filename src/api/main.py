import os
import sys
import logging
import traceback
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from zoneinfo import ZoneInfo
import json
import uuid

from src.models.calendar import Calendar
from src.models.event import CalendarEvent as CalendarEventPydantic
from src.database.connection import get_db, DatabaseManager
from src.database.models import CalendarEvent as DBCalendarEvent
import pytz

from src.config.manager import ConfigManager
from src.services.calendar_sync_service import CalendarSyncService
from src.services.calendar_manager import CalendarManager
from src.nlp.processor import NLPProcessor
from src.integrations.google_calendar import GoogleCalendarClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the src directory to the Python path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(root_dir)
logger.info(f"Added {root_dir} to Python path")
logger.info(f"Current PYTHONPATH: {os.environ.get('PYTHONPATH', '')}")

# Initialize services
config_manager = ConfigManager()
google_config = config_manager._load_google_config()
db_manager = DatabaseManager()
google_client = GoogleCalendarClient(config=google_config)
nlp_processor = NLPProcessor()
calendar_sync_service = CalendarSyncService(db_manager, google_client, nlp_processor)

logger.info("Services initialized successfully")

# Initialize FastAPI app
app = FastAPI(title="Calendar Agent API")

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002", 
    "http://localhost:3003",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:3003",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connections
active_connections = set()

async def broadcast_message(message: dict):
    """Broadcast a message to all connected clients"""
    if not active_connections:
        logger.debug("No active connections to broadcast to")
        return
        
    # Convert message to JSON string
    try:
        message_str = json.dumps(message)
    except Exception as e:
        logger.error(f"Error serializing message: {e}")
        return
        
    # Send to all connected clients
    for connection in active_connections.copy():
        try:
            await connection.send_text(message_str)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            try:
                active_connections.remove(connection)
            except KeyError:
                pass

@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    if request.headers.get("origin") in origins:
        response.headers["Access-Control-Allow-Origin"] = request.headers["origin"]
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    try:
        # Log connection attempt
        logger.info("New WebSocket connection request")
        logger.debug("WebSocket Headers:")
        for k, v in websocket.headers.items():
            logger.debug(f"  {k}: {v}")
            
        # Validate origin
        origin = websocket.headers.get("origin")
        logger.info(f"WebSocket connection attempt from origin: {origin}")
        logger.info(f"Request URL: {websocket.url}")
        
        # Accept connection
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Add to active connections
        active_connections.add(websocket)
        
        try:
            while True:
                try:
                    # Wait for message
                    data = await websocket.receive_text()
                    
                    # Skip empty messages
                    if not data or not data.strip():
                        continue
                        
                    try:
                        # Parse message
                        message = json.loads(data)
                        
                        # Handle message
                        if message.get('type') == 'ping':
                            await websocket.send_json({
                                'type': 'pong',
                                'timestamp': datetime.now().isoformat()
                            })
                        else:
                            logger.warning(f"Unknown message type: {message.get('type')}")
                            
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON message: {data}")
                        continue
                        
                except WebSocketDisconnect:
                    logger.info("WebSocket connection closed")
                    break
                    
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
            raise
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        raise
        
    finally:
        # Remove from active connections
        active_connections.discard(websocket)
        logger.info("WebSocket connection closed")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    error_message = str(exc)
    logger.error(f"Error processing request: {error_message}")
    return Response(status_code=500, content=json.dumps({"detail": error_message}))

# Pydantic models for API
class CommandRequest(BaseModel):
    command: str

class EventData(BaseModel):
    title: str
    description: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    participants: Optional[List[str]] = None

class EventResponse(BaseModel):
    success: bool
    message: str
    events: Optional[List[Dict]] = None
    error: Optional[str] = None

class CommandResponse(BaseModel):
    success: bool
    message: str
    events: Optional[List[EventResponse]] = None
    error: Optional[str] = None

class SyncStatus(BaseModel):
    new_events: int = 0
    updated_events: int = 0
    deleted_events: int = 0
    errors: List[str] = []

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    calendar_id: str
    source: str

class EventUpdate(EventCreate):
    id: str

@app.post("/command", response_model=CommandResponse)
async def process_command(command: CommandRequest):
    try:
        logger.info(f"Processing command: {command.command}")
        
        # For debugging
        if not command or not command.command:
            logger.error("Empty command received")
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "No command provided", "error": "Empty command"}
            )
        
        # Extract event details using NLP
        event_details = nlp_processor.extract_event_details(command.command)
        logger.info(f"Extracted event details: {event_details}")
        
        if not event_details or not event_details.get("intent"):
            logger.error(f"Failed to extract intent from command: {command.command}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Failed to extract event details", "error": "Missing intent"}
            )

        if event_details["intent"] == "SCHEDULE":
            # Create an event object from the extracted details
            try:
                title = event_details.get("event", {}).get("title") or event_details.get("title")
                if not title:
                    logger.error(f"No title found in extracted event details: {event_details}")
                    return JSONResponse(
                        status_code=400,
                        content={"success": False, "message": "Missing event title", "error": "Title required"}
                    )
                
                # Parse dates from strings if needed
                start_time = event_details.get("start_time")
                if isinstance(start_time, str):
                    try:
                        start_time = datetime.fromisoformat(start_time)
                        
                        # Check if the date is in the past - this is often a parsing error
                        current_time = datetime.fromisoformat('2025-02-25T12:00:00-08:00')
                        if start_time.year < current_time.year:
                            # Extract time components from parsed date, but use current date
                            if "tomorrow" in command.command.lower():
                                base_date = current_time.date() + timedelta(days=1)
                            else:
                                base_date = current_time.date()
                                
                            # Create a new datetime with today/tomorrow and the parsed time
                            start_time = datetime.combine(
                                base_date,
                                start_time.time(),
                                tzinfo=current_time.tzinfo
                            )
                            logger.info(f"Corrected past date to: {start_time}")
                    except ValueError as e:
                        logger.error(f"Error parsing start time: {e}")
                        return JSONResponse(
                            status_code=400,
                            content={"success": False, "message": f"Invalid start time format: {start_time}", "error": str(e)}
                        )
                    
                end_time = event_details.get("end_time")
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time)
                    
                # If end_time is not provided, calculate it from duration or default to 1 hour
                if not end_time:
                    duration_minutes = None
                    if event_details.get("duration"):
                        try:
                            duration_minutes = int(event_details["duration"])
                        except (ValueError, TypeError):
                            # Try to parse duration string (e.g., "30 minutes", "1 hour")
                            duration_str = str(event_details["duration"]).lower()
                            if "hour" in duration_str:
                                try:
                                    hours = float(duration_str.split("hour")[0].strip())
                                    duration_minutes = int(hours * 60)
                                except (ValueError, TypeError):
                                    duration_minutes = 60
                            elif "minute" in duration_str:
                                try:
                                    duration_minutes = int(duration_str.split("minute")[0].strip())
                                except (ValueError, TypeError):
                                    duration_minutes = 30
                    
                    # Default to 1 hour if duration couldn't be parsed
                    if not duration_minutes:
                        duration_minutes = 60
                        
                    logger.info(f"No end time provided, using duration of {duration_minutes} minutes")
                    end_time = start_time + timedelta(minutes=duration_minutes)
                
                event_data = {
                    "title": title,
                    "description": event_details.get("event", {}).get("description") or event_details.get("description"),
                    "start_time": start_time,
                    "end_time": end_time,
                    "location": event_details.get("location"),
                    "participants": event_details.get("participants", [])
                }
                
                logger.info(f"Creating event with data: {event_data}")
                
                # Create the event
                result = await calendar_sync_service.schedule_event(event_data)
                
                if result["success"]:
                    logger.info(f"Event scheduled successfully: {result['event']['id']}")
                    command_result = {
                        "success": True,
                        "result": f"Event '{result['event']['title']}' scheduled for {result['event']['start']}",
                        "data": result["event"]
                    }
                    return JSONResponse(content=command_result)
                else:
                    logger.error(f"Error scheduling event: {result.get('error', 'Unknown error')}")
                    return JSONResponse(
                        status_code=500,
                        content={"success": False, "message": f"Error scheduling event: {result.get('error', 'Unknown error')}", "error": result.get('error')}
                    )
                
            except Exception as e:
                logger.error(f"Error creating event object: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return JSONResponse(
                    status_code=500,
                    content={"success": False, "message": f"Error creating event: {str(e)}", "error": str(e)}
                )
        else:
            logger.error(f"Unsupported intent: {event_details['intent']}")
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Unsupported intent: {event_details['intent']}", "error": "Unsupported intent"}
            )

    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error processing command: {str(e)}", "error": str(e)}
        )

@app.post("/sync")
async def sync_calendars(db: Session = Depends(get_db)):
    """Sync calendars from Google Calendar"""
    try:
        # Get configured calendar ID
        calendar_id = os.getenv('GOOGLE_CALENDAR_IDS', '').split(',')[0]
        if not calendar_id:
            raise ValueError("No calendar ID configured")
            
        result = calendar_sync_service.sync_calendars(db)
        
        # Notify connected clients
        await broadcast_message({
            "type": "sync_complete",
            "data": {
                "success": result["success"],
                "new_events": result.get("events_synced", 0),
                "updated_events": result.get("events_updated", 0),
                "deleted_events": result.get("events_deleted", 0),
                "errors": result.get("errors", [])
            }
        })
        
        return {"message": "Calendar sync complete", "result": result}
        
    except Exception as e:
        logger.error(f"Error syncing calendars: {str(e)}")
        return Response(
            status_code=500,
            content=json.dumps({"error": f"Error syncing calendars: {str(e)}"}),
            media_type="application/json"
        )

@app.get("/events/today")
async def get_today_events():
    """Get events for today"""
    try:
        today = datetime.now(ZoneInfo('America/Los_Angeles')).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        logger.info(f"Getting events between {today} and {tomorrow}")
        
        # Get events from calendar service
        response = calendar_sync_service.list_events(today, tomorrow)
        
        if not response.get("success", False):
            return Response(
                status_code=500,
                content=json.dumps({"error": response.get("error", "Unknown error")}),
                media_type="application/json"
            )
        
        return response.get("events", [])
    except Exception as e:
        logger.error(f"Error getting today's events: {str(e)}")
        return Response(
            status_code=500,
            content=json.dumps({"error": f"Error getting today's events: {str(e)}"}),
            media_type="application/json"
        )

@app.get("/events/week")
async def get_week_events():
    """Get events for the current week (Monday to Sunday)"""
    try:
        today = datetime.now(ZoneInfo('America/Los_Angeles'))
        
        # Get the start of the week (Monday)
        start_of_week = today - timedelta(days=today.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get the end of the week (Sunday)
        end_of_week = start_of_week + timedelta(days=7)
        
        logger.info(f"Getting events between {start_of_week} and {end_of_week}")
        
        # Get events from calendar service
        response = calendar_sync_service.list_events(start_of_week, end_of_week)
        
        if not response.get("success", False):
            return Response(
                status_code=500,
                content=json.dumps({"error": response.get("error", "Unknown error")}),
                media_type="application/json"
            )
        
        return response.get("events", [])
    except Exception as e:
        logger.error(f"Error getting week's events: {str(e)}")
        return Response(
            status_code=500,
            content=json.dumps({"error": f"Error getting week's events: {str(e)}"}),
            media_type="application/json"
        )

@app.get("/events/month")
async def get_month_events():
    """Get events for the current month"""
    try:
        today = datetime.now(ZoneInfo('America/Los_Angeles'))
        
        # Calculate first day of month
        start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate first day of next month
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            end = today.replace(month=today.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        logger.info(f"Getting events between {start} and {end}")
        
        # Get events from calendar service
        response = calendar_sync_service.list_events(start, end)
        
        if not response.get("success", False):
            return Response(
                status_code=500,
                content=json.dumps({"error": response.get("error", "Unknown error")}),
                media_type="application/json"
            )
        
        return response.get("events", [])
    except Exception as e:
        logger.error(f"Error getting month's events: {str(e)}")
        return Response(
            status_code=500,
            content=json.dumps({"error": f"Error getting month's events: {str(e)}"}),
            media_type="application/json"
        )

@app.get("/events/range")
async def get_events_by_range(start_date: str, end_date: str):
    """Get events between start_date and end_date. Dates should be ISO format (YYYY-MM-DD)"""
    try:
        # Parse dates
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        logger.info(f"Getting events between {start} and {end}")
        
        # Get events from calendar service
        response = calendar_sync_service.list_events(start, end)
        
        if not response.get("success", False):
            return Response(
                status_code=500,
                content=json.dumps({"error": response.get("error", "Unknown error")}),
                media_type="application/json"
            )
        
        return response.get("events", [])
    except Exception as e:
        logger.error(f"Error getting events for date range: {str(e)}")
        return Response(
            status_code=500,
            content=json.dumps({"error": f"Error getting events for date range: {str(e)}"}),
            media_type="application/json"
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Calendar management routes
@app.get("/calendars", response_model=List[Dict])
async def get_calendars(session: Session = Depends(get_db)):
    """Get all calendars."""
    try:
        calendar_manager = CalendarManager()
        return calendar_manager.get_calendars(session)
    except Exception as e:
        logger.error(f"Error getting calendars: {str(e)}")
        response_content = EventResponse(
            success=False,
            message=f"Error getting calendars: {str(e)}",
            error=str(e)
        )
        return Response(status_code=500, content=json.dumps(response_content.model_dump()))

@app.get("/calendars/{calendar_id}", response_model=Dict)
async def get_calendar(calendar_id: str, session: Session = Depends(get_db)):
    """Get a specific calendar."""
    try:
        calendar_manager = CalendarManager()
        calendar = calendar_manager.get_calendar(session, calendar_id)
        if not calendar:
            raise HTTPException(status_code=404, detail=f"Calendar {calendar_id} not found")
        return calendar
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting calendar {calendar_id}: {str(e)}")
        response_content = EventResponse(
            success=False,
            message=f"Error getting calendar {calendar_id}: {str(e)}",
            error=str(e)
        )
        return Response(status_code=500, content=json.dumps(response_content.model_dump()))

@app.post("/calendars/{calendar_id}", response_model=Dict)
async def add_calendar(calendar_id: str, session: Session = Depends(get_db)):
    """Add a new calendar."""
    try:
        calendar_manager = CalendarManager()
        return calendar_manager.add_calendar(session, calendar_id)
    except Exception as e:
        logger.error(f"Error adding calendar {calendar_id}: {str(e)}")
        response_content = EventResponse(
            success=False,
            message=f"Error adding calendar {calendar_id}: {str(e)}",
            error=str(e)
        )
        return Response(status_code=500, content=json.dumps(response_content.model_dump()))

@app.delete("/calendars/{calendar_id}")
async def remove_calendar(calendar_id: str, session: Session = Depends(get_db)):
    """Remove a calendar."""
    try:
        calendar_manager = CalendarManager()
        calendar_manager.remove_calendar(session, calendar_id)
        return {"message": f"Calendar {calendar_id} removed successfully"}
    except Exception as e:
        logger.error(f"Error removing calendar {calendar_id}: {str(e)}")
        response_content = EventResponse(
            success=False,
            message=f"Error removing calendar {calendar_id}: {str(e)}",
            error=str(e)
        )
        return Response(status_code=500, content=json.dumps(response_content.model_dump()))

@app.put("/calendars/{calendar_id}/colors")
async def update_calendar_colors(
    calendar_id: str,
    background_color: Optional[str] = None,
    foreground_color: Optional[str] = None,
    session: Session = Depends(get_db)
):
    """Update calendar colors."""
    try:
        calendar_manager = CalendarManager()
        return calendar_manager.update_calendar_colors(
            session, calendar_id, background_color, foreground_color
        )
    except Exception as e:
        logger.error(f"Error updating calendar colors for {calendar_id}: {str(e)}")
        response_content = EventResponse(
            success=False,
            message=f"Error updating calendar colors for {calendar_id}: {str(e)}",
            error=str(e)
        )
        return Response(status_code=500, content=json.dumps(response_content.model_dump()))

@app.post("/calendars/sync")
async def sync_calendars(session: Session = Depends(get_db)):
    """Sync calendars from Google Calendar."""
    try:
        calendar_manager = CalendarManager()
        result = calendar_manager.sync_calendars(session)
        return {"success": True, "message": "Calendars synced successfully", "data": result}
    except Exception as e:
        logger.error(f"Error syncing calendars: {str(e)}")
        response_content = {
            "success": False,
            "message": f"Error syncing calendars: {str(e)}",
            "error": str(e)
        }
        return Response(status_code=500, content=json.dumps(response_content))

@app.delete("/events/{event_id}")
async def delete_event(event_id: str, db: Session = Depends(get_db)):
    """Delete an event from the calendar"""
    try:
        deletion_success = calendar_sync_service.delete_event(event_id)
        return {"message": "Event deleted successfully" if deletion_success else "Event not found"}
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {str(e)}")
        return Response(
            status_code=500,
            content=json.dumps({"error": f"Error deleting event: {str(e)}"}),
            media_type="application/json"
        )

@app.post("/events")
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """Create a new calendar event."""
    try:
        # Check if calendar exists
        calendar = db.query(Calendar).filter_by(id=event.calendar_id).first()
        if not calendar:
            return Response(
                status_code=404,
                content=json.dumps({
                    "success": False,
                    "error": f"Calendar {event.calendar_id} not found"
                })
            )

        # Create event
        new_event = DBCalendarEvent(
            id=str(uuid.uuid4()),
            title=event.title,
            description=event.description,
            start=event.start,
            end=event.end,
            calendar_id=event.calendar_id,
            source=event.source
        )
        db.begin()
        try:
            db.add(new_event)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating event: {str(e)}")
            return Response(
                status_code=500,
                content=json.dumps({
                    "success": False,
                    "error": str(e)
                })
            )
        db.refresh(new_event)

        return {"success": True, "events": [new_event.to_dict()]}

    except Exception as e:
        logger.error(f"Error creating event: {str(e)}")
        return Response(
            status_code=500,
            content=json.dumps({
                "success": False,
                "error": str(e)
            })
        )

@app.put("/events/{event_id}")
async def update_event(event_id: str, event: EventUpdate, db: Session = Depends(get_db)):
    """Update an existing calendar event."""
    try:
        db_event = db.query(DBCalendarEvent).filter_by(id=event_id).first()
        if not db_event:
            return Response(status_code=404, content=json.dumps({"message": "Event not found"}))

        for key, value in event.dict(exclude={'id'}).items():
            setattr(db_event, key, value)

        db.commit()
        db.refresh(db_event)
        return {"success": True, "events": [db_event.to_dict()]}
    except Exception as e:
        logger.error(f"Error updating event {event_id}: {str(e)}")
        return Response(status_code=500, content=json.dumps({"error": str(e)}))

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI application with uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
