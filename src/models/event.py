from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class CalendarEvent(BaseModel):
    id: Optional[str]
    title: str
    start: datetime
    end: datetime
    description: Optional[str]
    location: Optional[str]
    attendees: List[str]
    source: str  # google/outlook
    
    def to_json(self):
        return self.json()
