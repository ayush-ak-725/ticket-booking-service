import json
import asyncio
from typing import Optional, List, Dict
from app.models.hold import Hold, HoldStatus
from app.repositories.base import BaseRepository
from app.core.logging import get_logger
from app.core.exceptions import InsufficientSeatsError
import redis.asyncio as redis


class HoldRepository(BaseRepository[Hold]):
    """Hold repository with Redis-based seat management"""
    
    def __init__(self, redis_client: redis.Redis, event_repository=None):
        self._holds: Dict[str, Hold] = {}
        self._redis = redis_client
        self._event_repository = event_repository
        self._lock = asyncio.Lock()
        self.logger = get_logger(__name__)
    
    async def create(self, hold: Hold) -> Hold:
        """Create a new hold with seat reservation"""
        async with self._lock:
            # Check seat availability
            available = await self._get_available_seats(hold.event_id)
            if available < hold.qty:
                raise InsufficientSeatsError(hold.qty, available)
            
            # Reserve seats atomically
            await self._reserve_seats(hold.event_id, hold.qty)
            
            # Store hold
            self._holds[hold.id] = hold
            # Temporarily bypass caching
            # await self._cache_hold(hold)
            
            self.logger.info(
                "Hold created", 
                hold_id=hold.id, 
                event_id=hold.event_id, 
                qty=hold.qty
            )
            return hold
    
    async def get_by_id(self, hold_id: str) -> Optional[Hold]:
        """Get hold by ID"""
        # Temporarily bypass cache
        # cached = await self._get_cached_hold(hold_id)
        # if cached:
        #     return cached
        
        # Fallback to memory
        hold = self._holds.get(hold_id)
        if hold:
            # await self._cache_hold(hold)
            pass
        
        return hold
    
    async def update(self, hold: Hold) -> Hold:
        """Update an existing hold"""
        async with self._lock:
            if hold.id not in self._holds:
                raise ValueError(f"Hold {hold.id} not found")
            
            self._holds[hold.id] = hold
            await self._cache_hold(hold)
            self.logger.info("Hold updated", hold_id=hold.id, status=hold.status)
            return hold
    
    async def delete(self, hold_id: str) -> bool:
        """Delete hold by ID and release seats"""
        async with self._lock:
            hold = self._holds.get(hold_id)
            if hold:
                # Release seats if hold was active
                if hold.status == HoldStatus.ACTIVE:
                    await self._release_seats(hold.event_id, hold.qty)
                
                del self._holds[hold_id]
                await self._delete_cached_hold(hold_id)
                self.logger.info("Hold deleted", hold_id=hold_id)
                return True
            return False
    
    async def list_all(self) -> List[Hold]:
        """List all holds"""
        return list(self._holds.values())
    
    async def get_active_holds_for_event(self, event_id: str) -> List[Hold]:
        """Get all active holds for an event"""
        active_holds = []
        for hold in self._holds.values():
            if hold.event_id == event_id and hold.is_active:
                active_holds.append(hold)
        return active_holds
    
    async def expire_hold(self, hold_id: str, correlation_id: str | None = None) -> bool:
        """Expire a hold and release seats"""
        async with self._lock:
            hold = self._holds.get(hold_id)
            if hold and hold.status == HoldStatus.ACTIVE:
                # Read counters before
                before = await self._redis.get(f"held_seats:{hold.event_id}")
                held_before = int(before) if before else 0
                self.logger.info(
                    "Expiring hold",
                    correlation_id=correlation_id,
                    hold_id=hold_id,
                    event_id=hold.event_id,
                    qty=hold.qty,
                    held_before=held_before,
                )
                hold.expire()
                await self._release_seats(hold.event_id, hold.qty, correlation_id)
                await self._cache_hold(hold)
                # Read counters after
                after = await self._redis.get(f"held_seats:{hold.event_id}")
                held_after = int(after) if after else 0
                self.logger.info(
                    "Hold expired",
                    correlation_id=correlation_id,
                    hold_id=hold_id,
                    event_id=hold.event_id,
                    held_after=held_after,
                )
                return True
            else:
                self.logger.warning(
                    "Hold not found or not active",
                    correlation_id=correlation_id,
                    hold_id=hold_id,
                    hold_found=hold is not None,
                    status=hold.status if hold else None,
                )
            return False
    
    async def confirm_hold(self, hold_id: str) -> bool:
        """Confirm a hold (mark as confirmed)"""
        async with self._lock:
            hold = self._holds.get(hold_id)
            if hold and hold.status == HoldStatus.ACTIVE:
                # Release the held seats when confirming, as booking will account in booked counter
                await self._release_seats(hold.event_id, hold.qty)
                hold.confirm()
                await self._cache_hold(hold)
                self.logger.info("Hold confirmed", hold_id=hold_id)
                return True
            return False
    
    async def _reserve_seats(self, event_id: str, qty: int) -> None:
        """Reserve seats atomically"""
        try:
            # Simplified approach for MockRedis
            current_held = await self._redis.get(f"held_seats:{event_id}")
            current_held = int(current_held) if current_held else 0
            
            # Check total capacity
            event_key = f"event:{event_id}"
            event_data = await self._redis.get(event_key)
            if event_data:
                event = json.loads(event_data)
                total_seats = event.get('total_seats', 0)
                if current_held + qty > total_seats:
                    raise InsufficientSeatsError(qty, total_seats - current_held)
            
            # Reserve seats
            await self._redis.incrby(f"held_seats:{event_id}", qty)
                
        except Exception as e:
            self.logger.error("Failed to reserve seats", event_id=event_id, qty=qty, error=str(e))
            raise
    
    async def _release_seats(self, event_id: str, qty: int, correlation_id: str | None = None) -> None:
        """Release reserved seats"""
        try:
            current_held = await self._redis.get(f"held_seats:{event_id}")
            current_held = int(current_held) if current_held else 0
            self.logger.info(
                "Before releasing seats",
                correlation_id=correlation_id,
                event_id=event_id,
                qty=qty,
                held_before=current_held,
            )
            
            # Ensure we do not go below zero
            if qty >= current_held:
                await self._redis.set(f"held_seats:{event_id}", "0")
            else:
                await self._redis.decrby(f"held_seats:{event_id}", qty)
            
            new_held = await self._redis.get(f"held_seats:{event_id}")
            new_held = int(new_held) if new_held else 0
            self.logger.info(
                "After releasing seats",
                correlation_id=correlation_id,
                event_id=event_id,
                qty=qty,
                held_after=new_held,
            )
        except Exception as e:
            self.logger.error(
                "Failed to release seats",
                correlation_id=correlation_id,
                event_id=event_id,
                qty=qty,
                error=str(e),
            )
    
    async def _get_available_seats(self, event_id: str) -> int:
        """Get available seats for an event"""
        try:
            # Get event from repository if available
            if self._event_repository:
                event = await self._event_repository.get_by_id(event_id)
                if event:
                    total_seats = event.total_seats
                else:
                    return 0
            else:
                # Fallback to Redis cache
                event_data = await self._redis.get(f"event:{event_id}")
                if not event_data:
                    return 0
                
                event = json.loads(event_data)
                total_seats = event.get('total_seats', 0)
            
            # Get held and booked seats
            held_seats = await self._redis.get(f"held_seats:{event_id}")
            held_seats = int(held_seats) if held_seats else 0
            
            booked_seats = await self._redis.get(f"booked_seats:{event_id}")
            booked_seats = int(booked_seats) if booked_seats else 0
            
            available = total_seats - held_seats - booked_seats
            return max(0, available)
            
        except Exception as e:
            self.logger.error("Failed to get available seats", event_id=event_id, error=str(e))
            return 0
    
    async def _cache_hold(self, hold: Hold) -> None:
        """Cache hold in Redis"""
        try:
            await self._redis.setex(
                f"hold:{hold.id}",
                3600,  # 1 hour TTL
                hold.model_dump_json()
            )
        except Exception as e:
            self.logger.warning("Failed to cache hold", hold_id=hold.id, error=str(e))
    
    async def _get_cached_hold(self, hold_id: str) -> Optional[Hold]:
        """Get hold from cache"""
        try:
            cached = await self._redis.get(f"hold:{hold_id}")
            if cached:
                return Hold.model_validate_json(cached)
        except Exception as e:
            self.logger.warning("Failed to get cached hold", hold_id=hold_id, error=str(e))
        return None
    
    async def _delete_cached_hold(self, hold_id: str) -> None:
        """Delete hold from cache"""
        try:
            await self._redis.delete(f"hold:{hold_id}")
        except Exception as e:
            self.logger.warning("Failed to delete cached hold", hold_id=hold_id, error=str(e))

