from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from src.models.base import Base

class Calendar(Base):
    __tablename__ = 'calendars'

    id = Column(String, primary_key=True)
    summary = Column(String)
    description = Column(String, nullable=True)
    time_zone = Column(String)
    background_color = Column(String, nullable=True)
    foreground_color = Column(String, nullable=True)
    access_role = Column(String)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'summary': self.summary,
            'description': self.description,
            'timeZone': self.time_zone,
            'backgroundColor': self.background_color,
            'foregroundColor': self.foreground_color,
            'accessRole': self.access_role,
            'primary': self.is_primary,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
