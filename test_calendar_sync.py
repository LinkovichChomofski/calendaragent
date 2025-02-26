from src.services.calendar_sync_service import CalendarSyncService
from src.services.calendar_manager import CalendarManager
from src.database.connection import DatabaseManager, db_manager, get_db
from src.models import Base, Calendar, CalendarEvent
from sqlalchemy import select
from dotenv import load_dotenv
import os
import tempfile
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.config import ConfigManager
import pytest
from fastapi.testclient import TestClient
from fastapi import Depends
import logging
from sqlalchemy import inspect

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_calendar_sync():
    """Test calendar sync service initialization"""
    current_time = datetime(2025, 2, 23, 12, 3, 3, tzinfo=ZoneInfo('America/Los_Angeles'))
    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        # Initialize test components
        db_manager = DatabaseManager(db_path)
        Base.metadata.create_all(bind=db_manager.engine)

        # Create test calendar
        with db_manager.get_session() as session:
            calendar = Calendar(
                id="test_calendar_id",
                google_id="test_google_calendar_id",
                name="Test Calendar",
                owner_email="test@example.com",
                last_synced=current_time
            )
            session.add(calendar)
            session.commit()

            # Verify calendar was created
            saved_calendar = session.query(Calendar).filter_by(id="test_calendar_id").first()
            assert saved_calendar is not None
            assert saved_calendar.name == "Test Calendar"

            # Create a test event
            event = CalendarEvent(
                id="test_event_id",
                google_id="test_google_event_id",
                title="Test Event",
                description="Test Description",
                start=current_time,
                end=current_time + timedelta(hours=1),
                calendar_id=calendar.id,
                source="google"
            )
            session.add(event)
            session.commit()

            # Verify event was created and linked to calendar
            assert len(saved_calendar.events) == 1
            assert saved_calendar.events[0].title == "Test Event"

    except Exception as e:
        raise e

    finally:
        # Clean up test database
        os.unlink(db_path)

from src.api.main import app
from src.services.calendar_service import CalendarService
from src.nlp.processor import NLPProcessor

# Create a test database manager
test_db_manager = None

def override_get_db():
    """Override the database dependency for testing"""
    if test_db_manager is None:
        raise RuntimeError("Test database not initialized")
    try:
        db = test_db_manager.get_session()
        yield db
    finally:
        db.close()

# Override FastAPI's database dependency
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def test_db():
    """Initialize test database for each test"""
    global test_db_manager

    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        # Initialize test database
        test_db_manager = DatabaseManager(db_path)
        
        # Create all tables
        Base.metadata.create_all(bind=test_db_manager.engine)
        logger.info("Created database tables")
        
        # Initialize database with primary calendar
        test_db_manager.init_database()
        logger.info("Initialized database with primary calendar")
        
        # Verify tables exist
        inspector = inspect(test_db_manager.engine)
        table_names = inspector.get_table_names()
        logger.info(f"Tables in database: {table_names}")
        
        # Override FastAPI's database dependency for each test
        app.dependency_overrides[get_db] = override_get_db
        
        yield test_db_manager
    finally:
        # Clean up test database
        try:
            Base.metadata.drop_all(bind=test_db_manager.engine)
        except:
            pass
        os.unlink(db_path)
        
        # Reset FastAPI's database dependency
        app.dependency_overrides.clear()

@pytest.fixture
def calendar_service(test_db):
    """Initialize calendar service with test dependencies"""
    nlp_processor = NLPProcessor()
    calendar_service = CalendarService(test_db, nlp_processor)
    return calendar_service

@pytest.mark.asyncio
async def test_full_event_lifecycle(test_db):
    """Test complete event lifecycle: create, read, update, delete"""
    current_time = datetime(2025, 2, 23, 12, 3, 3, tzinfo=ZoneInfo('America/Los_Angeles'))
    start_time = current_time + timedelta(days=1)
    end_time = start_time + timedelta(minutes=30)

    # Create test calendar and event in database
    with test_db.get_session() as session:
        calendar = Calendar(
            id="test_calendar_id",
            google_id="test_google_calendar_id",
            name="Test Calendar",
            owner_email="test@example.com",
            last_synced=current_time
        )
        session.add(calendar)
        session.commit()

    # Test event creation
    create_response = client.post(
        "/events",
        json={
            "title": "Team Sync",
            "description": "Weekly team sync meeting",
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "calendar_id": "test_calendar_id",
            "source": "google"
        }
    )
    assert create_response.status_code == 200
    event_data = create_response.json()["events"][0]
    event_id = event_data["id"]

    # Test event retrieval
    get_response = client.get(f"/events/{event_id}")
    assert get_response.status_code == 200
    assert get_response.json()["events"][0]["title"] == "Team Sync"

    # Test event update
    update_response = client.put(
        f"/events/{event_id}",
        json={
            "id": event_id,
            "title": "Updated Team Sync",
            "description": "Updated team sync meeting",
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "calendar_id": "test_calendar_id",
            "source": "google"
        }
    )
    assert update_response.status_code == 200
    assert update_response.json()["events"][0]["title"] == "Updated Team Sync"

    # Test event deletion
    delete_response = client.delete(f"/events/{event_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Event deleted successfully"

@pytest.mark.asyncio
async def test_error_handling(test_db):
    """Test error handling for invalid inputs"""
    current_time = datetime(2025, 2, 23, 12, 3, 3, tzinfo=ZoneInfo('America/Los_Angeles'))

    # Test creating event with invalid calendar_id
    create_response = client.post(
        "/events",
        json={
            "title": "Test Event",
            "description": "Test Description",
            "start": current_time.isoformat(),
            "end": (current_time + timedelta(hours=1)).isoformat(),
            "calendar_id": "invalid_calendar_id",
            "source": "google"
        }
    )
    assert create_response.status_code == 404
    assert "not found" in create_response.json()["error"].lower()

    # Test updating non-existent event
    update_response = client.put(
        "/events/non_existent_id",
        json={
            "id": "non_existent_id",
            "title": "Updated Event",
            "description": "Updated Description",
            "start": current_time.isoformat(),
            "end": (current_time + timedelta(hours=1)).isoformat(),
            "calendar_id": "test_calendar_id",
            "source": "google"
        }
    )
    assert update_response.status_code == 404
    assert "not found" in update_response.json()["message"].lower()

    # Test deleting non-existent event
    delete_response = client.delete("/events/non_existent_id")
    assert delete_response.status_code == 200
    assert "not found" in delete_response.json()["message"].lower()
