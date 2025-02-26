#!/usr/bin/env python3
"""
Script to fix database issues by creating all necessary tables
"""
import os
import sys
import logging
import sqlite3
from sqlalchemy import create_engine, inspect

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database():
    """Fix database issues by creating all necessary tables"""
    logger.info("Fixing database...")
    
    # Database path
    db_path = os.path.join(project_root, 'calendar.db')
    logger.info(f"Database path: {db_path}")
    
    # Create engine for inspection
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Check existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    logger.info(f"Existing tables: {existing_tables}")
    
    # Connect directly to SQLite to create tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create calendar_participants table if it doesn't exist
    if 'calendar_participants' not in existing_tables:
        logger.info("Creating calendar_participants table...")
        cursor.execute('''
        CREATE TABLE calendar_participants (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            email VARCHAR
        )
        ''')
        logger.info("Created calendar_participants table")
    
    # Create calendar_event_participants table if it doesn't exist
    if 'calendar_event_participants' not in existing_tables:
        logger.info("Creating calendar_event_participants table...")
        cursor.execute('''
        CREATE TABLE calendar_event_participants (
            event_id VARCHAR,
            participant_id VARCHAR,
            FOREIGN KEY (event_id) REFERENCES calendar_events(id),
            FOREIGN KEY (participant_id) REFERENCES calendar_participants(id)
        )
        ''')
        logger.info("Created calendar_event_participants table")
    
    # Create sync_state table if it doesn't exist
    if 'sync_state' not in existing_tables:
        logger.info("Creating sync_state table...")
        cursor.execute('''
        CREATE TABLE sync_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calendar_id VARCHAR NOT NULL UNIQUE,
            last_sync_token VARCHAR,
            last_synced TIMESTAMP,
            full_sync_needed BOOLEAN DEFAULT 1
        )
        ''')
        logger.info("Created sync_state table")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    # Verify tables after fix
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info(f"Tables after fix: {tables}")
    
    # Check columns in each table
    for table in tables:
        columns = [col['name'] for col in inspector.get_columns(table)]
        logger.info(f"Columns in {table} table: {columns}")
    
    logger.info("Database fix complete")

if __name__ == "__main__":
    fix_database()
