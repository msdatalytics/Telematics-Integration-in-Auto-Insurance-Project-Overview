"""
SQLAlchemy database models for telematics UBI system.
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from .base import Base


class User(Base):
    """User model for authentication and profile management."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    role = Column(String(50), default="user", nullable=False)  # user, admin
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    vehicles = relationship("Vehicle", back_populates="user")
    policies = relationship("Policy", back_populates="user")
    trips = relationship("Trip", back_populates="user")
    risk_scores = relationship("RiskScore", back_populates="user")
    
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
    )


class Vehicle(Base):
    """Vehicle model for tracking insured vehicles."""
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vin = Column(String(17), unique=True, index=True, nullable=False)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    color = Column(String(30), nullable=True)
    license_plate = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="vehicles")
    policies = relationship("Policy", back_populates="vehicle")
    trips = relationship("Trip", back_populates="vehicle")
    
    __table_args__ = (
        Index('idx_vehicles_user_id', 'user_id'),
        Index('idx_vehicles_vin', 'vin'),
        CheckConstraint('year >= 1900 AND year <= 2030', name='check_year_range'),
    )


class Policy(Base):
    """Insurance policy model."""
    __tablename__ = "policies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    policy_number = Column(String(50), unique=True, index=True, nullable=False)
    base_premium = Column(Float, nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active, cancelled, expired
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="policies")
    vehicle = relationship("Vehicle", back_populates="policies")
    premium_adjustments = relationship("PremiumAdjustment", back_populates="policy")
    
    __table_args__ = (
        Index('idx_policies_user_id', 'user_id'),
        Index('idx_policies_vehicle_id', 'vehicle_id'),
        Index('idx_policies_status', 'status'),
        CheckConstraint('base_premium > 0', name='check_positive_premium'),
        CheckConstraint('end_date > start_date', name='check_policy_dates'),
    )


class Trip(Base):
    """Trip model for aggregated telematics data."""
    __tablename__ = "trips"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    trip_uuid = Column(String(36), unique=True, index=True, nullable=False)
    start_ts = Column(DateTime(timezone=True), nullable=False)
    end_ts = Column(DateTime(timezone=True), nullable=False)
    distance_km = Column(Float, nullable=False)
    duration_minutes = Column(Float, nullable=False)
    mean_speed_kph = Column(Float, nullable=False)
    max_speed_kph = Column(Float, nullable=False)
    night_fraction = Column(Float, nullable=False)  # Fraction of trip during night hours
    weekend_fraction = Column(Float, nullable=False)  # Fraction of trip during weekends
    urban_fraction = Column(Float, nullable=False)  # Fraction of trip in urban areas
    harsh_brake_events = Column(Integer, default=0, nullable=False)
    harsh_accel_events = Column(Integer, default=0, nullable=False)
    speeding_events = Column(Integer, default=0, nullable=False)
    phone_distraction_prob = Column(Float, default=0.0, nullable=False)
    weather_exposure = Column(Float, default=0.0, nullable=False)  # Rain/snow exposure
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="trips")
    vehicle = relationship("Vehicle", back_populates="trips")
    telematics_events = relationship("TelematicsEvent", back_populates="trip")
    risk_scores = relationship("RiskScore", back_populates="trip")
    
    __table_args__ = (
        Index('idx_trips_user_id', 'user_id'),
        Index('idx_trips_vehicle_id', 'vehicle_id'),
        Index('idx_trips_start_ts', 'start_ts'),
        Index('idx_trips_end_ts', 'end_ts'),
        CheckConstraint('distance_km >= 0', name='check_positive_distance'),
        CheckConstraint('duration_minutes > 0', name='check_positive_duration'),
        CheckConstraint('night_fraction >= 0 AND night_fraction <= 1', name='check_night_fraction'),
    )


class TelematicsEvent(Base):
    """Individual telematics events (GPS + accelerometer data)."""
    __tablename__ = "telematics_events"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    event_uuid = Column(String(36), unique=True, index=True, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    lat = Column(Float, nullable=False)  # Latitude (bucketized for privacy)
    lon = Column(Float, nullable=False)  # Longitude (bucketized for privacy)
    speed_kph = Column(Float, nullable=False)
    accel_ms2 = Column(Float, nullable=False)  # Acceleration in m/s²
    brake_intensity = Column(Float, nullable=False)  # 0-1 scale
    heading = Column(Float, nullable=True)  # Compass heading
    altitude = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)  # GPS accuracy in meters
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    trip = relationship("Trip", back_populates="telematics_events")
    
    __table_args__ = (
        Index('idx_telematics_trip_id', 'trip_id'),
        Index('idx_telematics_ts', 'ts'),
        Index('idx_telematics_location', 'lat', 'lon'),
        CheckConstraint('lat >= -90 AND lat <= 90', name='check_latitude'),
        CheckConstraint('lon >= -180 AND lon <= 180', name='check_longitude'),
        CheckConstraint('speed_kph >= 0', name='check_positive_speed'),
    )


