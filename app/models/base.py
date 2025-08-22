from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel as PydanticBaseModel, Field
import uuid


class BaseModel(PydanticBaseModel):
    """Base model with common configuration"""
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v)
        }


class TimestampedModel(BaseModel):
    """Base model with timestamp fields"""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


class IdentifiableModel(TimestampedModel):
    """Base model with ID field"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

