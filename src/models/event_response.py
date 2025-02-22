from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class EventResponse(BaseModel):
    id: int
    title: str
    type: str
    category: str
    start_time: datetime
    end_time: Optional[datetime]
    location: Optional[str]
    description: Optional[str]
    participants: List[str]

    class Config:
        from_attributes = True
