#!/usr/bin/env python3
"""
Demo script to demonstrate concurrent hold behavior and overbooking prevention.
This script shows how the system handles multiple simultaneous hold requests.
"""

import asyncio
import aiohttp
import json
from datetime import datetime


class BoxOfficeDemo:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_event(self, name, total_seats):
        """Create a new event"""
        url = f"{self.base_url}/api/v1/events"
        data = {"name": name, "total_seats": total_seats}
        
        async with self.session.post(url, json=data) as response:
            result = await response.json()
            print(f"✅ Created event: {result['event_id']} - {name} ({total_seats} seats)")
            return result['event_id']
    
    async def create_hold(self, event_id, qty, client_name):
        """Create a hold with timing information"""
        url = f"{self.base_url}/api/v1/holds"
        data = {"event_id": event_id, "qty": qty}
        
        start_time = datetime.now()
        try:
            async with self.session.post(url, json=data) as response:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                if response.status == 201:
                    result = await response.json()
                    print(f"✅ {client_name}: Hold created in {duration:.3f}s - {result['hold_id']} ({qty} seats)")
                    return result
                else:
                    error = await response.json()
                    print(f"❌ {client_name}: Hold failed in {duration:.3f}s - {error.get('error', 'Unknown error')}")
                    return None
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"❌ {client_name}: Exception in {duration:.3f}s - {str(e)}")
            return None
    
    async def get_event_status(self, event_id):
        """Get current event status"""
        url = f"{self.base_url}/api/v1/events/{event_id}/status"
        
        async with self.session.get(url) as response:
            result = await response.json()
            return result
    
    async def demo_concurrent_holds(self):
        """Demonstrate concurrent hold behavior"""
        print("🎭 Box Office Concurrent Hold Demo")
        print("=" * 50)
        
        # Step 1: Create an event with limited seats
        event_id = await self.create_event("Concurrent Demo Concert", 50)
        
        # Step 2: Show initial status
        status = await self.get_event_status(event_id)
        print(f"\n📊 Initial Status: {status['available']} seats available")
        
        # Step 3: Create multiple concurrent holds
        print(f"\n🚀 Creating concurrent holds...")
        
        # Define hold requests that would exceed capacity
        hold_requests = [
            ("Client A", 30),  # 30 seats
            ("Client B", 25),  # 25 seats (should fail - would exceed 50)
            ("Client C", 15),  # 15 seats
            ("Client D", 20),  # 20 seats (should fail - would exceed 50)
        ]
        
        # Create all holds concurrently
        tasks = [
            self.create_hold(event_id, qty, client_name)
            for client_name, qty in hold_requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Step 4: Show final status
        print(f"\n📊 Final Status:")
        final_status = await self.get_event_status(event_id)
        print(f"   Total seats: {final_status['total']}")
        print(f"   Available: {final_status['available']}")
        print(f"   Held: {final_status['held']}")
        print(f"   Booked: {final_status['booked']}")
        
        # Step 5: Analysis
        print(f"\n📈 Analysis:")
        successful_holds = [r for r in results if r is not None]
        failed_holds = [r for r in results if r is None]
        
        print(f"   Successful holds: {len(successful_holds)}")
        print(f"   Failed holds: {len(failed_holds)}")
        
        total_held = sum(r['qty'] for r in successful_holds)
        print(f"   Total seats held: {total_held}")
        
        if total_held <= final_status['total']:
            print("   ✅ No overbooking occurred!")
        else:
            print("   ❌ Overbooking detected!")
        
        return event_id, results


async def main():
    """Main demo function"""
    async with BoxOfficeDemo() as demo:
        try:
            event_id, results = await demo.demo_concurrent_holds()
            
            print(f"\n🎉 Demo completed successfully!")
            print(f"Event ID: {event_id}")
            
        except Exception as e:
            print(f"❌ Demo failed: {str(e)}")
            print("Make sure the Box Office API is running on http://localhost:8080")


if __name__ == "__main__":
    print("Starting Box Office Concurrent Hold Demo...")
    print("Make sure the API is running: docker-compose up -d")
    print()
    
    asyncio.run(main())

