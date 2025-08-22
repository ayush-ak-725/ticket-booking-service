from datetime import datetime, timedelta, timezone
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, validator
from .base import IdentifiableModel
import uuid


class HoldStatus(str, Enum):
    """Hold status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CONFIRMED = "confirmed"


class HoldCreate(BaseModel):
    """Request model for creating a hold"""
    event_id: str = Field(..., description="Event ID")
    qty: int = Field(..., gt=0, le=100, description="Number of seats to hold")
    
    @validator('qty')
    def validate_qty(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        if v > 100:
            raise ValueError('Cannot hold more than 100 seats at once')
        return v


class HoldResponse(BaseModel):
    """Response model for hold data"""
    hold_id: str
    event_id: str
    qty: int
    expires_at: datetime
    payment_token: str
    status: HoldStatus


class Hold(IdentifiableModel):
    """Hold entity model"""
    event_id: str = Field(..., description="Event ID")
    qty: int = Field(..., gt=0, le=100)
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=2))
    payment_token: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: HoldStatus = Field(default=HoldStatus.ACTIVE)
    
    @property
    def hold_id(self) -> str:
        return self.id
    
    @property
    def is_expired(self) -> bool:
        """Check if hold has expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if hold is active and not expired"""
        return self.status == HoldStatus.ACTIVE and not self.is_expired
    
    def expire(self) -> None:
        """Mark hold as expired"""
        self.status = HoldStatus.EXPIRED
        self.updated_at = datetime.now(timezone.utc)
    
    def confirm(self) -> None:
        """Mark hold as confirmed"""
        self.status = HoldStatus.CONFIRMED
        self.updated_at = datetime.now(timezone.utc)
    
    def to_response(self) -> HoldResponse:
        """Convert to response model"""
        return HoldResponse(
            hold_id=self.hold_id,
            event_id=self.event_id,
            qty=self.qty,
            expires_at=self.expires_at,
            payment_token=self.payment_token,
            status=self.status
        )
