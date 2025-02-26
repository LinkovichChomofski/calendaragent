from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from src.models.base import Base
from src.database.models import Calendar, CalendarEvent, CalendarParticipant, calendar_event_participants, SyncState
import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Get the project root directory (two levels up from this file)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, 'calendar.db')
            
        self.db_path = db_path
        self.timezone = ZoneInfo('America/Los_Angeles')
        
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
            connect_args={'detect_types': 3}  # Enable parsing of both string and timestamp formats
        )
        
        # Create all tables
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
        
        # Register timezone conversion functions
        @event.listens_for(self.engine, 'connect')
        def set_sqlite_timezone(dbapi_connection, connection_record):
            # Store timezone-aware datetimes
            dbapi_connection.create_function('current_timestamp', 0, lambda: datetime.now(self.timezone).isoformat())
            
            def adapt_datetime(ts):
                if ts is None:
                    return None
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts)
                else:
                    dt = ts
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=self.timezone)
                return dt.isoformat()
            
            def convert_datetime(ts):
                if ts is None:
                    return None
                dt = datetime.fromisoformat(ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=self.timezone)
                return dt
            
            dbapi_connection.create_function('adapt_datetime', 1, adapt_datetime)
            dbapi_connection.create_function('convert_datetime', 1, convert_datetime)
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
    def init_database(self):
        """Initialize database tables"""
        try:
            # Create primary calendar if it doesn't exist
            with self.get_session() as session:
                primary_calendar = session.query(Calendar).filter(Calendar.id == 'primary').first()
                if not primary_calendar:
                    primary_calendar = Calendar(
                        id='primary',
                        google_id='primary',
                        name='Primary Calendar',
                        owner_email='user@example.com',
                        last_synced=datetime.now(self.timezone)
                    )
                    session.add(primary_calendar)
                    session.commit()
                    logger.info("Created primary calendar")
                    
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
            
    def get_session(self):
        return self.SessionLocal()

# Create a default database manager instance
db_manager = DatabaseManager()

def get_db():
    """FastAPI dependency that provides a database session"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()
