from typing import List
from pydantic import BaseModel

class SyncStatus(BaseModel):
    """Model for tracking sync status and results"""
    new_events: int = 0
    updated_events: int = 0
    deleted_events: int = 0
    errors: List[str] = []

    def model_dump(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "new_events": self.new_events,
            "updated_events": self.updated_events,
            "deleted_events": self.deleted_events,
            "errors": self.errors
        }
