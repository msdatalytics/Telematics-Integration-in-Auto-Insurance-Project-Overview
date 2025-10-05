"""
Stream processing pipeline for telematics data.
"""
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from .producer import TelematicsProducer
from .consumer import TelematicsConsumer
from ..settings import settings


class TelematicsPipeline:
    """Complete telematics data processing pipeline."""
    
    def __init__(self):
        self.producer = TelematicsProducer()
        self.consumer = TelematicsConsumer()
        self.logger = logging.getLogger(__name__)
    
    async def start_pipeline(self):
        """Start the complete pipeline."""
        self.logger.info("Starting telematics pipeline...")
        
        # Start consumer in background
        consumer_task = asyncio.create_task(self.consumer.start())
        
        # Start producer
        producer_task = asyncio.create_task(self.run_producer())
        
        # Wait for both tasks
        await asyncio.gather(consumer_task, producer_task)
    
    async def run_producer(self):
        """Run the producer with continuous data generation."""
        self.logger.info("Starting producer...")
        
        while True:
            try:
                # Generate events for multiple users
                for user_id in range(1, 11):  # 10 users
                    vehicle_id = user_id
                    
                    # Generate a few trips per user
                    events = await self.producer.generate_realistic_events(
                        user_id, vehicle_id, num_events=random.randint(20, 50)
                    )
                    
                    # Produce events
                    produced = await self.producer.produce_events(events)
                    self.logger.info(f"Produced {produced} events for user {user_id}")
                
                # Wait before next batch
                await asyncio.sleep(30)  # Generate every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in producer: {e}")
                await asyncio.sleep(5)
    
    async def process_historical_data(self, days_back: int = 30):
        """Process historical telematics data."""
        self.logger.info(f"Processing historical data for {days_back} days...")
        
        # This would typically read from a data lake or historical storage
        # For now, we'll generate synthetic historical data
        
        total_events = 0
        
        for day in range(days_back):
            date = datetime.utcnow() - timedelta(days=day)
            
            # Generate events for each day
            for user_id in range(1, 51):  # 50 users
                vehicle_id = user_id
                
                # Generate 1-3 trips per user per day
                num_trips = random.randint(1, 3)
                
                for trip in range(num_trips):
                    events = await self.producer.generate_realistic_events(
                        user_id, vehicle_id, num_events=random.randint(10, 30)
                    )
                    
                    # Update timestamps to be historical
                    for event in events:
                        event['timestamp'] = (
                            date + timedelta(hours=random.randint(6, 22))
                        ).isoformat()
                    
                    produced = await self.producer.produce_events(events)
                    total_events += produced
            
            self.logger.info(f"Processed day {day + 1}/{days_back}")
        
        self.logger.info(f"Historical processing complete: {total_events} events")
    
    async def get_stream_stats(self) -> Dict[str, Any]:
        """Get statistics about the stream."""
        try:
            # Get stream info
            stream_info = self.producer.redis_client.xinfo_stream(self.producer.stream_name)
            
            # Get consumer group info
            group_info = self.producer.redis_client.xinfo_groups(self.producer.stream_name)
            
            return {
                "stream_length": stream_info.get("length", 0),
                "first_entry_id": stream_info.get("first-entry", {}).get("id"),
                "last_entry_id": stream_info.get("last-entry", {}).get("id"),
                "consumer_groups": len(group_info),
                "consumer_group_info": group_info
            }
        
        except Exception as e:
            self.logger.error(f"Error getting stream stats: {e}")
            return {}
    
    async def cleanup_old_events(self, max_age_hours: int = 24):
        """Clean up old events from the stream."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            cutoff_timestamp = int(cutoff_time.timestamp() * 1000)
            
            # Trim stream to remove old events
            trimmed = self.producer.redis_client.xtrim(
                self.producer.stream_name, 
                maxlen=1000,  # Keep last 1000 events
                approximate=True
            )
            
            self.logger.info(f"Trimmed {trimmed} old events from stream")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old events: {e}")
    
    async def monitor_pipeline_health(self):
        """Monitor pipeline health and performance."""
        while True:
            try:
                stats = await self.get_stream_stats()
                
                self.logger.info(f"Pipeline stats: {stats}")
                
                # Check for issues
                if stats.get("stream_length", 0) > 10000:
                    self.logger.warning("Stream length is high, consider cleanup")
                
                # Cleanup if needed
                await self.cleanup_old_events()
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)


async def main():
    """Main function for running the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Telematics Pipeline")
    parser.add_argument("--mode", choices=["producer", "consumer", "pipeline", "historical"], 
                       default="pipeline", help="Pipeline mode")
    parser.add_argument("--days", type=int, default=30, help="Days of historical data")
    
    args = parser.parse_args()
    
    pipeline = TelematicsPipeline()
    
    if args.mode == "producer":
        await pipeline.run_producer()
    elif args.mode == "consumer":
        await pipeline.consumer.start()
    elif args.mode == "historical":
        await pipeline.process_historical_data(args.days)
    else:  # pipeline
        await pipeline.start_pipeline()


if __name__ == "__main__":
    import random
    asyncio.run(main())
