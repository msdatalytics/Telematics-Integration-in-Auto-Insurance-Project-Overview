# API Contract Documentation

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.telematics-ubi.com`

## Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "data": <response_data>,
  "message": "Success message (optional)",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Error Response
```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error

## Endpoints

### Authentication

#### POST /api/v1/users/register

Register a new user.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### POST /api/v1/users/login

Login user and get access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### User Management

#### GET /api/v1/users/me

Get current user profile.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### GET /api/v1/users/me/vehicles

Get current user's vehicles.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "vin": "1HGBH41JXMN109186",
    "make": "Honda",
    "model": "Civic",
    "year": 2020,
    "color": "Silver",
    "license_plate": "ABC123",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### GET /api/v1/users/me/policies

Get current user's policies.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "vehicle_id": 1,
    "policy_number": "POL-20240101-ABC12345",
    "base_premium": 1200.00,
    "status": "active",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### GET /api/v1/users/me/dashboard

Get dashboard statistics for current user.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "current_premium": 1080.00,
  "premium_delta": -120.00,
  "premium_delta_pct": -0.10,
  "current_band": "B",
  "current_score": 78.5,
  "score_trend": [
    {
      "date": "2024-01-01T00:00:00Z",
      "score": 75.2,
      "band": "C"
    },
    {
      "date": "2024-01-02T00:00:00Z",
      "score": 78.5,
      "band": "B"
    }
  ],
  "total_trips": 45,
  "total_distance_km": 1250.5,
  "avg_score": 76.8
}
```

### Telematics Data

#### POST /api/v1/telematics/events

Bulk create telematics events.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "events": [
    {
      "trip_id": 1,
      "ts": "2024-01-01T10:00:00Z",
      "lat": 40.7128,
      "lon": -74.0060,
      "speed_kph": 45.5,
      "accel_ms2": 1.2,
      "brake_intensity": 0.0,
      "heading": 180.0,
      "altitude": 10.5,
      "accuracy": 5.0
    }
  ]
}
```

**Response:**
```json
[
  {
    "id": 1,
    "trip_id": 1,
    "event_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "ts": "2024-01-01T10:00:00Z",
    "lat": 40.7128,
    "lon": -74.0060,
    "speed_kph": 45.5,
    "accel_ms2": 1.2,
    "brake_intensity": 0.0,
    "heading": 180.0,
    "altitude": 10.5,
    "accuracy": 5.0,
    "created_at": "2024-01-01T10:00:00Z"
  }
]
```

#### POST /api/v1/telematics/trips/simulate

Simulate trips for a user/vehicle.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "user_id": 1,
  "vehicle_id": 1,
  "num_trips": 10,
  "days_back": 7
}
```

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "vehicle_id": 1,
    "trip_uuid": "trip-550e8400-e29b-41d4-a716-446655440000",
    "start_ts": "2024-01-01T08:00:00Z",
    "end_ts": "2024-01-01T08:30:00Z",
    "distance_km": 15.5,
    "duration_minutes": 30.0,
    "mean_speed_kph": 31.0,
    "max_speed_kph": 45.0,
    "night_fraction": 0.0,
    "weekend_fraction": 0.0,
    "urban_fraction": 0.8,
    "harsh_brake_events": 2,
    "harsh_accel_events": 1,
    "speeding_events": 3,
    "phone_distraction_prob": 0.05,
    "weather_exposure": 0.1,
    "created_at": "2024-01-01T08:00:00Z"
  }
]
```

#### GET /api/v1/telematics/trips/{trip_id}

Get trip details.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "vehicle_id": 1,
  "trip_uuid": "trip-550e8400-e29b-41d4-a716-446655440000",
  "start_ts": "2024-01-01T08:00:00Z",
  "end_ts": "2024-01-01T08:30:00Z",
  "distance_km": 15.5,
  "duration_minutes": 30.0,
  "mean_speed_kph": 31.0,
  "max_speed_kph": 45.0,
  "night_fraction": 0.0,
  "weekend_fraction": 0.0,
  "urban_fraction": 0.8,
  "harsh_brake_events": 2,
  "harsh_accel_events": 1,
  "speeding_events": 3,
  "phone_distraction_prob": 0.05,
  "weather_exposure": 0.1,
  "created_at": "2024-01-01T08:00:00Z"
}
```

#### GET /api/v1/telematics/trips/{trip_id}/path

Get GPS path for a trip.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "trip_id": 1,
  "path": [
    {
      "lat": 40.7128,
      "lon": -74.0060,
      "ts": "2024-01-01T08:00:00Z"
    },
    {
      "lat": 40.7130,
      "lon": -74.0058,
      "ts": "2024-01-01T08:01:00Z"
    }
  ]
}
```

### Risk Scoring

#### GET /api/v1/score/user/{user_id}/latest

