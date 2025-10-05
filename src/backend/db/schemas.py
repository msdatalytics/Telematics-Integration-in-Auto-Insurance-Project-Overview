"""
Pydantic schemas for API request/response models.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class PolicyStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ScoreType(str, Enum):
    DAILY = "daily"
    TRIP = "trip"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class RiskBand(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# User schemas
class UserBase(BaseSchema):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseSchema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserLogin(BaseSchema):
    email: EmailStr
    password: str


class Token(BaseSchema):
    access_token: str
    token_type: str


class TokenData(BaseSchema):
    email: Optional[str] = None


# Vehicle schemas
class VehicleBase(BaseSchema):
    vin: str = Field(..., min_length=17, max_length=17)
    make: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=1900, le=2030)
    color: Optional[str] = None
    license_plate: Optional[str] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseSchema):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    license_plate: Optional[str] = None


class Vehicle(VehicleBase):
    id: int
    user_id: int
    created_at: datetime


# Policy schemas
class PolicyBase(BaseSchema):
    base_premium: float = Field(..., gt=0)
    start_date: datetime
    end_date: datetime
    status: PolicyStatus = PolicyStatus.ACTIVE


class PolicyCreate(PolicyBase):
    vehicle_id: int


class PolicyUpdate(BaseSchema):
    base_premium: Optional[float] = None
    status: Optional[PolicyStatus] = None
    end_date: Optional[datetime] = None


class Policy(PolicyBase):
    id: int
    user_id: int
    vehicle_id: int
    policy_number: str
    created_at: datetime


# Trip schemas
class TripBase(BaseSchema):
    start_ts: datetime
    end_ts: datetime
    distance_km: float = Field(..., ge=0)
    duration_minutes: float = Field(..., gt=0)
    mean_speed_kph: float = Field(..., ge=0)
    max_speed_kph: float = Field(..., ge=0)
    night_fraction: float = Field(..., ge=0, le=1)
    weekend_fraction: float = Field(..., ge=0, le=1)
    urban_fraction: float = Field(..., ge=0, le=1)
    harsh_brake_events: int = Field(..., ge=0)
    harsh_accel_events: int = Field(..., ge=0)
    speeding_events: int = Field(..., ge=0)
    phone_distraction_prob: float = Field(..., ge=0, le=1)
    weather_exposure: float = Field(..., ge=0, le=1)


class TripCreate(TripBase):
    vehicle_id: int


class Trip(TripBase):
    id: int
    user_id: int
    vehicle_id: int
    trip_uuid: str
    created_at: datetime


# Telematics event schemas
class TelematicsEventBase(BaseSchema):
    ts: datetime
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    speed_kph: float = Field(..., ge=0)
    accel_ms2: float
    brake_intensity: float = Field(..., ge=0, le=1)
    heading: Optional[float] = None
    altitude: Optional[float] = None
    accuracy: Optional[float] = None


class TelematicsEventCreate(TelematicsEventBase):
    trip_id: int


class TelematicsEvent(TelematicsEventBase):
    id: int
    trip_id: int
    event_uuid: str
    created_at: datetime


# Context schemas
class ContextBase(BaseSchema):
    ts: datetime
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    weather_code: Optional[int] = None
    temperature_c: Optional[float] = None
    precipitation_mm: Optional[float] = None
    visibility_km: Optional[float] = None
    road_type: Optional[str] = None
    speed_limit_kph: Optional[int] = None
    traffic_density: Optional[float] = None
    crime_index: Optional[float] = None
    accident_density: Optional[float] = None
    school_zone: bool = False
    construction_zone: bool = False


class ContextCreate(ContextBase):
    pass


class Context(ContextBase):
    id: int
    created_at: datetime


# Risk score schemas
class RiskScoreBase(BaseSchema):
    score_type: ScoreType
    score_value: float = Field(..., ge=0, le=100)
    band: RiskBand
    expected_loss: float = Field(..., ge=0)
    claim_probability: float = Field(..., ge=0, le=1)
    claim_severity: float = Field(..., ge=0)
    model_version: str
    feature_values: Optional[Dict[str, Any]] = None
    explanations: Optional[Dict[str, Any]] = None


class RiskScoreCreate(RiskScoreBase):
    user_id: int
    trip_id: Optional[int] = None


class RiskScore(RiskScoreBase):
    id: int
    user_id: int
    trip_id: Optional[int] = None
    computed_at: datetime


# Premium adjustment schemas
class PremiumAdjustmentBase(BaseSchema):
    period_start: datetime
    period_end: datetime
    delta_pct: float = Field(..., ge=-0.5, le=0.5)
    delta_amount: float
    new_premium: float = Field(..., gt=0)
    reason: Optional[str] = None
    score_version: str


class PremiumAdjustmentCreate(PremiumAdjustmentBase):
    policy_id: int
    risk_score_id: Optional[int] = None


class PremiumAdjustment(PremiumAdjustmentBase):
    id: int
    policy_id: int
    risk_score_id: Optional[int] = None
    created_at: datetime


# API request/response schemas
class TelematicsEventBulkCreate(BaseSchema):
    events: List[TelematicsEventCreate]


class TripSimulationRequest(BaseSchema):
    user_id: int
    vehicle_id: int
    num_trips: int = Field(..., ge=1, le=100)
    days_back: int = Field(..., ge=1, le=30)


class PricingQuoteRequest(BaseSchema):
    policy_id: Optional[int] = None
    base_premium: Optional[float] = None
    score: float = Field(..., ge=0, le=100)


class PricingQuoteResponse(BaseSchema):
    policy_id: Optional[int] = None
    band: RiskBand
    delta_pct: float
    delta_amount: float
    new_premium: float
    rationale: str


class UserScoreResponse(BaseSchema):
    user_id: int
    score: float
    band: RiskBand
    expected_loss: float
    explanations: List[str]
    computed_at: datetime


class TripScoreResponse(BaseSchema):
    trip_id: int
    score: float
    band: RiskBand
    expected_loss: float
    explanations: List[str]
    computed_at: datetime


# Dashboard schemas
class DashboardStats(BaseSchema):
    current_premium: float
    premium_delta: float
    premium_delta_pct: float
    current_band: RiskBand
    current_score: float
    score_trend: List[Dict[str, Any]]  # Last 30 days
    total_trips: int
    total_distance_km: float
    avg_score: float


class TripInsights(BaseSchema):
    trip_id: int
    score: float
    band: RiskBand
    distance_km: float
    duration_minutes: float
    harsh_events: int
    speeding_events: int
    night_fraction: float
    weather_exposure: float
    map_data: Optional[Dict[str, Any]] = None


# Admin schemas
class AdminUserList(BaseSchema):
    users: List[User]
    total: int
    page: int
    size: int


class ModelRetrainRequest(BaseSchema):
    force: bool = False
    data_days: int = Field(..., ge=7, le=365)


class ModelMetrics(BaseSchema):
    model_version: str
    classification_auc: float
    regression_rmse: float
    calibration_score: float
    training_date: datetime
    feature_importance: Dict[str, float]


# Error schemas
class ErrorResponse(BaseSchema):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
