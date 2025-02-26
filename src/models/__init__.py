from src.models.base import Base
from src.models.calendar import Calendar
from src.models.event import CalendarEvent

# This ensures all models are registered with SQLAlchemy's metadata
__all__ = ['Base', 'Calendar', 'CalendarEvent']