Get latest risk score for a user.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "user_id": 1,
  "score": 78.5,
  "band": "B",
  "expected_loss": 125.50,
  "explanations": [
    "Score 78.5 (Band B)",
    "Good speed compliance",
    "Low harsh braking rate"
  ],
  "computed_at": "2024-01-01T00:00:00Z"
}
```

#### GET /api/v1/score/trip/{trip_id}

Get risk score for a specific trip.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "trip_id": 1,
  "score": 72.3,
  "band": "B",
  "expected_loss": 95.20,
  "explanations": [
    "Score 72.3 (Band B)",
    "Moderate speeding events",
    "Good overall behavior"
  ],
  "computed_at": "2024-01-01T08:30:00Z"
}
```

#### GET /api/v1/score/user/{user_id}/history

Get risk score history for a user.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `days` (optional): Number of days to retrieve (default: 30)

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "trip_id": null,
    "score_type": "daily",
    "score_value": 78.5,
    "band": "B",
    "expected_loss": 125.50,
    "claim_probability": 0.025,
    "claim_severity": 5020.00,
    "model_version": "v1.0.0",
    "feature_values": {
      "total_distance_km": 45.2,
      "avg_speed_kph": 52.3,
      "harsh_brake_rate": 0.08
    },
    "explanations": [
      "Score 78.5 (Band B)",
      "Good speed compliance"
    ],
    "computed_at": "2024-01-01T00:00:00Z"
  }
]
```

### Dynamic Pricing

#### POST /api/v1/pricing/quote

Get dynamic pricing quote.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "policy_id": 1,
  "base_premium": 1200.00,
  "score": 78.5
}
```

**Response:**
```json
{
  "policy_id": 1,
  "band": "B",
  "delta_pct": -0.05,
  "delta_amount": -60.00,
  "new_premium": 1140.00,
  "rationale": "Score 78.5 (Band B): Good driving behavior with minimal risk factors"
}
```

#### GET /api/v1/pricing/policy/{policy_id}/adjustments

Get premium adjustments for a policy.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
[
  {
    "id": 1,
    "policy_id": 1,
    "period_start": "2024-01-01T00:00:00Z",
    "period_end": "2024-12-31T23:59:59Z",
    "delta_pct": -0.05,
    "delta_amount": -60.00,
    "new_premium": 1140.00,
    "reason": "Score 78.5 (Band B): Good driving behavior",
    "score_version": "v1.0.0",
    "risk_score_id": 1,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### GET /api/v1/pricing/policy/{policy_id}/current-premium

Get current premium for a policy.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "policy_id": 1,
  "base_premium": 1200.00,
  "current_premium": 1140.00,
  "delta_pct": -0.05,
  "last_adjustment_date": "2024-01-01T00:00:00Z"
}
```

### Admin Endpoints

#### GET /api/v1/users/admin/users

List all users (admin only).

**Headers:** `Authorization: Bearer <admin_token>`

**Query Parameters:**
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records (default: 100)

**Response:**
```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "user",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### POST /api/v1/score/compute/daily

Compute daily risk scores for all users (admin only).

**Headers:** `Authorization: Bearer <admin_token>`

**Response:**
```json
{
  "message": "Computed daily scores for 150 users",
  "total_users": 150,
  "successful": 150
}
```

#### GET /api/v1/score/admin/metrics

Get scoring system metrics (admin only).

**Headers:** `Authorization: Bearer <admin_token>`

**Response:**
```json
{
  "model_version": "v1.0.0",
  "last_training_date": "2024-01-01T00:00:00Z",
  "total_scores_computed": 1500,
  "average_score": 72.5,
  "score_distribution": {
    "A": 25,
    "B": 45,
    "C": 35,
    "D": 30,
    "E": 15
  },
  "model_performance": {
    "classification_auc": 0.78,
    "regression_rmse": 1850.50
  }
}
```

## Rate Limiting

- **Default**: 100 requests per minute per user
- **Headers**: Rate limit information included in response headers
- **Exceeded**: Returns 429 status code with retry-after header

## Error Codes

- `INVALID_CREDENTIALS` - Invalid email/password
- `USER_NOT_FOUND` - User does not exist
- `VEHICLE_NOT_FOUND` - Vehicle does not exist
- `POLICY_NOT_FOUND` - Policy does not exist
- `TRIP_NOT_FOUND` - Trip does not exist
- `INSUFFICIENT_PERMISSIONS` - User lacks required permissions
- `INVALID_SCORE` - Risk score out of valid range
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `MODEL_NOT_AVAILABLE` - ML model not loaded
- `PRICING_ERROR` - Pricing calculation failed

## Webhooks (Future)

Webhook endpoints for real-time notifications:

- `POST /webhooks/trip-completed` - Trip completion events
- `POST /webhooks/score-updated` - Risk score updates
- `POST /webhooks/premium-adjusted` - Premium adjustment events
