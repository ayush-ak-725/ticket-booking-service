from typing import List, Optional
from datetime import datetime, timedelta, timezone
from app.models.hold import Hold, HoldCreate, HoldResponse
from app.repositories.hold_repository import HoldRepository
from app.repositories.event_repository import EventRepository
from app.core.exceptions import (
    EventNotFoundError, HoldNotFoundError, InsufficientSeatsError,
    HoldExpiredError, InvalidPaymentTokenError
)
from app.core.logging import get_logger
from app.core.config import config


class HoldService:
    """Hold service with business logic and concurrency control"""
    
    def __init__(self, hold_repository: HoldRepository, event_repository: EventRepository):
        self._hold_repository = hold_repository
        self._event_repository = event_repository
        self.logger = get_logger(__name__)
    
    async def create_hold(self, hold_data: HoldCreate, ttl_seconds: Optional[int] = None) -> HoldResponse:
        """Create a new hold with seat reservation"""
        # Validate event exists
        event = await self._event_repository.get_by_id(hold_data.event_id)
        if not event:
            raise EventNotFoundError(hold_data.event_id)
        
        # Determine TTL with sensible caps
        default_ttl = config.hold_ttl_minutes * 60
        min_ttl = max(1, getattr(config, 'hold_ttl_min_seconds', 10))
        max_ttl = max(min_ttl, getattr(config, 'hold_ttl_max_seconds', 900))
        if ttl_seconds is None:
            effective_ttl = default_ttl
        else:
            effective_ttl = max(min_ttl, min(int(ttl_seconds), max_ttl))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=effective_ttl)

        # Create hold with automatic seat reservation
        hold = Hold(
            event_id=hold_data.event_id,
            qty=hold_data.qty,
            expires_at=expires_at
        )
        
        try:
            created_hold = await self._hold_repository.create(hold)
            self.logger.info(
                "Hold created successfully", 
                hold_id=created_hold.id,
                event_id=created_hold.event_id,
                qty=created_hold.qty,
                ttl_seconds=effective_ttl
            )
            return created_hold.to_response()
        except InsufficientSeatsError as e:
            self.logger.warning(
                "Insufficient seats for hold request",
                event_id=hold_data.event_id,
                requested=hold_data.qty,
                available=e.available
            )
            raise
    
    async def get_hold(self, hold_id: str) -> HoldResponse:
        """Get hold by ID"""
        hold = await self._hold_repository.get_by_id(hold_id)
        if not hold:
            raise HoldNotFoundError(hold_id)
        
        return hold.to_response()
    
    async def expire_hold(self, hold_id: str) -> bool:
        """Expire a hold and release seats"""
        hold = await self._hold_repository.get_by_id(hold_id)
        if not hold:
            raise HoldNotFoundError(hold_id)
        
        if hold.is_expired:
            raise HoldExpiredError(hold_id)
        
        success = await self._hold_repository.expire_hold(hold_id)
        if success:
            self.logger.info("Hold expired successfully", hold_id=hold_id)
        
        return success
    
    async def get_active_holds_for_event(self, event_id: str) -> List[HoldResponse]:
        """Get all active holds for an event"""
        holds = await self._hold_repository.get_active_holds_for_event(event_id)
        return [hold.to_response() for hold in holds]
    
    async def validate_hold_for_booking(self, hold_id: str, payment_token: str) -> Hold:
        """Validate hold for booking (used by booking service)"""
        hold = await self._hold_repository.get_by_id(hold_id)
        if not hold:
            raise HoldNotFoundError(hold_id)
        
        if hold.is_expired:
            raise HoldExpiredError(hold_id)
        
        if hold.payment_token != payment_token:
            raise InvalidPaymentTokenError(hold_id)
        
        return hold

