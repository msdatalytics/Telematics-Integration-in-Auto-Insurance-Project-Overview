"""
Database seeding script for sample data generation.
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from .base import SessionLocal, create_tables
from .models import (
    User, Vehicle, Policy, Trip, TelematicsEvent, Context, 
    RiskScore, PremiumAdjustment
)
from .crud import (
    user_crud, vehicle_crud, policy_crud, trip_crud,
    telematics_event_crud, context_crud, risk_score_crud,
    premium_adjustment_crud
)
from ..core.hashing import get_password_hash


def create_sample_users(db: Session, num_users: int = 50) -> List[User]:
    """Create sample users with realistic data."""
    users = []
    
    # Sample names and emails
    first_names = [
        "John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Jessica",
        "William", "Ashley", "James", "Amanda", "Christopher", "Jennifer", "Daniel",
        "Lisa", "Matthew", "Nancy", "Anthony", "Karen", "Mark", "Betty", "Donald",
        "Helen", "Steven", "Sandra", "Paul", "Donna", "Andrew", "Carol", "Joshua",
        "Ruth", "Kenneth", "Sharon", "Kevin", "Michelle", "Brian", "Laura", "George",
        "Sarah", "Edward", "Kimberly", "Ronald", "Deborah", "Timothy", "Dorothy"
    ]
    
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
        "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"
    ]
    
    for i in range(num_users):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}@example.com"
        
        # Create user
        user_data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": "admin" if i < 5 else "user"  # First 5 users are admins
        }
        
        hashed_password = get_password_hash("password123")
        user = user_crud.create(db, user_data, hashed_password)
        users.append(user)
    
    return users


def create_sample_vehicles(db: Session, users: List[User]) -> List[Vehicle]:
    """Create sample vehicles for users."""
    vehicles = []
    
    # Sample vehicle data
    makes_models = [
        ("Toyota", ["Camry", "Corolla", "RAV4", "Prius", "Highlander"]),
        ("Honda", ["Civic", "Accord", "CR-V", "Pilot", "Fit"]),
        ("Ford", ["F-150", "Escape", "Explorer", "Mustang", "Focus"]),
        ("Chevrolet", ["Silverado", "Equinox", "Malibu", "Cruze", "Tahoe"]),
        ("Nissan", ["Altima", "Sentra", "Rogue", "Pathfinder", "Versa"]),
        ("BMW", ["3 Series", "5 Series", "X3", "X5", "i3"]),
        ("Mercedes", ["C-Class", "E-Class", "GLC", "GLE", "A-Class"]),
        ("Audi", ["A4", "A6", "Q5", "Q7", "A3"]),
        ("Tesla", ["Model 3", "Model S", "Model X", "Model Y"]),
        ("Hyundai", ["Elantra", "Sonata", "Tucson", "Santa Fe", "Accent"])
    ]
    
    colors = ["White", "Black", "Silver", "Gray", "Red", "Blue", "Green", "Brown"]
    
    for user in users:
        # Each user gets 1-3 vehicles
        num_vehicles = random.randint(1, 3)
        
        for _ in range(num_vehicles):
            make, models = random.choice(makes_models)
            model = random.choice(models)
            year = random.randint(2015, 2024)
            color = random.choice(colors)
            
            # Generate realistic VIN (simplified)
            vin = f"{make[:3].upper()}{year}{random.randint(100000, 999999)}"
            
            vehicle_data = {
                "vin": vin,
                "make": make,
                "model": model,
                "year": year,
                "color": color,
                "license_plate": f"{random.randint(100, 999)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(100, 999)}"
            }
            
            vehicle = vehicle_crud.create(db, vehicle_data, user.id)
            vehicles.append(vehicle)
    
    return vehicles


def create_sample_policies(db: Session, users: List[User], vehicles: List[Vehicle]) -> List[Policy]:
    """Create sample insurance policies."""
    policies = []
    
    # Group vehicles by user
    vehicles_by_user = {}
    for vehicle in vehicles:
        if vehicle.user_id not in vehicles_by_user:
            vehicles_by_user[vehicle.user_id] = []
        vehicles_by_user[vehicle.user_id].append(vehicle)
    
    for user in users:
        user_vehicles = vehicles_by_user.get(user.id, [])
        
        for vehicle in user_vehicles:
            # Base premium varies by vehicle type and year
            base_premium = random.uniform(800, 2000)
            
            # Adjust for vehicle age
            age_factor = max(0.5, 1.0 - (2024 - vehicle.year) * 0.05)
            base_premium *= age_factor
            
            # Adjust for luxury brands
            if vehicle.make in ["BMW", "Mercedes", "Audi", "Tesla"]:
                base_premium *= 1.3
            
            start_date = datetime.utcnow() - timedelta(days=random.randint(30, 365))
            end_date = start_date + timedelta(days=365)
            
            policy_data = {
                "vehicle_id": vehicle.id,
                "base_premium": round(base_premium, 2),
                "start_date": start_date,
                "end_date": end_date,
                "status": "active"
            }
            
            policy = policy_crud.create(db, policy_data, user.id)
            policies.append(policy)
    
    return policies


def generate_realistic_trip_data(start_lat: float, start_lon: float, 
                                duration_minutes: float) -> Dict[str, Any]:
    """Generate realistic trip data with GPS traces and events."""
    
    # Trip parameters
    num_points = max(10, int(duration_minutes * 2))  # ~2 points per minute
    distance_km = random.uniform(2, 50)  # 2-50 km trips
    
    # Generate GPS path (simplified - straight line with some noise)
    end_lat = start_lat + random.uniform(-0.01, 0.01)
    end_lon = start_lon + random.uniform(-0.01, 0.01)
    
    lats = np.linspace(start_lat, end_lat, num_points)
    lons = np.linspace(start_lon, end_lon, num_points)
    
    # Add some noise to make it more realistic
    lats += np.random.normal(0, 0.001, num_points)
    lons += np.random.normal(0, 0.001, num_points)
    
    # Generate speeds (start slow, peak in middle, slow at end)
    speeds = []
    for i in range(num_points):
        progress = i / (num_points - 1)
        base_speed = 30 + 40 * (1 - abs(progress - 0.5) * 2)  # Peak at 70 kph
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
            accel = speed_diff / 3.6  # Convert to m/s²
            accel += random.uniform(-1, 1)  # Add noise
        
        accelerations.append(accel)
        
        # Brake intensity (0-1)
        brake_intensity = max(0, min(1, -accel / 5)) if accel < 0 else 0
        brake_intensities.append(brake_intensity)
    
    # Calculate trip metrics
    mean_speed = np.mean(speeds)
    max_speed = np.max(speeds)
    
    # Count harsh events
    harsh_brake_events = sum(1 for bi in brake_intensities if bi > 0.7)
    harsh_accel_events = sum(1 for accel in accelerations if accel > 3.0)
    speeding_events = sum(1 for speed in speeds if speed > 80)  # 80 kph limit
    
    # Time-based fractions
    night_fraction = random.uniform(0, 0.3)  # 0-30% night driving
    weekend_fraction = random.uniform(0, 1) if random.random() < 0.3 else 0  # 30% chance weekend
    urban_fraction = random.uniform(0.3, 0.9)  # 30-90% urban
    
    # Other metrics
    phone_distraction_prob = random.uniform(0, 0.1)  # 0-10% distraction
    weather_exposure = random.uniform(0, 0.2)  # 0-20% bad weather
    
    return {
        "distance_km": distance_km,
        "duration_minutes": duration_minutes,
        "mean_speed_kph": mean_speed,
        "max_speed_kph": max_speed,
        "night_fraction": night_fraction,
        "weekend_fraction": weekend_fraction,
        "urban_fraction": urban_fraction,
        "harsh_brake_events": harsh_brake_events,
        "harsh_accel_events": harsh_accel_events,
        "speeding_events": speeding_events,
        "phone_distraction_prob": phone_distraction_prob,
        "weather_exposure": weather_exposure,
        "gps_path": list(zip(lats, lons, speeds, accelerations, brake_intensities))
    }


def create_sample_trips(db: Session, users: List[User], vehicles: List[Vehicle], 
                       num_trips: int = 500) -> List[Trip]:
    """Create sample trips with telematics data."""
    trips = []
    
    # Group vehicles by user
    vehicles_by_user = {}
    for vehicle in vehicles:
        if vehicle.user_id not in vehicles_by_user:
            vehicles_by_user[vehicle.user_id] = []
        vehicles_by_user[vehicle.user_id].append(vehicle)
    
    # Generate trips
    for _ in range(num_trips):
        user = random.choice(users)
        user_vehicles = vehicles_by_user.get(user.id, [])
        
        if not user_vehicles:
            continue
        
        vehicle = random.choice(user_vehicles)
        
        # Generate trip timing
        days_back = random.randint(1, 90)
        start_time = datetime.utcnow() - timedelta(days=days_back)
        start_time += timedelta(hours=random.randint(6, 22))  # 6 AM to 10 PM
        
        duration_minutes = random.uniform(5, 120)  # 5 minutes to 2 hours
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Starting location (simplified - around a city center)
        start_lat = 40.7128 + random.uniform(-0.1, 0.1)  # NYC area
        start_lon = -74.0060 + random.uniform(-0.1, 0.1)
        
        # Generate trip data
        trip_data = generate_realistic_trip_data(start_lat, start_lon, duration_minutes)
        
        # Create trip
        trip_create_data = {
            "vehicle_id": vehicle.id,
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
        
        trip = trip_crud.create(db, trip_create_data, user.id)
        trips.append(trip)
        
        # Create telematics events for this trip
        create_telematics_events_for_trip(db, trip, trip_data["gps_path"])
    
    return trips


def create_telematics_events_for_trip(db: Session, trip: Trip, gps_path: List[tuple]):
    """Create telematics events for a trip."""
    events = []
    
    for i, (lat, lon, speed, accel, brake_intensity) in enumerate(gps_path):
        # Calculate timestamp
        progress = i / (len(gps_path) - 1)
        event_time = trip.start_ts + timedelta(
            minutes=progress * trip.duration_minutes
        )
        
        event_data = {
            "trip_id": trip.id,
            "ts": event_time,
            "lat": round(lat, 5),  # Privacy: bucketize to 5 decimal places
            "lon": round(lon, 5),
            "speed_kph": speed,
            "accel_ms2": accel,
            "brake_intensity": brake_intensity,
            "heading": random.uniform(0, 360),
            "altitude": random.uniform(0, 100),
            "accuracy": random.uniform(3, 10)
        }
        
        events.append(event_data)
    
    # Create events in batches
    telematics_event_crud.create_bulk(db, events)


def create_sample_context_data(db: Session) -> List[Context]:
    """Create sample contextual data (weather, road conditions, etc.)."""
    contexts = []
    
    # Generate context data for various locations and times
    base_lat, base_lon = 40.7128, -74.0060  # NYC area
    
    for day in range(90):  # Last 90 days
        date = datetime.utcnow() - timedelta(days=day)
        
        # Generate multiple context points per day
        for _ in range(random.randint(5, 15)):
            lat = base_lat + random.uniform(-0.1, 0.1)
            lon = base_lon + random.uniform(-0.1, 0.1)
            ts = date + timedelta(hours=random.randint(0, 23))
            
            context_data = {
                "ts": ts,
                "lat": lat,
                "lon": lon,
                "weather_code": random.choice([0, 1, 2, 3, 45, 48, 51, 53, 55, 61, 63, 65, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99]),
                "temperature_c": random.uniform(-10, 35),
                "precipitation_mm": random.uniform(0, 20),
                "visibility_km": random.uniform(1, 20),
                "road_type": random.choice(["highway", "urban", "rural"]),
                "speed_limit_kph": random.choice([30, 50, 70, 90, 110]),
                "traffic_density": random.uniform(0, 1),
                "crime_index": random.uniform(0, 100),
                "accident_density": random.uniform(0, 10),
                "school_zone": random.random() < 0.1,
                "construction_zone": random.random() < 0.05
            }
            
            context = context_crud.create(db, context_data)
            contexts.append(context)
    
    return contexts


def create_sample_risk_scores(db: Session, users: List[User], trips: List[Trip]):
    """Create sample risk scores for users and trips."""
    
    # Generate daily scores for users
    for user in users:
        for day in range(30):  # Last 30 days
            date = datetime.utcnow() - timedelta(days=day)
            
            # Generate realistic risk score
            base_score = random.uniform(40, 90)
            
            # Adjust based on user's driving behavior
            user_trips = [t for t in trips if t.user_id == user.id]
            if user_trips:
                avg_harsh_events = np.mean([t.harsh_brake_events + t.harsh_accel_events for t in user_trips])
                avg_speeding = np.mean([t.speeding_events for t in user_trips])
                avg_night = np.mean([t.night_fraction for t in user_trips])
                
                # Adjust score based on behavior
                if avg_harsh_events > 5:
                    base_score -= 10
                if avg_speeding > 3:
                    base_score -= 5
                if avg_night > 0.3:
                    base_score -= 5
            
            # Ensure score is in valid range
            score_value = max(0, min(100, base_score))
            
            # Determine band
            if score_value >= 85:
                band = "A"
            elif score_value >= 70:
                band = "B"
            elif score_value >= 55:
                band = "C"
            elif score_value >= 40:
                band = "D"
            else:
                band = "E"
            
            # Calculate expected loss (simplified)
            claim_prob = max(0.01, (100 - score_value) / 100 * 0.1)  # 0.01-0.1 probability
            claim_severity = random.uniform(2000, 15000)  # $2k-$15k severity
            expected_loss = claim_prob * claim_severity
            
            risk_score_data = {
                "user_id": user.id,
                "trip_id": None,
                "score_type": "daily",
                "score_value": score_value,
                "band": band,
                "expected_loss": expected_loss,
                "claim_probability": claim_prob,
                "claim_severity": claim_severity,
                "model_version": "v1.0.0",
                "feature_values": {
                    "harsh_events": avg_harsh_events if user_trips else 0,
                    "speeding_events": avg_speeding if user_trips else 0,
                    "night_fraction": avg_night if user_trips else 0
                },
                "explanations": [
                    f"Score {score_value:.1f} (Band {band})",
                    f"Expected loss: ${expected_loss:.0f}"
                ]
            }
            
            risk_score_crud.create(db, risk_score_data)


def seed_database():
    """Main seeding function."""
    print("Creating database tables...")
    create_tables()
    
    print("Seeding sample data...")
    db = SessionLocal()
    
    try:
        # Create users
        print("Creating users...")
        users = create_sample_users(db, 50)
        
        # Create vehicles
        print("Creating vehicles...")
        vehicles = create_sample_vehicles(db, users)
        
        # Create policies
        print("Creating policies...")
        policies = create_sample_policies(db, users, vehicles)
        
        # Create trips
        print("Creating trips...")
        trips = create_sample_trips(db, users, vehicles, 500)
        
        # Create context data
        print("Creating context data...")
        contexts = create_sample_context_data(db)
        
        # Create risk scores
        print("Creating risk scores...")
        create_sample_risk_scores(db, users, trips)
        
        print(f"Seeding completed successfully!")
        print(f"- Users: {len(users)}")
        print(f"- Vehicles: {len(vehicles)}")
        print(f"- Policies: {len(policies)}")
        print(f"- Trips: {len(trips)}")
        print(f"- Context records: {len(contexts)}")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
