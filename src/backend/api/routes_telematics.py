"""
Telematics data API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime, timedelta
import random

from ..core.dependencies import (
    get_current_user_dependency, get_current_admin_dependency,
    get_database_dependency, validate_vehicle_access
)
from ..db import crud, schemas
from ..db.schemas import (
    TelematicsEventBulkCreate, TripSimulationRequest, Trip, TelematicsEvent
)

router = APIRouter()


@router.post("/events", response_model=List[schemas.TelematicsEvent])
async def create_telematics_events(
    events_data: TelematicsEventBulkCreate,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Bulk create telematics events."""
    # Validate that all events belong to trips owned by the user
    trip_ids = list(set(event.trip_id for event in events_data.events))
    
    for trip_id in trip_ids:
        trip = crud.trip_crud.get_by_id(db, trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found"
            )
        
        if trip.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to add events to trip {trip_id}"
            )
    
    # Create events
    events = crud.telematics_event_crud.create_bulk(db, events_data.events)
    return events


@router.post("/trips/simulate", response_model=List[schemas.Trip])
async def simulate_trips(
    simulation_request: TripSimulationRequest,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Simulate trips for a user/vehicle."""
    # Validate vehicle access
    vehicle = crud.vehicle_crud.get_by_id(db, simulation_request.vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    if vehicle.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to simulate trips for this vehicle"
        )
    
    # Generate simulated trips
    trips = []
    
    for _ in range(simulation_request.num_trips):
        # Generate trip timing
        days_back = random.randint(1, simulation_request.days_back)
        start_time = datetime.utcnow() - timedelta(days=days_back)
        start_time += timedelta(hours=random.randint(6, 22))
        
        duration_minutes = random.uniform(5, 120)
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Generate realistic trip data
        trip_data = generate_realistic_trip_data()
        
        # Create trip
        trip_create_data = {
            "vehicle_id": simulation_request.vehicle_id,
            "start_ts": start_time,
            "end_ts": end_time,
            "distance_km": trip_data["distance_km"],
            "duration_minutes": trip_data["duration_minutes"],
            "mean_speed_kph": trip_data["mean_speed_kph"],
            "max_speed_kph": trip_data["max_speed_kph"],
            "night_fraction": trip_data["night_fraction"],
            "weekend_fraction": trip_data["weekend_fraction"],
            "urban_fraction": trip_data["urban_fraction"],
            "harsh_brake_events": trip_data["harsh_brake_events"],
            "harsh_accel_events": trip_data["harsh_accel_events"],
            "speeding_events": trip_data["speeding_events"],
            "phone_distraction_prob": trip_data["phone_distraction_prob"],
            "weather_exposure": trip_data["weather_exposure"]
        }
        
        trip = crud.trip_crud.create(db, trip_create_data, simulation_request.user_id)
        trips.append(trip)
        
        # Generate telematics events for this trip
        generate_telematics_events_for_trip(db, trip, trip_data)
    
    return trips


@router.get("/trips/{trip_id}", response_model=schemas.Trip)
async def get_trip(
    trip_id: int,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get trip details."""
    trip = crud.trip_crud.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    if trip.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this trip"
        )
    
    return trip


@router.get("/trips/{trip_id}/events", response_model=List[schemas.TelematicsEvent])
async def get_trip_events(
    trip_id: int,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get telematics events for a trip."""
    trip = crud.trip_crud.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    if trip.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this trip"
        )
    
    events = crud.telematics_event_crud.get_by_trip(db, trip_id)
    return events


@router.get("/trips/{trip_id}/path")
async def get_trip_path(
    trip_id: int,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get GPS path for a trip."""
    trip = crud.trip_crud.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    if trip.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this trip"
        )
    
    path = crud.telematics_event_crud.get_trip_path(db, trip_id)
    return {"trip_id": trip_id, "path": path}


