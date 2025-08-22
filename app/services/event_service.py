from typing import List, Optional
import redis.asyncio as redis
from app.models.event import Event, EventCreate, EventResponse
from app.repositories.event_repository import EventRepository
from app.core.exceptions import EventNotFoundError
from app.core.logging import get_logger


class EventService:
    """Event service with business logic"""
    
    def __init__(self, event_repository: EventRepository):
        self._repository = event_repository
        self.logger = get_logger(__name__)
    
    async def create_event(self, event_data: EventCreate) -> EventResponse:
        """Create a new event"""
        event = Event(
            name=event_data.name,
            total_seats=event_data.total_seats
        )
        
        created_event = await self._repository.create(event)
        self.logger.info("Event created successfully", event_id=created_event.id)
        
        return created_event.to_response()
    
    async def get_event(self, event_id: str) -> EventResponse:
        """Get event by ID"""
        event = await self._repository.get_by_id(event_id)
        if not event:
            raise EventNotFoundError(event_id)
        
        return event.to_response()
    
    async def get_event_status(self, event_id: str) -> dict:
        """Get event status with seat counts"""
        event = await self._repository.get_by_id(event_id)
        if not event:
            raise EventNotFoundError(event_id)
        
        available = await self._repository.get_available_seats(event_id)
        held = await self._get_held_seats(event_id)
        booked = await self._get_booked_seats(event_id)
        
        return {
            "total": event.total_seats,
            "available": available,
            "held": held,
            "booked": booked
        }
    
    async def list_events(self) -> List[EventResponse]:
        """List all events"""
        events = await self._repository.list_all()
        return [event.to_response() for event in events]
    
    async def _get_held_seats(self, event_id: str) -> int:
        """Get held seats for an event from Redis counters maintained by HoldRepository"""
        try:
            value = await self._repository._redis.get(f"held_seats:{event_id}")
            return int(value) if value else 0
        except Exception as error:
            self.logger.warning("Failed to read held seats", event_id=event_id, error=str(error))
            return 0
    
    async def _get_booked_seats(self, event_id: str) -> int:
        """Get booked seats for an event from Redis counters maintained by BookingRepository"""
        try:
            value = await self._repository._redis.get(f"booked_seats:{event_id}")
            return int(value) if value else 0
        except Exception as error:
            self.logger.warning("Failed to read booked seats", event_id=event_id, error=str(error))
            return 0