class Context(Base):
    """Contextual data for risk assessment (weather, road conditions, etc.)."""
    __tablename__ = "context"
    
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    weather_code = Column(Integer, nullable=True)  # Weather condition code
    temperature_c = Column(Float, nullable=True)
    precipitation_mm = Column(Float, nullable=True)
    visibility_km = Column(Float, nullable=True)
    road_type = Column(String(50), nullable=True)  # highway, urban, rural
    speed_limit_kph = Column(Integer, nullable=True)
    traffic_density = Column(Float, nullable=True)  # 0-1 scale
    crime_index = Column(Float, nullable=True)  # Area crime index
    accident_density = Column(Float, nullable=True)  # Accidents per km²
    school_zone = Column(Boolean, default=False, nullable=False)
    construction_zone = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_context_ts', 'ts'),
        Index('idx_context_location', 'lat', 'lon'),
        Index('idx_context_weather', 'weather_code'),
    )


class RiskScore(Base):
    """Risk scores computed for users and trips."""
    __tablename__ = "risk_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=True)  # Null for daily scores
    score_type = Column(String(20), nullable=False)  # daily, trip, weekly, monthly
    score_value = Column(Float, nullable=False)  # 0-100 scale
    band = Column(String(1), nullable=False)  # A, B, C, D, E
    expected_loss = Column(Float, nullable=False)  # Expected claim cost
    claim_probability = Column(Float, nullable=False)  # Probability of claim
    claim_severity = Column(Float, nullable=False)  # Expected severity if claim occurs
    model_version = Column(String(50), nullable=False)
    feature_values = Column(JSONB, nullable=True)  # Feature values used for scoring
    explanations = Column(JSONB, nullable=True)  # SHAP explanations
    computed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="risk_scores")
    trip = relationship("Trip", back_populates="risk_scores")
    
    __table_args__ = (
        Index('idx_risk_scores_user_id', 'user_id'),
        Index('idx_risk_scores_trip_id', 'trip_id'),
        Index('idx_risk_scores_computed_at', 'computed_at'),
        Index('idx_risk_scores_score_type', 'score_type'),
        CheckConstraint('score_value >= 0 AND score_value <= 100', name='check_score_range'),
        CheckConstraint('band IN (\'A\', \'B\', \'C\', \'D\', \'E\')', name='check_band_values'),
    )


class PremiumAdjustment(Base):
    """Premium adjustments based on risk scores."""
    __tablename__ = "premium_adjustments"
    
    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    delta_pct = Column(Float, nullable=False)  # Percentage change (-0.2 to +0.5)
    delta_amount = Column(Float, nullable=False)  # Absolute change in premium
    new_premium = Column(Float, nullable=False)  # New premium amount
    reason = Column(Text, nullable=True)  # Explanation for adjustment
    score_version = Column(String(50), nullable=False)
    risk_score_id = Column(Integer, ForeignKey("risk_scores.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    policy = relationship("Policy", back_populates="premium_adjustments")
    risk_score = relationship("RiskScore")
    
    __table_args__ = (
        Index('idx_premium_adjustments_policy_id', 'policy_id'),
        Index('idx_premium_adjustments_period', 'period_start', 'period_end'),
        CheckConstraint('delta_pct >= -0.5 AND delta_pct <= 0.5', name='check_delta_range'),
        CheckConstraint('new_premium > 0', name='check_positive_new_premium'),
    )


# TimescaleDB hypertables (optional - for time-series optimization)
def create_hypertables():
    """Create TimescaleDB hypertables for time-series data."""
    from .base import engine
    
    with engine.connect() as conn:
        # Convert trips table to hypertable
        conn.execute("""
            SELECT create_hypertable('trips', 'start_ts', 
                chunk_time_interval => INTERVAL '1 day',
                if_not_exists => TRUE);
        """)
        
        # Convert telematics_events table to hypertable
        conn.execute("""
            SELECT create_hypertable('telematics_events', 'ts',
                chunk_time_interval => INTERVAL '1 hour',
                if_not_exists => TRUE);
        """)
        
        # Convert context table to hypertable
        conn.execute("""
            SELECT create_hypertable('context', 'ts',
                chunk_time_interval => INTERVAL '1 day',
                if_not_exists => TRUE);
        """)
        
        # Convert risk_scores table to hypertable
        conn.execute("""
            SELECT create_hypertable('risk_scores', 'computed_at',
                chunk_time_interval => INTERVAL '1 day',
                if_not_exists => TRUE);
        """)
        
        conn.commit()
