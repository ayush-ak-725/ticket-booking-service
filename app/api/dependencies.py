import redis.asyncio as redis
from typing import Generator
from fastapi import Depends
from app.core.config import config
from app.core.redis_mock import MockRedis
from app.repositories.event_repository import EventRepository
from app.repositories.hold_repository import HoldRepository
from app.repositories.booking_repository import BookingRepository
from app.services.event_service import EventService
from app.services.hold_service import HoldService
from app.services.booking_service import BookingService
from app.services.expiry_service import ExpiryService


async def get_redis_client():
    """Get Redis client or mock"""
    try:
        client = redis.from_url(config.redis_url)
        await client.ping()
        try:
            yield client
        finally:
            await client.close()
    except Exception:
        # Fallback to mock Redis
        mock_client = MockRedis()
        try:
            yield mock_client
        finally:
            await mock_client.close()


async def get_event_repository() -> EventRepository:
    """Get event repository"""
    if not services.event_repository:
        await services.initialize()
    return services.event_repository


async def get_hold_repository(
    event_repo: EventRepository = Depends(get_event_repository)
) -> HoldRepository:
    """Get hold repository"""
    if not services.hold_repository:
        await services.initialize()
    return services.hold_repository


async def get_booking_repository() -> BookingRepository:
    """Get booking repository"""
    if not services.booking_repository:
        await services.initialize()
    return services.booking_repository


async def get_event_service(
    event_repo: EventRepository = Depends(get_event_repository)
) -> EventService:
    """Get event service"""
    return EventService(event_repo)


async def get_hold_service(
    hold_repo: HoldRepository = Depends(get_hold_repository),
    event_repo: EventRepository = Depends(get_event_repository)
) -> HoldService:
    """Get hold service"""
    return HoldService(hold_repo, event_repo)


async def get_booking_service(
    booking_repo: BookingRepository = Depends(get_booking_repository),
    hold_service: HoldService = Depends(get_hold_service)
) -> BookingService:
    """Get booking service"""
    return BookingService(booking_repo, hold_service)


async def get_expiry_service(
    hold_repo: HoldRepository = Depends(get_hold_repository)
) -> ExpiryService:
    """Get expiry service"""
    return ExpiryService(hold_repo)


class ServiceContainer:
    """Container for all services"""
    
    def __init__(self):
        self.redis_client = None
        self.event_repository = None
        self.hold_repository = None
        self.booking_repository = None
        self.event_service = None
        self.hold_service = None
        self.booking_service = None
        self.expiry_service = None
    
    async def initialize(self):
        """Initialize all services"""
        try:
            self.redis_client = redis.from_url(config.redis_url)
            await self.redis_client.ping()
        except Exception:
            # Fallback to mock Redis
            self.redis_client = MockRedis()
        
        self.event_repository = EventRepository(self.redis_client)
        self.hold_repository = HoldRepository(self.redis_client, self.event_repository)
        self.booking_repository = BookingRepository(self.redis_client)
        self.event_service = EventService(self.event_repository)
        self.hold_service = HoldService(self.hold_repository, self.event_repository)
        self.booking_service = BookingService(self.booking_repository, self.hold_service)
        self.expiry_service = ExpiryService(self.hold_repository)
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()


# Global service container
services = ServiceContainer()


async def get_services() -> ServiceContainer:
    """Get service container"""
    return services
