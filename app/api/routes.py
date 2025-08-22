from fastapi import APIRouter, Depends, HTTPException, status
from app.models.event import EventCreate, EventResponse
from app.models.hold import HoldCreate, HoldResponse
from app.models.booking import BookingCreate, BookingResponse
from app.services.event_service import EventService
from app.services.hold_service import HoldService
from app.services.booking_service import BookingService
from app.api.dependencies import (
    get_event_service, get_hold_service, get_booking_service
)

router = APIRouter(prefix="/api/v1", tags=["box-office"])


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    event_service: EventService = Depends(get_event_service)
) -> EventResponse:
    """Create a new event"""
    return await event_service.create_event(event_data)

@router.get("/events/{event_id}")
async def get_event_status(
    event_id: str,
    event_service: EventService = Depends(get_event_service)
) -> dict:
    """Get event status with seat counts"""
    return await event_service.get_event_status(event_id)


@router.post("/holds", response_model=HoldResponse, status_code=status.HTTP_201_CREATED)
async def create_hold(
    hold_data: HoldCreate,
    ttl_seconds: int | None = None,
    hold_service: HoldService = Depends(get_hold_service)
) -> HoldResponse:
    """Create a temporary hold on seats"""
    return await hold_service.create_hold(hold_data, ttl_seconds)

@router.post("/book", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreate,
    booking_service: BookingService = Depends(get_booking_service)
) -> BookingResponse:
    """Confirm a booking using an active hold"""
    return await booking_service.create_booking(booking_data)


# Bonus endpoints
@router.get("/metrics")
async def get_metrics(
    event_service: EventService = Depends(get_event_service),
    hold_service: HoldService = Depends(get_hold_service),
    booking_service: BookingService = Depends(get_booking_service)
) -> dict:
    """Get system metrics"""
    events = await event_service.list_events()
    bookings = await booking_service.list_bookings()
    
    total_events = len(events)
    total_bookings = len(bookings)
    
    # Calculate active holds
    active_holds = 0
    for event in events:
        holds = await hold_service.get_active_holds_for_event(event.event_id)
        active_holds += len(holds)
    
    # Expiry count metric (best-effort)
    expired_holds_total = 0
    try:
        # Access redis via hold service repository
        redis_client = hold_service._hold_repository._redis
        value = await redis_client.get("expired_holds_total")
        expired_holds_total = int(value) if value else 0
    except Exception:
        pass

    return {
        "total_events": total_events,
        "total_bookings": total_bookings,
        "active_holds": active_holds,
        "total_seats_booked": sum(booking.qty for booking in bookings),
        "expired_holds_total": expired_holds_total
    }


@router.post("/holds/{hold_id}/expire")
async def expire_hold(
    hold_id: str,
    hold_service: HoldService = Depends(get_hold_service)
) -> dict:
    """Manually expire a hold (for testing)"""
    success = await hold_service.expire_hold(hold_id)
    return {"success": success, "hold_id": hold_id}


# Health check endpoint
@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {"status": "healthy", "service": "Box Office API"}

