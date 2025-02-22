import os
import sys
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pytz
import traceback
from pydantic import BaseModel
from zoneinfo import ZoneInfo
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add the src directory to the Python path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(root_dir)
logger.info(f"Added {root_dir} to Python path")
logger.info(f"Current PYTHONPATH: {os.environ.get('PYTHONPATH', '')}")

from src.config.manager import ConfigManager
from src.database.session import get_db
from src.services.calendar_sync_service import CalendarSyncService
from src.database.models import Event
from src.services.calendar_manager import CalendarManager

# Pydantic models for API
class CommandRequest(BaseModel):
    command: str

class EventResponse(BaseModel):
    id: int
    title: str
    type: str
    category: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    participants: List[str] = []

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

app = FastAPI(title="Calendar Agent API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Initializing services...")
# Initialize services
config = ConfigManager()
google_config = config._load_google_config()

# Add required type field if not present
if 'type' not in google_config:
    google_config['type'] = 'service_account'

sync_service = CalendarSyncService(config=google_config)
logger.info("Services initialized successfully")

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
    if request.headers.get("origin") in ["http://localhost:3000", "http://localhost:3001"]:
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
    return {"detail": error_message}

@app.post("/command", response_model=CommandResponse)
async def process_command(request: CommandRequest, db: Session = Depends(get_db)):
    """Process natural language command"""
    try:
        logger.info(f"Processing command: {request.command}")
        
        # Parse command
        parsed = nlp.parse_command(request.command)
        logger.debug(f"Parsed command result: {parsed}")
        
        if parsed['intent'] == 'QUERY':
            logger.info("Executing QUERY intent")
            try:
                # Query events
                events = sync_service.query_events(db, parsed)
                logger.info(f"Found {len(events)} events")
                
                event_responses = [
                    EventResponse(
                        id=event.id,
                        title=event.title,
                        type=event.event_type,
                        category=event.category,
                        start_time=event.start_time,
                        end_time=event.end_time,
                        location=event.location,
                        description=event.description,
                        participants=[p.name for p in event.participants]
                    ) for event in events
                ]
                
                response = CommandResponse(
                    success=True,
                    message="Events retrieved successfully",
                    events=event_responses
                )
                logger.info("Successfully built response")
                return response
            except Exception as e:
                logger.error(f"Error querying events: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error querying events: {str(e)}"
                )
                    
        elif parsed['intent'] == 'SCHEDULE':
            logger.info("Executing SCHEDULE intent")
            try:
                # Create event in calendar and database
                event = sync_service._create_event(db, parsed)
                
                # Broadcast update to all clients
                await broadcast_message({
                    'type': 'event_created',
                    'event': event.to_dict()
                })
                
                return CommandResponse(
                    success=True,
                    message=f"Event '{event.title}' scheduled successfully",
                    events=[EventResponse(
                        id=event.id,
                        title=event.title,
                        type=event.event_type,
                        category=event.category,
                        start_time=event.start_time,
                        end_time=event.end_time,
                        location=event.location,
                        description=event.description,
                        participants=[p.name for p in event.participants]
                    )]
                )
            except Exception as e:
                logger.error(f"Error scheduling event: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error scheduling event: {str(e)}"
                )
                    
        elif parsed['intent'] == 'CANCEL':
            logger.info("Executing CANCEL intent")
            try:
                # Cancel event
                success = sync_service.cancel_event(db, parsed)
                return CommandResponse(
                    success=success,
                    message="Event cancelled successfully" if success else "Failed to cancel event"
                )
            except Exception as e:
                logger.error(f"Error cancelling event: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error cancelling event: {str(e)}"
                )
                    
        elif parsed['intent'] == 'UPDATE':
            logger.info("Executing UPDATE intent")
            try:
                # Update event
                success = sync_service.update_event(db, parsed)
                return CommandResponse(
                    success=success,
                    message="Event updated successfully" if success else "Failed to update event"
                )
            except Exception as e:
                logger.error(f"Error updating event: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error updating event: {str(e)}"
                )
        else:
            logger.info(f"Unknown intent: {parsed['intent']}")
            raise HTTPException(status_code=400, detail="Unknown command intent")
                
    except Exception as e:
        logger.error(f"Error processing command: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return CommandResponse(
            success=False,
            message="Error processing command",
            error=str(e)
        )

