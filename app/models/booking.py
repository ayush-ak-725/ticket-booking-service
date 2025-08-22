from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from .base import IdentifiableModel


class BookingCreate(BaseModel):
    """Request model for creating a booking"""
    hold_id: str = Field(..., description="Hold ID")
    payment_token: str = Field(..., description="Payment token from hold")


class BookingResponse(BaseModel):
    """Response model for booking data"""
    booking_id: str
    hold_id: str
    event_id: str
    qty: int
    created_at: datetime


class Booking(IdentifiableModel):
    """Booking entity model"""
    hold_id: str = Field(..., description="Hold ID")
    event_id: str = Field(..., description="Event ID")
    qty: int = Field(..., gt=0)
    payment_token: str = Field(..., description="Payment token used")
    
    @property
    def booking_id(self) -> str:
        return self.id
    
    def to_response(self) -> BookingResponse:
        """Convert to response model"""
        return BookingResponse(
            booking_id=self.booking_id,
            hold_id=self.hold_id,
            event_id=self.event_id,
            qty=self.qty,
            created_at=self.created_at
        )
