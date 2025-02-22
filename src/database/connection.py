from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from src.database.models import Base, Calendar, Event, Participant, SyncState
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
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
            
            # Create primary calendar if it doesn't exist
            with self.get_session() as session:
                primary_calendar = session.query(Calendar).filter(Calendar.id == 'primary').first()
                if not primary_calendar:
                    primary_calendar = Calendar(
                        id='primary',
                        summary='Primary Calendar',
                        time_zone='America/Los_Angeles',
                        access_role='owner',
                        is_primary=True
                    )
                    session.add(primary_calendar)
                    session.commit()
                    logger.info("Created primary calendar")
                    
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
            
    def get_session(self):
        return self.SessionLocal()
