from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime

class EventData(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    location: Optional[str] = None
    participants: Optional[List[str]] = None
    recurrence: Optional[str] = None

class EventResponse(BaseModel):
    success: bool
    message: str
    events: Optional[List[EventData]] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return self.model_dump()
