import asyncio
from datetime import datetime
from typing import List, Tuple
import uuid
from app.repositories.hold_repository import HoldRepository
from app.core.logging import get_logger


class ExpiryService:
    """Service for handling hold expiration"""
    
    def __init__(self, hold_repository: HoldRepository):
        self._hold_repository = hold_repository
        self.logger = get_logger(__name__)
        self._running = False
        self._task = None
    
    async def start_expiry_worker(self) -> None:
        """Start the expiry worker task"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._expiry_worker())
        self.logger.info("Expiry worker started")
    
    async def stop_expiry_worker(self) -> None:
        """Stop the expiry worker task"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Expiry worker stopped")
    
    async def _expiry_worker(self) -> None:
        """Worker task that periodically checks for expired holds"""
        while self._running:
            try:
                await self._process_expired_holds()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in expiry worker", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _process_expired_holds(self) -> None:
        """Process all expired holds"""
        holds = await self._hold_repository.list_all()
        expired_count = 0
        
        for hold in holds:
            if hold.is_expired and hold.status.value == "active":
                try:
                    correlation_id = str(uuid.uuid4())
                    # Read counts before
                    available_before, held_before, booked_before = await self._read_seat_counts(hold.event_id)
                    self.logger.info(
                        "Expiry worker processing hold",
                        correlation_id=correlation_id,
                        hold_id=hold.id,
                        event_id=hold.event_id,
                        available_before=available_before,
                        held_before=held_before,
                        booked_before=booked_before,
                    )

                    await self._hold_repository.expire_hold(hold.id, correlation_id)

                    # Read counts after
                    available_after, held_after, booked_after = await self._read_seat_counts(hold.event_id)
                    self.logger.info(
                        "Expiry worker expired hold",
                        correlation_id=correlation_id,
                        hold_id=hold.id,
                        event_id=hold.event_id,
                        available_after=available_after,
                        held_after=held_after,
                        booked_after=booked_after,
                    )
                    expired_count += 1
                except Exception as e:
                    self.logger.error(
                        "Failed to expire hold",
                        hold_id=hold.id,
                        error=str(e)
                    )
        
        if expired_count > 0:
            # Track total expiries in redis counter for metrics
            try:
                await self._hold_repository._redis.incrby("expired_holds_total", expired_count)
            except Exception:
                pass
            self.logger.info(f"Expired {expired_count} holds")

    async def _read_seat_counts(self, event_id: str) -> Tuple[int, int, int]:
        """Read available, held, booked counts for an event from repositories/redis"""
        try:
            # Total seats from event repo (if available)
            total_seats = 0
            if getattr(self._hold_repository, "_event_repository", None):
                event = await self._hold_repository._event_repository.get_by_id(event_id)
                if event:
                    total_seats = event.total_seats
            
            # Counters from redis
            redis_client = self._hold_repository._redis
            held_value = await redis_client.get(f"held_seats:{event_id}")
            booked_value = await redis_client.get(f"booked_seats:{event_id}")
            held = int(held_value) if held_value else 0
            booked = int(booked_value) if booked_value else 0
            available = max(0, total_seats - held - booked)
            return (available, held, booked)
        except Exception as error:
            self.logger.warning("Failed to read seat counts in expiry worker", event_id=event_id, error=str(error))
            return (0, 0, 0)
    
    async def expire_hold_manually(self, hold_id: str) -> bool:
        """Manually expire a specific hold"""
        try:
            success = await self._hold_repository.expire_hold(hold_id)
            if success:
                self.logger.info("Hold manually expired", hold_id=hold_id)
            return success
        except Exception as e:
            self.logger.error("Failed to manually expire hold", hold_id=hold_id, error=str(e))
            return False

