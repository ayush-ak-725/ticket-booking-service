import asyncio
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_no_overbooking_under_parallel_holds(async_client: AsyncClient):
    # Create an event with a small capacity
    total_seats = 10
    create_event_resp = await async_client.post(
        "/api/v1/events", json={"name": "Parallel Show", "total_seats": total_seats}
    )
    assert create_event_resp.status_code == 201
    event_id = create_event_resp.json()["event_id"]

    # Fetch initial status
    status_before = await async_client.get(f"/api/v1/events/{event_id}/status")
    assert status_before.status_code == 200
    sb = status_before.json()
    assert sb["total"] == total_seats

    # Prepare two holds whose combined qty exceeds availability by 1
    # e.g., 5 and 6 when total is 10
    q_total = sb["available"] + 1
    q1 = max(1, q_total // 2)
    q2 = q_total - q1
    body1 = {"event_id": event_id, "qty": q1}
    body2 = {"event_id": event_id, "qty": q2}

    async def post_hold(body):
        return await async_client.post("/api/v1/holds", json=body)

    # Fire concurrently
    r1, r2 = await asyncio.gather(post_hold(body1), post_hold(body2))

    # One must succeed (201), the other must fail (400)
    codes = sorted([r1.status_code, r2.status_code])
    assert codes == [400, 201]

    # Check invariant: held + booked <= total, and none negative
    status_after = await async_client.get(f"/api/v1/events/{event_id}/status")
    assert status_after.status_code == 200
    sa = status_after.json()
    assert 0 <= sa["held"] <= total_seats
    assert 0 <= sa["booked"] <= total_seats
    assert sa["held"] + sa["booked"] <= total_seats
    assert sa["available"] == total_seats - sa["held"] - sa["booked"]


