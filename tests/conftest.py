import pytest
import asyncio
import redis.asyncio as redis
from httpx import AsyncClient
from app.main import app
from app.core.config import config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def redis_client():
    """Redis client fixture"""
    client = redis.from_url(config.redis_url)
    yield client
    await client.close()


@pytest.fixture
async def async_client():
    """Async HTTP client fixture"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def sample_event():
    """Sample event data"""
    return {
        "name": "Test Concert",
        "total_seats": 100
    }


@pytest.fixture
async def sample_hold():
    """Sample hold data"""
    return {
        "event_id": "test-event-id",
        "qty": 5
    }


@pytest.fixture
async def sample_booking():
    """Sample booking data"""
    return {
        "hold_id": "test-hold-id",
        "payment_token": "test-payment-token"
    }

