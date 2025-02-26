#!/usr/bin/env python3
"""
Script to initialize the database with the correct schema
"""
import os
import sys
import logging
from sqlalchemy import inspect

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models and database connection
from src.models.base import Base
from src.database.models import Calendar, CalendarEvent, CalendarParticipant, calendar_event_participants
from src.database.connection import DatabaseManager

def init_database():
    """Initialize the database with the correct schema"""
    logger.info("Initializing database...")
    
    # Remove existing database if it exists
    db_path = os.path.join(project_root, 'calendar.db')
    if os.path.exists(db_path):
        logger.info(f"Removing existing database: {db_path}")
        os.remove(db_path)
    
    # Create database manager
    db_manager = DatabaseManager(db_path)
    
    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=db_manager.engine)
    
    # Verify tables were created
    inspector = inspect(db_manager.engine)
    tables = inspector.get_table_names()
    logger.info(f"Created tables: {tables}")
    
    # Check columns in each table
    for table in tables:
        columns = [col['name'] for col in inspector.get_columns(table)]
        logger.info(f"Columns in {table} table: {columns}")
    
    logger.info("Database initialization complete")

if __name__ == "__main__":
    init_database()
