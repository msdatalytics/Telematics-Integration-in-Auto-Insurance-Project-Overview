"""
CRUD operations for database models.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from .models import (
    User, Vehicle, Policy, Trip, TelematicsEvent, Context, 
    RiskScore, PremiumAdjustment
)
from .schemas import (
    UserCreate, UserUpdate, VehicleCreate, VehicleUpdate,
    PolicyCreate, PolicyUpdate, TripCreate, TelematicsEventCreate,
    ContextCreate, RiskScoreCreate, PremiumAdjustmentCreate
)


# User CRUD
class UserCRUD:
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create(db: Session, user: UserCreate, hashed_password: str) -> User:
        db_user = User(
            email=user.email,
            hashed_password=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def update(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return None
        
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()


# Vehicle CRUD
class VehicleCRUD:
    @staticmethod
    def get_by_id(db: Session, vehicle_id: int) -> Optional[Vehicle]:
        return db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    
    @staticmethod
    def get_by_vin(db: Session, vin: str) -> Optional[Vehicle]:
        return db.query(Vehicle).filter(Vehicle.vin == vin).first()
    
    @staticmethod
    def get_by_user(db: Session, user_id: int) -> List[Vehicle]:
        return db.query(Vehicle).filter(Vehicle.user_id == user_id).all()
    
    @staticmethod
    def create(db: Session, vehicle: VehicleCreate, user_id: int) -> Vehicle:
        db_vehicle = Vehicle(
            user_id=user_id,
            vin=vehicle.vin,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year,
            color=vehicle.color,
            license_plate=vehicle.license_plate
        )
        db.add(db_vehicle)
        db.commit()
        db.refresh(db_vehicle)
        return db_vehicle
    
    @staticmethod
    def update(db: Session, vehicle_id: int, vehicle_update: VehicleUpdate) -> Optional[Vehicle]:
        db_vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not db_vehicle:
            return None
        
        update_data = vehicle_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_vehicle, field, value)
        
        db.commit()
        db.refresh(db_vehicle)
        return db_vehicle


# Policy CRUD
class PolicyCRUD:
    @staticmethod
    def get_by_id(db: Session, policy_id: int) -> Optional[Policy]:
        return db.query(Policy).filter(Policy.id == policy_id).first()
    
    @staticmethod
    def get_by_user(db: Session, user_id: int) -> List[Policy]:
        return db.query(Policy).filter(Policy.user_id == user_id).all()
    
    @staticmethod
    def get_active_by_user(db: Session, user_id: int) -> List[Policy]:
        return db.query(Policy).filter(
            and_(Policy.user_id == user_id, Policy.status == "active")
        ).all()
    
    @staticmethod
    def create(db: Session, policy: PolicyCreate, user_id: int) -> Policy:
        policy_number = f"POL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        db_policy = Policy(
            user_id=user_id,
            vehicle_id=policy.vehicle_id,
            policy_number=policy_number,
            base_premium=policy.base_premium,
            status=policy.status,
            start_date=policy.start_date,
            end_date=policy.end_date
        )
        db.add(db_policy)
        db.commit()
        db.refresh(db_policy)
        return db_policy
    
    @staticmethod
    def update(db: Session, policy_id: int, policy_update: PolicyUpdate) -> Optional[Policy]:
        db_policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if not db_policy:
            return None
        
        update_data = policy_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_policy, field, value)
        
        db.commit()
        db.refresh(db_policy)
        return db_policy


# Trip CRUD
class TripCRUD:
    @staticmethod
    def get_by_id(db: Session, trip_id: int) -> Optional[Trip]:
        return db.query(Trip).filter(Trip.id == trip_id).first()
    
    @staticmethod
    def get_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Trip]:
        return db.query(Trip).filter(Trip.user_id == user_id)\
            .order_by(desc(Trip.start_ts)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_vehicle(db: Session, vehicle_id: int, skip: int = 0, limit: int = 100) -> List[Trip]:
        return db.query(Trip).filter(Trip.vehicle_id == vehicle_id)\
            .order_by(desc(Trip.start_ts)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_recent_by_user(db: Session, user_id: int, days: int = 30) -> List[Trip]:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return db.query(Trip).filter(
            and_(Trip.user_id == user_id, Trip.start_ts >= cutoff_date)
        ).order_by(desc(Trip.start_ts)).all()
    
    @staticmethod
    def create(db: Session, trip: TripCreate, user_id: int) -> Trip:
        trip_uuid = str(uuid.uuid4())
        
        db_trip = Trip(
            user_id=user_id,
            vehicle_id=trip.vehicle_id,
            trip_uuid=trip_uuid,
            start_ts=trip.start_ts,
            end_ts=trip.end_ts,
            distance_km=trip.distance_km,
            duration_minutes=trip.duration_minutes,
            mean_speed_kph=trip.mean_speed_kph,
            max_speed_kph=trip.max_speed_kph,
            night_fraction=trip.night_fraction,
            weekend_fraction=trip.weekend_fraction,
            urban_fraction=trip.urban_fraction,
            harsh_brake_events=trip.harsh_brake_events,
            harsh_accel_events=trip.harsh_accel_events,
            speeding_events=trip.speeding_events,
            phone_distraction_prob=trip.phone_distraction_prob,
            weather_exposure=trip.weather_exposure
        )
        db.add(db_trip)
        db.commit()
        db.refresh(db_trip)
        return db_trip
    
    @staticmethod
    def get_user_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """Get aggregated statistics for a user."""
        stats = db.query(
            func.count(Trip.id).label('total_trips'),
            func.sum(Trip.distance_km).label('total_distance'),
            func.avg(Trip.mean_speed_kph).label('avg_speed'),
            func.sum(Trip.harsh_brake_events).label('total_harsh_brakes'),
            func.sum(Trip.harsh_accel_events).label('total_harsh_accels'),
            func.sum(Trip.speeding_events).label('total_speeding'),
            func.avg(Trip.night_fraction).label('avg_night_fraction')
        ).filter(Trip.user_id == user_id).first()
        
        return {
            'total_trips': stats.total_trips or 0,
            'total_distance_km': stats.total_distance or 0.0,
            'avg_speed_kph': stats.avg_speed or 0.0,
            'total_harsh_brakes': stats.total_harsh_brakes or 0,
            'total_harsh_accels': stats.total_harsh_accels or 0,
            'total_speeding': stats.total_speeding or 0,
            'avg_night_fraction': stats.avg_night_fraction or 0.0
        }


# Telematics Event CRUD
class TelematicsEventCRUD:
    @staticmethod
    def get_by_trip(db: Session, trip_id: int) -> List[TelematicsEvent]:
        return db.query(TelematicsEvent).filter(TelematicsEvent.trip_id == trip_id)\
            .order_by(TelematicsEvent.ts).all()
    
    @staticmethod
    def create_bulk(db: Session, events: List[TelematicsEventCreate]) -> List[TelematicsEvent]:
        db_events = []
        for event in events:
            event_uuid = str(uuid.uuid4())
            db_event = TelematicsEvent(
                trip_id=event.trip_id,
                event_uuid=event_uuid,
                ts=event.ts,
                lat=event.lat,
                lon=event.lon,
                speed_kph=event.speed_kph,
                accel_ms2=event.accel_ms2,
                brake_intensity=event.brake_intensity,
                heading=event.heading,
                altitude=event.altitude,
                accuracy=event.accuracy
            )
            db_events.append(db_event)
        
        db.add_all(db_events)
        db.commit()
        return db_events
    
    @staticmethod
    def get_trip_path(db: Session, trip_id: int) -> List[Dict[str, float]]:
        """Get GPS path for a trip."""
        events = db.query(TelematicsEvent.lat, TelematicsEvent.lon, TelematicsEvent.ts)\
            .filter(TelematicsEvent.trip_id == trip_id)\
            .order_by(TelematicsEvent.ts).all()
        
        return [
            {'lat': event.lat, 'lon': event.lon, 'ts': event.ts}
            for event in events
        ]


# Context CRUD
class ContextCRUD:
    @staticmethod
    def get_by_location_and_time(db: Session, lat: float, lon: float, 
                                ts: datetime, radius_km: float = 5.0) -> Optional[Context]:
        """Get context data for a location and time."""
        # Simple implementation - in production, use PostGIS for spatial queries
        return db.query(Context).filter(
            and_(
                Context.lat.between(lat - 0.05, lat + 0.05),  # Rough approximation
                Context.lon.between(lon - 0.05, lon + 0.05),
                Context.ts.between(ts - timedelta(hours=1), ts + timedelta(hours=1))
            )
        ).first()
    
    @staticmethod
    def create(db: Session, context: ContextCreate) -> Context:
        db_context = Context(**context.dict())
        db.add(db_context)
        db.commit()
        db.refresh(db_context)
        return db_context


# Risk Score CRUD
class RiskScoreCRUD:
    @staticmethod
    def get_latest_by_user(db: Session, user_id: int, score_type: str = "daily") -> Optional[RiskScore]:
        return db.query(RiskScore).filter(
            and_(RiskScore.user_id == user_id, RiskScore.score_type == score_type)
        ).order_by(desc(RiskScore.computed_at)).first()
    
    @staticmethod
    def get_by_trip(db: Session, trip_id: int) -> Optional[RiskScore]:
        return db.query(RiskScore).filter(RiskScore.trip_id == trip_id).first()
    
    @staticmethod
    def get_user_score_history(db: Session, user_id: int, days: int = 30) -> List[RiskScore]:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return db.query(RiskScore).filter(
            and_(RiskScore.user_id == user_id, RiskScore.computed_at >= cutoff_date)
        ).order_by(desc(RiskScore.computed_at)).all()
    
    @staticmethod
    def create(db: Session, risk_score: RiskScoreCreate) -> RiskScore:
        db_risk_score = RiskScore(**risk_score.dict())
        db.add(db_risk_score)
        db.commit()
        db.refresh(db_risk_score)
        return db_risk_score
    
    @staticmethod
    def get_score_trend(db: Session, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get score trend data for dashboard."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        scores = db.query(
            RiskScore.computed_at,
            RiskScore.score_value,
            RiskScore.band
        ).filter(
            and_(RiskScore.user_id == user_id, RiskScore.computed_at >= cutoff_date)
        ).order_by(RiskScore.computed_at).all()
        
        return [
            {
                'date': score.computed_at.isoformat(),
                'score': score.score_value,
                'band': score.band
            }
            for score in scores
        ]


# Premium Adjustment CRUD
class PremiumAdjustmentCRUD:
    @staticmethod
    def get_by_policy(db: Session, policy_id: int) -> List[PremiumAdjustment]:
        return db.query(PremiumAdjustment).filter(
            PremiumAdjustment.policy_id == policy_id
        ).order_by(desc(PremiumAdjustment.created_at)).all()
    
    @staticmethod
    def get_latest_by_policy(db: Session, policy_id: int) -> Optional[PremiumAdjustment]:
        return db.query(PremiumAdjustment).filter(
            PremiumAdjustment.policy_id == policy_id
        ).order_by(desc(PremiumAdjustment.created_at)).first()
    
    @staticmethod
    def create(db: Session, adjustment: PremiumAdjustmentCreate) -> PremiumAdjustment:
        db_adjustment = PremiumAdjustment(**adjustment.dict())
        db.add(db_adjustment)
        db.commit()
        db.refresh(db_adjustment)
        return db_adjustment


# Initialize CRUD instances
user_crud = UserCRUD()
vehicle_crud = VehicleCRUD()
policy_crud = PolicyCRUD()
trip_crud = TripCRUD()
telematics_event_crud = TelematicsEventCRUD()
context_crud = ContextCRUD()
risk_score_crud = RiskScoreCRUD()
premium_adjustment_crud = PremiumAdjustmentCRUD()
