from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, validator
from .base import IdentifiableModel


class EventStatus(str, Enum):
    """Event status enumeration"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class EventCreate(BaseModel):
    """Request model for creating an event"""
    name: str = Field(..., min_length=1, max_length=255, description="Event name")
    total_seats: int = Field(..., gt=0, le=10000, description="Total number of seats")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Event name cannot be empty')
        return v.strip()


class EventResponse(BaseModel):
    """Response model for event data"""
    event_id: str
    name: str
    total_seats: int
    created_at: datetime


class Event(IdentifiableModel):
    """Event entity model"""
    name: str = Field(..., min_length=1, max_length=255)
    total_seats: int = Field(..., gt=0, le=10000)
    status: EventStatus = Field(default=EventStatus.ACTIVE)
    
    @property
    def event_id(self) -> str:
        return self.id
    
    def to_response(self) -> EventResponse:
        """Convert to response model"""
        return EventResponse(
            event_id=self.event_id,
            name=self.name,
            total_seats=self.total_seats,
            created_at=self.created_at
        )
