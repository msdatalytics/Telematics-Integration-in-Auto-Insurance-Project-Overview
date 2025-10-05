"""
Redis Streams producer for telematics events.
"""
import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
import redis
import numpy as np

from ..settings import settings


class TelematicsProducer:
    """Producer for telematics events to Redis Streams."""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.stream_name = "telematics:events"
    
    async def generate_realistic_events(self, user_id: int, vehicle_id: int, 
                                      num_events: int = 100) -> List[Dict[str, Any]]:
        """Generate realistic telematics events."""
        events = []
        
        # Generate trip parameters
        start_time = datetime.utcnow() - timedelta(hours=random.randint(1, 24))
        duration_minutes = random.uniform(10, 120)
        
        # Starting location (NYC area)
        start_lat = 40.7128 + random.uniform(-0.1, 0.1)
        start_lon = -74.0060 + random.uniform(-0.1, 0.1)
        
        # Generate GPS path
        num_points = min(num_events, int(duration_minutes * 2))
        end_lat = start_lat + random.uniform(-0.01, 0.01)
        end_lon = start_lon + random.uniform(-0.01, 0.01)
        
        lats = np.linspace(start_lat, end_lat, num_points)
        lons = np.linspace(start_lon, end_lon, num_points)
        
        # Add realistic noise
        lats += np.random.normal(0, 0.001, num_points)
        lons += np.random.normal(0, 0.001, num_points)
        
        # Generate speeds (start slow, peak in middle, slow at end)
        speeds = []
        for i in range(num_points):
            progress = i / (num_points - 1)
            base_speed = 20 + 50 * (1 - abs(progress - 0.5) * 2)
            speed = max(0, base_speed + random.uniform(-10, 10))
            speeds.append(speed)
        
        # Generate accelerations and brake intensities
        accelerations = []
        brake_intensities = []
        
        for i in range(num_points):
            if i == 0:
                accel = random.uniform(-2, 2)
            else:
                speed_diff = speeds[i] - speeds[i-1]
                accel = speed_diff / 3.6  # Convert to m/s²
                accel += random.uniform(-1, 1)
            
            accelerations.append(accel)
            brake_intensity = max(0, min(1, -accel / 5)) if accel < 0 else 0
            brake_intensities.append(brake_intensity)
        
        # Create events
        for i in range(num_points):
            progress = i / (num_points - 1)
            event_time = start_time + timedelta(minutes=progress * duration_minutes)
            
            event = {
                "event_id": str(uuid.uuid4()),
                "user_id": user_id,
                "vehicle_id": vehicle_id,
                "timestamp": event_time.isoformat(),
                "lat": round(lats[i], 5),  # Privacy: bucketize to 5 decimal places
                "lon": round(lons[i], 5),
                "speed_kph": speeds[i],
                "accel_ms2": accelerations[i],
                "brake_intensity": brake_intensities[i],
                "heading": random.uniform(0, 360),
                "altitude": random.uniform(0, 100),
                "accuracy": random.uniform(3, 10),
                "event_type": "telematics"
            }
            
            events.append(event)
        
        return events
    
    async def produce_events(self, events: List[Dict[str, Any]]) -> int:
        """Produce events to Redis Stream."""
        produced_count = 0
        
        for event in events:
            try:
                # Add to Redis Stream
                message_id = self.redis_client.xadd(
                    self.stream_name,
                    event,
                    maxlen=10000  # Keep last 10k events
                )
                produced_count += 1
                
            except Exception as e:
                print(f"Error producing event {event['event_id']}: {e}")
                continue
        
        return produced_count
    
    async def simulate_user_trips(self, user_id: int, vehicle_id: int, 
                                num_trips: int = 5) -> int:
        """Simulate multiple trips for a user."""
        total_events = 0
        
        for trip_num in range(num_trips):
            # Generate events for this trip
            events = await self.generate_realistic_events(
                user_id, vehicle_id, num_events=random.randint(20, 100)
            )
            
            # Produce events
            produced = await self.produce_events(events)
            total_events += produced
            
            # Small delay between trips
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        return total_events


async def main():
    """Main function for running the producer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Telematics Event Producer")
    parser.add_argument("--users", type=int, default=10, help="Number of users to simulate")
    parser.add_argument("--trips", type=int, default=50, help="Total number of trips to generate")
    parser.add_argument("--events-per-trip", type=int, default=50, help="Events per trip")
    
    args = parser.parse_args()
    
    producer = TelematicsProducer()
    
    print(f"Starting telematics producer...")
    print(f"Users: {args.users}, Trips: {args.trips}, Events per trip: {args.events_per_trip}")
    
    total_events = 0
    
    # Generate trips for multiple users
    trips_per_user = args.trips // args.users
    
    for user_id in range(1, args.users + 1):
        vehicle_id = user_id  # Simple mapping
        
        print(f"Generating trips for user {user_id}...")
        
        events_generated = await producer.simulate_user_trips(
            user_id, vehicle_id, trips_per_user
        )
        
        total_events += events_generated
        print(f"Generated {events_generated} events for user {user_id}")
    
    print(f"Total events generated: {total_events}")
    print("Producer finished.")


if __name__ == "__main__":
    asyncio.run(main())