@app.post("/sync", response_model=SyncStatus)
async def sync_calendar(db: Session = Depends(get_db)):
    """Sync calendar events"""
    try:
        # Get the configured calendar ID
        calendar_id = os.getenv('GOOGLE_CALENDAR_IDS', '').split(',')[0]
        if not calendar_id:
            raise ValueError("No calendar ID configured")
            
        sync_service = CalendarSyncService(config=config.config.get('google'))
        result = sync_service.sync_calendar(calendar_id=calendar_id)
        
        # Notify connected clients
        await broadcast_message({
            "type": "sync_complete",
            "stats": result
        })
        
        return result
    except Exception as e:
        logger.error(f"Error syncing calendar: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/today", response_model=List[EventResponse])
async def get_today_events(db: Session = Depends(get_db)):
    """Get today's events"""
    try:
        logger.info("Fetching today's events")
        tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        events = sync_service.get_events_between(db, start, end)
        logger.info(f"Found {len(events)} events")
        
        return [EventResponse(
            id=event.id,
            title=event.title,
            type=event.event_type,
            category=event.category,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            description=event.description,
            participants=[p.name for p in event.participants]
        ) for event in events]
    except Exception as e:
        logger.error(f"Error fetching today's events: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/week", response_model=List[EventResponse])
async def get_week_events():
    """Get events for the current week"""
    try:
        logger.info("Fetching week events...")
        
        # Get current time from metadata
        current_time = datetime.fromisoformat('2025-02-21T22:32:30-08:00')
        
        # Calculate start of week (Sunday) and end of week (Saturday)
        start_of_week = current_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=current_time.weekday())
        end_of_week = start_of_week + timedelta(days=7)
        
        logger.info(f"Getting events between {start_of_week} and {end_of_week}")
        
        # Get events from calendar service
        return sync_service.get_events_between(start_of_week, end_of_week)
        
    except Exception as e:
        logger.error(f"Error getting week events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/month", response_model=List[EventResponse])
async def get_month_events(db: Session = Depends(get_db)):
    """Get this month's events"""
    try:
        logger.info("Fetching month events")
        tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(tz)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate end of month
        if now.month == 12:
            end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        events = sync_service.get_events_between(db, start, end)
        logger.info(f"Found {len(events)} events")
        
        return [EventResponse(
            id=event.id,
            title=event.title,
            type=event.event_type,
            category=event.category,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            description=event.description,
            participants=[p.name for p in event.participants]
        ) for event in events]
    except Exception as e:
        logger.error(f"Error fetching month events: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/range", response_model=List[EventResponse])
async def get_events_range(start: datetime, end: datetime, db: Session = Depends(get_db)):
    """Get events within a date range"""
    try:
        logger.info("Fetching events within date range")
        tz = pytz.timezone('America/Los_Angeles')
        if start.tzinfo is None:
            start = start.replace(tzinfo=tz)
        if end.tzinfo is None:
            end = end.replace(tzinfo=tz)
            
        events = sync_service.get_events_between(db, start, end)
        logger.info(f"Found {len(events)} events")
        
        return [EventResponse(
            id=event.id,
            title=event.title,
            type=event.event_type,
            category=event.category,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            description=event.description,
            participants=[p.name for p in event.participants]
        ) for event in events]
    except Exception as e:
        logger.error(f"Error fetching events within date range: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calendars/{calendar_id}", response_model=Dict)
async def add_calendar(calendar_id: str, session: Session = Depends(get_db)):
    """Add a new calendar."""
    try:
        calendar_manager = CalendarManager()
        return calendar_manager.add_calendar(session, calendar_id)
    except Exception as e:
        logger.error(f"Error adding calendar {calendar_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/calendars/{calendar_id}")
async def remove_calendar(calendar_id: str, session: Session = Depends(get_db)):
    """Remove a calendar."""
    try:
        calendar_manager = CalendarManager()
        calendar_manager.remove_calendar(session, calendar_id)
        return {"message": f"Calendar {calendar_id} removed successfully"}
    except Exception as e:
        logger.error(f"Error removing calendar {calendar_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calendars/sync")
async def sync_calendars(session: Session = Depends(get_db)):
    """Sync calendars from Google Calendar."""
    try:
        calendar_manager = CalendarManager()
        return calendar_manager.sync_calendars(session)
    except Exception as e:
        logger.error(f"Error syncing calendars: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
