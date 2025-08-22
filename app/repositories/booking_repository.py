import json
import asyncio
from typing import Optional, List, Dict
from app.models.booking import Booking
from app.repositories.base import BaseRepository
from app.core.logging import get_logger
import redis.asyncio as redis


class BookingRepository(BaseRepository[Booking]):
    """Booking repository with idempotency support"""
    
    def __init__(self, redis_client: redis.Redis):
        self._bookings: Dict[str, Booking] = {}
        self._redis = redis_client
        self._lock = asyncio.Lock()
        self.logger = get_logger(__name__)
    
    async def create(self, booking: Booking) -> Booking:
        """Create a new booking with idempotency check"""
        async with self._lock:
            # Check for existing booking with same hold_id (idempotency)
            existing = await self.get_by_hold_id(booking.hold_id)
            if existing:
                self.logger.info("Booking already exists for hold", hold_id=booking.hold_id)
                return existing
            
            # Create new booking
            self._bookings[booking.id] = booking
            await self._cache_booking(booking)
            
            # Update booked seats count
            await self._increment_booked_seats(booking.event_id, booking.qty)
            
            self.logger.info(
                "Booking created", 
                booking_id=booking.id, 
                hold_id=booking.hold_id,
                event_id=booking.event_id,
                qty=booking.qty
            )
            return booking
    
    async def get_by_id(self, booking_id: str) -> Optional[Booking]:
        """Get booking by ID"""
        # Try cache first
        cached = await self._get_cached_booking(booking_id)
        if cached:
            return cached
        
        # Fallback to memory
        booking = self._bookings.get(booking_id)
        if booking:
            await self._cache_booking(booking)
        
        return booking
    
    async def get_by_hold_id(self, hold_id: str) -> Optional[Booking]:
        """Get booking by hold ID (for idempotency)"""
        for booking in self._bookings.values():
            if booking.hold_id == hold_id:
                return booking
        return None
    
    async def update(self, booking: Booking) -> Booking:
        """Update an existing booking"""
        async with self._lock:
            if booking.id not in self._bookings:
                raise ValueError(f"Booking {booking.id} not found")
            
            self._bookings[booking.id] = booking
            await self._cache_booking(booking)
            self.logger.info("Booking updated", booking_id=booking.id)
            return booking
    
    async def delete(self, booking_id: str) -> bool:
        """Delete booking by ID"""
        async with self._lock:
            booking = self._bookings.get(booking_id)
            if booking:
                # Decrement booked seats count
                await self._decrement_booked_seats(booking.event_id, booking.qty)
                
                del self._bookings[booking_id]
                await self._delete_cached_booking(booking_id)
                self.logger.info("Booking deleted", booking_id=booking_id)
                return True
            return False
    
    async def list_all(self) -> List[Booking]:
        """List all bookings"""
        return list(self._bookings.values())
    
    async def get_bookings_for_event(self, event_id: str) -> List[Booking]:
        """Get all bookings for an event"""
        bookings = []
        for booking in self._bookings.values():
            if booking.event_id == event_id:
                bookings.append(booking)
        return bookings
    
    async def _increment_booked_seats(self, event_id: str, qty: int) -> None:
        """Increment booked seats count for an event"""
        try:
            await self._redis.incrby(f"booked_seats:{event_id}", qty)
        except Exception as e:
            self.logger.error("Failed to increment booked seats", event_id=event_id, qty=qty, error=str(e))
    
    async def _decrement_booked_seats(self, event_id: str, qty: int) -> None:
        """Decrement booked seats count for an event"""
        try:
            await self._redis.decrby(f"booked_seats:{event_id}", qty)
        except Exception as e:
            self.logger.error("Failed to decrement booked seats", event_id=event_id, qty=qty, error=str(e))
    
    async def _cache_booking(self, booking: Booking) -> None:
        """Cache booking in Redis"""
        try:
            await self._redis.setex(
                f"booking:{booking.id}",
                3600,  # 1 hour TTL
                booking.model_dump_json()
            )
        except Exception as e:
            self.logger.warning("Failed to cache booking", booking_id=booking.id, error=str(e))
    
    async def _get_cached_booking(self, booking_id: str) -> Optional[Booking]:
        """Get booking from cache"""
        try:
            cached = await self._redis.get(f"booking:{booking_id}")
            if cached:
                return Booking.model_validate_json(cached)
        except Exception as e:
            self.logger.warning("Failed to get cached booking", booking_id=booking_id, error=str(e))
        return None
    
    async def _delete_cached_booking(self, booking_id: str) -> None:
        """Delete booking from cache"""
        try:
            await self._redis.delete(f"booking:{booking_id}")
        except Exception as e:
            self.logger.warning("Failed to delete cached booking", booking_id=booking_id, error=str(e))

