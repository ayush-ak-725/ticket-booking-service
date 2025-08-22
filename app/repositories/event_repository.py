import json
import asyncio
from typing import Optional, List, Dict
from app.models.event import Event
from app.repositories.base import BaseRepository
from app.core.logging import get_logger
import redis.asyncio as redis


class EventRepository(BaseRepository[Event]):
    """Event repository with in-memory storage and Redis caching"""
    
    def __init__(self, redis_client: redis.Redis):
        self._events: Dict[str, Event] = {}
        self._redis = redis_client
        self._lock = asyncio.Lock()
        self.logger = get_logger(__name__)
    
    async def create(self, event: Event) -> Event:
        """Create a new event"""
        async with self._lock:
            self._events[event.id] = event
            self.logger.info("Event stored in memory", event_id=event.id, name=event.name, total_events=len(self._events))
            await self._cache_event(event)
            self.logger.info("Event created", event_id=event.id, name=event.name)
            return event
    
    async def get_by_id(self, event_id: str) -> Optional[Event]:
        """Get event by ID with cache fallback"""
        # Temporarily bypass cache for debugging
        # cached = await self._get_cached_event(event_id)
        # if cached:
        #     return cached
        
        # Fallback to memory
        self.logger.info("Looking for event", event_id=event_id, total_events=len(self._events), event_keys=list(self._events.keys()))
        event = self._events.get(event_id)
        if event:
            await self._cache_event(event)
            self.logger.info("Event found", event_id=event_id)
        else:
            self.logger.warning("Event not found", event_id=event_id)
        
        return event
    
    async def update(self, event: Event) -> Event:
        """Update an existing event"""
        async with self._lock:
            if event.id not in self._events:
                raise ValueError(f"Event {event.id} not found")
            
            self._events[event.id] = event
            await self._cache_event(event)
            self.logger.info("Event updated", event_id=event.id)
            return event
    
    async def delete(self, event_id: str) -> bool:
        """Delete event by ID"""
        async with self._lock:
            if event_id in self._events:
                del self._events[event_id]
                await self._delete_cached_event(event_id)
                self.logger.info("Event deleted", event_id=event_id)
                return True
            return False
    
    async def list_all(self) -> List[Event]:
        """List all events"""
        return list(self._events.values())
    
    async def get_available_seats(self, event_id: str) -> int:
        """Get available seats for an event"""
        event = await self.get_by_id(event_id)
        if not event:
            return 0
        
        # Calculate available seats
        total_seats = event.total_seats
        held_seats = await self._get_held_seats(event_id)
        booked_seats = await self._get_booked_seats(event_id)
        
        available = total_seats - held_seats - booked_seats
        return max(0, available)
    
    async def _cache_event(self, event: Event) -> None:
        """Cache event in Redis"""
        try:
            await self._redis.setex(
                f"event:{event.id}",
                3600,  # 1 hour TTL
                event.model_dump_json()
            )
        except Exception as e:
            self.logger.warning("Failed to cache event", event_id=event.id, error=str(e))
    
    async def _get_cached_event(self, event_id: str) -> Optional[Event]:
        """Get event from cache"""
        try:
            cached = await self._redis.get(f"event:{event_id}")
            if cached:
                return Event.model_validate_json(cached)
        except Exception as e:
            self.logger.warning("Failed to get cached event", event_id=event_id, error=str(e))
        return None
    
    async def _delete_cached_event(self, event_id: str) -> None:
        """Delete event from cache"""
        try:
            await self._redis.delete(f"event:{event_id}")
        except Exception as e:
            self.logger.warning("Failed to delete cached event", event_id=event_id, error=str(e))
    
    async def _get_held_seats(self, event_id: str) -> int:
        """Get total held seats for an event"""
        try:
            held_seats = await self._redis.get(f"held_seats:{event_id}")
            return int(held_seats) if held_seats else 0
        except Exception as e:
            self.logger.warning("Failed to get held seats", event_id=event_id, error=str(e))
            return 0
    
    async def _get_booked_seats(self, event_id: str) -> int:
        """Get total booked seats for an event"""
        try:
            booked_seats = await self._redis.get(f"booked_seats:{event_id}")
            return int(booked_seats) if booked_seats else 0
        except Exception as e:
            self.logger.warning("Failed to get booked seats", event_id=event_id, error=str(e))
            return 0

