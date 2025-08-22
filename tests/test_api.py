import pytest
from httpx import AsyncClient


class TestEventAPI:
    """Test event-related API endpoints"""
    
    async def test_create_event(self, async_client: AsyncClient, sample_event):
        """Test creating a new event"""
        response = await async_client.post("/api/v1/events", json=sample_event)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_event["name"]
        assert data["total_seats"] == sample_event["total_seats"]
        assert "event_id" in data
        assert "created_at" in data
    
    async def test_get_event(self, async_client: AsyncClient, sample_event):
        """Test getting an event by ID"""
        # First create an event
        create_response = await async_client.post("/api/v1/events", json=sample_event)
        event_id = create_response.json()["event_id"]
        
        # Then get it
        response = await async_client.get(f"/api/v1/events/{event_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == event_id
        assert data["name"] == sample_event["name"]
    
    async def test_get_event_status(self, async_client: AsyncClient, sample_event):
        """Test getting event status"""
        # First create an event
        create_response = await async_client.post("/api/v1/events", json=sample_event)
        event_id = create_response.json()["event_id"]
        
        # Then get status
        response = await async_client.get(f"/api/v1/events/{event_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == sample_event["total_seats"]
        assert data["available"] == sample_event["total_seats"]
        assert data["held"] == 0
        assert data["booked"] == 0


class TestHoldAPI:
    """Test hold-related API endpoints"""
    
    async def test_create_hold(self, async_client: AsyncClient, sample_event, sample_hold):
        """Test creating a hold"""
        # First create an event
        create_event_response = await async_client.post("/api/v1/events", json=sample_event)
        event_id = create_event_response.json()["event_id"]
        
        # Update sample_hold with real event_id
        sample_hold["event_id"] = event_id
        
        # Create hold
        response = await async_client.post("/api/v1/holds", json=sample_hold)
        assert response.status_code == 201
        data = response.json()
        assert data["event_id"] == event_id
        assert data["qty"] == sample_hold["qty"]
        assert "hold_id" in data
        assert "payment_token" in data
        assert "expires_at" in data
    
    async def test_create_hold_insufficient_seats(self, async_client: AsyncClient, sample_event):
        """Test creating a hold with insufficient seats"""
        # First create an event with 10 seats
        sample_event["total_seats"] = 10
        create_event_response = await async_client.post("/api/v1/events", json=sample_event)
        event_id = create_event_response.json()["event_id"]
        
        # Try to hold 15 seats
        hold_data = {"event_id": event_id, "qty": 15}
        response = await async_client.post("/api/v1/holds", json=hold_data)
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "INSUFFICIENT_SEATS" in data["error_code"]
    
    async def test_get_hold(self, async_client: AsyncClient, sample_event, sample_hold):
        """Test getting a hold by ID"""
        # First create an event and hold
        create_event_response = await async_client.post("/api/v1/events", json=sample_event)
        event_id = create_event_response.json()["event_id"]
        sample_hold["event_id"] = event_id
        
        create_hold_response = await async_client.post("/api/v1/holds", json=sample_hold)
        hold_id = create_hold_response.json()["hold_id"]
        
        # Get the hold
        response = await async_client.get(f"/api/v1/holds/{hold_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["hold_id"] == hold_id
        assert data["event_id"] == event_id


class TestBookingAPI:
    """Test booking-related API endpoints"""
    
    async def test_create_booking(self, async_client: AsyncClient, sample_event, sample_hold):
        """Test creating a booking"""
        # First create an event
        create_event_response = await async_client.post("/api/v1/events", json=sample_event)
        event_id = create_event_response.json()["event_id"]
        
        # Create a hold
        sample_hold["event_id"] = event_id
        create_hold_response = await async_client.post("/api/v1/holds", json=sample_hold)
        hold_data = create_hold_response.json()
        hold_id = hold_data["hold_id"]
        payment_token = hold_data["payment_token"]
        
        # Create booking
        booking_data = {
            "hold_id": hold_id,
            "payment_token": payment_token
        }
        response = await async_client.post("/api/v1/book", json=booking_data)
        assert response.status_code == 201
        data = response.json()
        assert data["hold_id"] == hold_id
        assert data["event_id"] == event_id
        assert data["qty"] == sample_hold["qty"]
        assert "booking_id" in data
    
    async def test_create_booking_idempotent(self, async_client: AsyncClient, sample_event, sample_hold):
        """Test booking idempotency"""
        # First create an event
        create_event_response = await async_client.post("/api/v1/events", json=sample_event)
        event_id = create_event_response.json()["event_id"]
        
        # Create a hold
        sample_hold["event_id"] = event_id
        create_hold_response = await async_client.post("/api/v1/holds", json=sample_hold)
        hold_data = create_hold_response.json()
        hold_id = hold_data["hold_id"]
        payment_token = hold_data["payment_token"]
        
        # Create booking
        booking_data = {
            "hold_id": hold_id,
            "payment_token": payment_token
        }
        response1 = await async_client.post("/api/v1/book", json=booking_data)
        assert response1.status_code == 201
        booking_id1 = response1.json()["booking_id"]
        
        # Create same booking again (idempotent)
        response2 = await async_client.post("/api/v1/book", json=booking_data)
        assert response2.status_code == 201
        booking_id2 = response2.json()["booking_id"]
        
        # Should return the same booking
        assert booking_id1 == booking_id2


class TestMetricsAPI:
    """Test metrics API endpoint"""
    
    async def test_get_metrics(self, async_client: AsyncClient):
        """Test getting system metrics"""
        response = await async_client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "total_bookings" in data
        assert "active_holds" in data
        assert "total_seats_booked" in data


class TestHealthAPI:
    """Test health check endpoint"""
    
    async def test_health_check(self, async_client: AsyncClient):
        """Test health check endpoint"""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Box Office API"