@router.get("/vehicles/{vehicle_id}/trips", response_model=List[schemas.Trip])
async def get_vehicle_trips(
    vehicle_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get trips for a specific vehicle."""
    vehicle = crud.vehicle_crud.get_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    if vehicle.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this vehicle"
        )
    
    trips = crud.trip_crud.get_by_vehicle(db, vehicle_id, skip, limit)
    return trips


# Helper functions for trip simulation
def generate_realistic_trip_data() -> dict:
    """Generate realistic trip data."""
    import numpy as np
    
    distance_km = random.uniform(2, 50)
    duration_minutes = random.uniform(5, 120)
    mean_speed_kph = distance_km / (duration_minutes / 60)
    max_speed_kph = mean_speed_kph * random.uniform(1.2, 2.0)
    
    # Driving behavior metrics
    night_fraction = random.uniform(0, 0.3)
    weekend_fraction = random.uniform(0, 1) if random.random() < 0.3 else 0
    urban_fraction = random.uniform(0.3, 0.9)
    
    # Event counts (correlated with distance and duration)
    harsh_brake_events = int(random.uniform(0, distance_km * 0.5))
    harsh_accel_events = int(random.uniform(0, distance_km * 0.3))
    speeding_events = int(random.uniform(0, duration_minutes * 0.1))
    
    # Other metrics
    phone_distraction_prob = random.uniform(0, 0.1)
    weather_exposure = random.uniform(0, 0.2)
    
    return {
        "distance_km": distance_km,
        "duration_minutes": duration_minutes,
        "mean_speed_kph": mean_speed_kph,
        "max_speed_kph": max_speed_kph,
        "night_fraction": night_fraction,
        "weekend_fraction": weekend_fraction,
        "urban_fraction": urban_fraction,
        "harsh_brake_events": harsh_brake_events,
        "harsh_accel_events": harsh_accel_events,
        "speeding_events": speeding_events,
        "phone_distraction_prob": phone_distraction_prob,
        "weather_exposure": weather_exposure
    }


def generate_telematics_events_for_trip(db: Session, trip: schemas.Trip, trip_data: dict):
    """Generate telematics events for a trip."""
    import numpy as np
    
    # Generate GPS path
    num_points = max(10, int(trip_data["duration_minutes"] * 2))
    
    # Simple straight-line path with noise
    start_lat = 40.7128 + random.uniform(-0.01, 0.01)
    start_lon = -74.0060 + random.uniform(-0.01, 0.01)
    end_lat = start_lat + random.uniform(-0.01, 0.01)
    end_lon = start_lon + random.uniform(-0.01, 0.01)
    
    lats = np.linspace(start_lat, end_lat, num_points)
    lons = np.linspace(start_lon, end_lon, num_points)
    
    # Add noise
    lats += np.random.normal(0, 0.001, num_points)
    lons += np.random.normal(0, 0.001, num_points)
    
    # Generate speeds
    speeds = []
    for i in range(num_points):
        progress = i / (num_points - 1)
        base_speed = 30 + 40 * (1 - abs(progress - 0.5) * 2)
        speed = max(0, base_speed + random.uniform(-10, 10))
        speeds.append(speed)
    
    # Generate accelerations
    accelerations = []
    brake_intensities = []
    
    for i in range(num_points):
        if i == 0:
            accel = random.uniform(-2, 2)
        else:
            speed_diff = speeds[i] - speeds[i-1]
            accel = speed_diff / 3.6
            accel += random.uniform(-1, 1)
        
        accelerations.append(accel)
        brake_intensity = max(0, min(1, -accel / 5)) if accel < 0 else 0
        brake_intensities.append(brake_intensity)
    
    # Create events
    events = []
    for i in range(num_points):
        progress = i / (num_points - 1)
        event_time = trip.start_ts + timedelta(
            minutes=progress * trip_data["duration_minutes"]
        )
        
        event_data = {
            "trip_id": trip.id,
            "ts": event_time,
            "lat": round(lats[i], 5),
            "lon": round(lons[i], 5),
            "speed_kph": speeds[i],
            "accel_ms2": accelerations[i],
            "brake_intensity": brake_intensities[i],
            "heading": random.uniform(0, 360),
            "altitude": random.uniform(0, 100),
            "accuracy": random.uniform(3, 10)
        }
        
        events.append(event_data)
    
    # Create events in database
    crud.telematics_event_crud.create_bulk(db, events)
