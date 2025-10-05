"""
Redis Streams consumer for telematics events.
"""
import asyncio
import json
import redis
from datetime import datetime, timedelta
from typing import Dict, Any, List
import uuid

from ..settings import settings
from ..db.base import SessionLocal
from ..db import crud, models


class TelematicsConsumer:
    """Consumer for telematics events from Redis Streams."""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.stream_name = "telematics:events"
        self.consumer_group = "telematics-processors"
        self.consumer_name = f"consumer-{uuid.uuid4().hex[:8]}"
        self.batch_size = 100
        self.processing_interval = 5  # seconds
    
    async def initialize_consumer_group(self):
        """Initialize Redis Stream consumer group."""
        try:
            self.redis_client.xgroup_create(
                self.stream_name, 
                self.consumer_group, 
                id="0", 
                mkstream=True
            )
            print(f"Created consumer group: {self.consumer_group}")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                print(f"Consumer group {self.consumer_group} already exists")
            else:
                raise e
    
    async def process_events_batch(self, events: List[Dict[str, Any]]) -> int:
        """Process a batch of telematics events."""
        db = SessionLocal()
        processed_count = 0
        
        try:
            # Group events by trip (simplified - in production would use trip detection)
            trip_events = {}
            
            for event in events:
                # Create a trip key based on user, vehicle, and time window
                trip_key = f"{event['user_id']}_{event['vehicle_id']}_{event['timestamp'][:10]}"  # Daily grouping
                
                if trip_key not in trip_events:
                    trip_events[trip_key] = []
                
                trip_events[trip_key].append(event)
            
            # Process each trip
            for trip_key, trip_event_list in trip_events.items():
                try:
                    await self.process_trip_events(db, trip_key, trip_event_list)
                    processed_count += len(trip_event_list)
                except Exception as e:
                    print(f"Error processing trip {trip_key}: {e}")
                    continue
        
        finally:
            db.close()
        
        return processed_count
    
    async def process_trip_events(self, db: SessionLocal, trip_key: str, 
                                events: List[Dict[str, Any]]):
        """Process events for a single trip."""
        if not events:
            return
        
        # Sort events by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        first_event = events[0]
        last_event = events[-1]
        
        # Calculate trip metrics
        trip_metrics = self.calculate_trip_metrics(events)
        
        # Check if trip already exists
        existing_trip = db.query(models.Trip).filter(
            models.Trip.trip_uuid == trip_key
        ).first()
        
        if existing_trip:
            # Update existing trip
            existing_trip.distance_km = trip_metrics['distance_km']
            existing_trip.duration_minutes = trip_metrics['duration_minutes']
            existing_trip.mean_speed_kph = trip_metrics['mean_speed_kph']
            existing_trip.max_speed_kph = trip_metrics['max_speed_kph']
            existing_trip.harsh_brake_events = trip_metrics['harsh_brake_events']
            existing_trip.harsh_accel_events = trip_metrics['harsh_accel_events']
            existing_trip.speeding_events = trip_metrics['speeding_events']
            
            db.commit()
            trip_id = existing_trip.id
        else:
            # Create new trip
            trip_data = {
                "vehicle_id": first_event['vehicle_id'],
                "start_ts": datetime.fromisoformat(first_event['timestamp']),
                "end_ts": datetime.fromisoformat(last_event['timestamp']),
                "distance_km": trip_metrics['distance_km'],
                "duration_minutes": trip_metrics['duration_minutes'],
                "mean_speed_kph": trip_metrics['mean_speed_kph'],
                "max_speed_kph": trip_metrics['max_speed_kph'],
                "night_fraction": trip_metrics['night_fraction'],
                "weekend_fraction": trip_metrics['weekend_fraction'],
                "urban_fraction": trip_metrics['urban_fraction'],
                "harsh_brake_events": trip_metrics['harsh_brake_events'],
                "harsh_accel_events": trip_metrics['harsh_accel_events'],
                "speeding_events": trip_metrics['speeding_events'],
                "phone_distraction_prob": trip_metrics['phone_distraction_prob'],
                "weather_exposure": trip_metrics['weather_exposure']
            }
            
            trip = crud.trip_crud.create(db, trip_data, first_event['user_id'])
            trip_id = trip.id
            
            # Update trip with UUID
            trip.trip_uuid = trip_key
            db.commit()
        
        # Create telematics events
        telematics_events = []
        for event in events:
            event_data = {
                "trip_id": trip_id,
                "ts": datetime.fromisoformat(event['timestamp']),
                "lat": event['lat'],
                "lon": event['lon'],
                "speed_kph": event['speed_kph'],
                "accel_ms2": event['accel_ms2'],
                "brake_intensity": event['brake_intensity'],
                "heading": event.get('heading'),
                "altitude": event.get('altitude'),
                "accuracy": event.get('accuracy')
            }
            telematics_events.append(event_data)
        
        # Bulk create telematics events
        crud.telematics_event_crud.create_bulk(db, telematics_events)
    
    def calculate_trip_metrics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trip metrics from events."""
        if not events:
            return {}
        
        # Basic metrics
        speeds = [event['speed_kph'] for event in events]
        accelerations = [event['accel_ms2'] for event in events]
        brake_intensities = [event['brake_intensity'] for event in events]
        
        # Distance calculation (simplified)
        total_distance = 0
        for i in range(1, len(events)):
            # Haversine distance calculation would go here
            # For now, use a simple approximation
            time_diff_hours = (
                datetime.fromisoformat(events[i]['timestamp']) - 
                datetime.fromisoformat(events[i-1]['timestamp'])
            ).total_seconds() / 3600
            
            avg_speed = (speeds[i] + speeds[i-1]) / 2
            segment_distance = avg_speed * time_diff_hours
            total_distance += segment_distance
        
        # Duration
        start_time = datetime.fromisoformat(events[0]['timestamp'])
        end_time = datetime.fromisoformat(events[-1]['timestamp'])
        duration_minutes = (end_time - start_time).total_seconds() / 60
        
        # Speed metrics
        mean_speed = sum(speeds) / len(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0
        
        # Event counts
        harsh_brake_events = sum(1 for bi in brake_intensities if bi > 0.7)
        harsh_accel_events = sum(1 for accel in accelerations if accel > 3.0)
        speeding_events = sum(1 for speed in speeds if speed > 80)
        
        # Time-based fractions
        night_hours = 0
        weekend_hours = 0
        
        for event in events:
            event_time = datetime.fromisoformat(event['timestamp'])
            
            # Night time (10 PM to 6 AM)
            if event_time.hour >= 22 or event_time.hour < 6:
                night_hours += 1
            
            # Weekend (Saturday = 5, Sunday = 6)
            if event_time.weekday() >= 5:
                weekend_hours += 1
        
        night_fraction = night_hours / len(events) if events else 0
        weekend_fraction = weekend_hours / len(events) if events else 0
        
        # Urban fraction (simplified - based on speed patterns)
        urban_fraction = 0.7 if mean_speed < 50 else 0.3
        
        # Other metrics
        phone_distraction_prob = 0.05  # Simplified
        weather_exposure = 0.1  # Simplified
        
        return {
            'distance_km': total_distance,
            'duration_minutes': duration_minutes,
            'mean_speed_kph': mean_speed,
            'max_speed_kph': max_speed,
            'night_fraction': night_fraction,
            'weekend_fraction': weekend_fraction,
            'urban_fraction': urban_fraction,
            'harsh_brake_events': harsh_brake_events,
            'harsh_accel_events': harsh_accel_events,
            'speeding_events': speeding_events,
            'phone_distraction_prob': phone_distraction_prob,
            'weather_exposure': weather_exposure
        }
    
    async def consume_events(self):
        """Main consumption loop."""
        print(f"Starting consumer: {self.consumer_name}")
        
        while True:
            try:
                # Read events from stream
                messages = self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_name: ">"},
                    count=self.batch_size,
                    block=1000  # 1 second timeout
                )
                
                if not messages:
                    await asyncio.sleep(self.processing_interval)
                    continue
                
                # Process messages
                events = []
                message_ids = []
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        # Convert Redis fields to dict
                        event = {k.decode(): v.decode() for k, v in fields.items()}
                        events.append(event)
                        message_ids.append(msg_id)
                
                if events:
                    # Process events
                    processed_count = await self.process_events_batch(events)
                    
                    # Acknowledge processed messages
                    for msg_id in message_ids:
                        self.redis_client.xack(self.stream_name, self.consumer_group, msg_id)
                    
                    print(f"Processed {processed_count} events")
                
            except Exception as e:
                print(f"Error in consumption loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def start(self):
        """Start the consumer."""
        await self.initialize_consumer_group()
        await self.consume_events()


async def main():
    """Main function for running the consumer."""
    consumer = TelematicsConsumer()
    await consumer.start()


if __name__ == "__main__":
    asyncio.run(main())
