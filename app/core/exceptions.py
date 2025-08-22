from typing import Optional


class BoxOfficeException(Exception):
    """Base exception for Box Office service"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class EventNotFoundError(BoxOfficeException):
    """Raised when event is not found"""
    
    def __init__(self, event_id: str):
        super().__init__(f"Event with ID {event_id} not found", "EVENT_NOT_FOUND")


class HoldNotFoundError(BoxOfficeException):
    """Raised when hold is not found"""
    
    def __init__(self, hold_id: str):
        super().__init__(f"Hold with ID {hold_id} not found", "HOLD_NOT_FOUND")


class InsufficientSeatsError(BoxOfficeException):
    """Raised when there are insufficient seats available"""
    
    def __init__(self, requested: int, available: int):
        super().__init__(
            f"Requested {requested} seats but only {available} available",
            "INSUFFICIENT_SEATS"
        )


class InvalidPaymentTokenError(BoxOfficeException):
    """Raised when payment token is invalid"""
    
    def __init__(self, hold_id: str):
        super().__init__(
            f"Invalid payment token for hold {hold_id}",
            "INVALID_PAYMENT_TOKEN"
        )


class HoldExpiredError(BoxOfficeException):
    """Raised when hold has expired"""
    
    def __init__(self, hold_id: str):
        super().__init__(f"Hold {hold_id} has expired", "HOLD_EXPIRED")


class BookingAlreadyExistsError(BoxOfficeException):
    """Raised when booking already exists for a hold"""
    
    def __init__(self, hold_id: str):
        super().__init__(
            f"Booking already exists for hold {hold_id}",
            "BOOKING_ALREADY_EXISTS"
        )

