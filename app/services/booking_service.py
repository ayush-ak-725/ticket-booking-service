from typing import List
from app.models.booking import Booking, BookingCreate, BookingResponse
from app.repositories.booking_repository import BookingRepository
from app.services.hold_service import HoldService
from app.core.exceptions import (
    BookingAlreadyExistsError, InvalidPaymentTokenError
)
from app.core.logging import get_logger


class BookingService:
    """Booking service with idempotency support"""
    
    def __init__(self, booking_repository: BookingRepository, hold_service: HoldService):
        self._booking_repository = booking_repository
        self._hold_service = hold_service
        self.logger = get_logger(__name__)
    
    async def create_booking(self, booking_data: BookingCreate) -> BookingResponse:
        """Create a new booking with idempotency support"""
        # Validate hold and payment token
        hold = await self._hold_service.validate_hold_for_booking(
            booking_data.hold_id, 
            booking_data.payment_token
        )
        
        # Check for existing booking (idempotency)
        existing_booking = await self._booking_repository.get_by_hold_id(booking_data.hold_id)
        if existing_booking:
            self.logger.info(
                "Booking already exists for hold (idempotent retry)",
                hold_id=booking_data.hold_id,
                booking_id=existing_booking.id
            )
            return existing_booking.to_response()
        
        # Create new booking
        booking = Booking(
            hold_id=booking_data.hold_id,
            event_id=hold.event_id,
            qty=hold.qty,
            payment_token=booking_data.payment_token
        )
        
        created_booking = await self._booking_repository.create(booking)
        
        # Confirm the hold
        await self._hold_service._hold_repository.confirm_hold(booking_data.hold_id)
        
        self.logger.info(
            "Booking created successfully",
            booking_id=created_booking.id,
            hold_id=booking_data.hold_id,
            event_id=hold.event_id
        )
        
        return created_booking.to_response()
    
    async def get_booking(self, booking_id: str) -> BookingResponse:
        """Get booking by ID"""
        booking = await self._booking_repository.get_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking {booking_id} not found")
        
        return booking.to_response()
    
    async def get_bookings_for_event(self, event_id: str) -> List[BookingResponse]:
        """Get all bookings for an event"""
        bookings = await self._booking_repository.get_bookings_for_event(event_id)
        return [booking.to_response() for booking in bookings]
    
    async def list_bookings(self) -> List[BookingResponse]:
        """List all bookings"""
        bookings = await self._booking_repository.list_all()
        return [booking.to_response() for booking in bookings]

