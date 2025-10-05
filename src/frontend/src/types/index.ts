// API Types
export interface User {
  id: number
  email: string
  first_name?: string
  last_name?: string
  role: 'user' | 'admin'
  is_active: boolean
  created_at: string
  updated_at?: string
}

export interface Vehicle {
  id: number
  user_id: number
  vin: string
  make: string
  model: string
  year: number
  color?: string
  license_plate?: string
  created_at: string
}

export interface Policy {
  id: number
  user_id: number
  vehicle_id: number
  policy_number: string
  base_premium: number
  status: 'active' | 'cancelled' | 'expired'
  start_date: string
  end_date: string
  created_at: string
}

export interface Trip {
  id: number
  user_id: number
  vehicle_id: number
  trip_uuid: string
  start_ts: string
  end_ts: string
  distance_km: number
  duration_minutes: number
  mean_speed_kph: number
  max_speed_kph: number
  night_fraction: number
  weekend_fraction: number
  urban_fraction: number
  harsh_brake_events: number
  harsh_accel_events: number
  speeding_events: number
  phone_distraction_prob: number
  weather_exposure: number
  created_at: string
}

export interface TelematicsEvent {
  id: number
  trip_id: number
  event_uuid: string
  ts: string
  lat: number
  lon: number
  speed_kph: number
  accel_ms2: number
  brake_intensity: number
  heading?: number
  altitude?: number
  accuracy?: number
  created_at: string
}

export interface RiskScore {
  id: number
  user_id: number
  trip_id?: number
  score_type: 'daily' | 'trip' | 'weekly' | 'monthly'
  score_value: number
  band: 'A' | 'B' | 'C' | 'D' | 'E'
  expected_loss: number
  claim_probability: number
  claim_severity: number
  model_version: string
  feature_values?: Record<string, any>
  explanations?: string[]
  computed_at: string
}

export interface PremiumAdjustment {
  id: number
  policy_id: number
  period_start: string
  period_end: string
  delta_pct: number
  delta_amount: number
  new_premium: number
  reason?: string
  score_version: string
  risk_score_id?: number
  created_at: string
}

// API Request/Response Types
export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface PricingQuoteRequest {
  policy_id?: number
  base_premium?: number
  score: number
}

export interface PricingQuoteResponse {
  policy_id?: number
  band: 'A' | 'B' | 'C' | 'D' | 'E'
  delta_pct: number
  delta_amount: number
  new_premium: number
  rationale: string
}

export interface DashboardStats {
  current_premium: number
  premium_delta: number
  premium_delta_pct: number
  current_band: 'A' | 'B' | 'C' | 'D' | 'E'
  current_score: number
  score_trend: Array<{
    date: string
    score: number
    band: string
  }>
  total_trips: number
  total_distance_km: number
  avg_score: number
}

export interface TripInsights {
  trip_id: number
  score: number
  band: 'A' | 'B' | 'C' | 'D' | 'E'
  distance_km: number
  duration_minutes: number
  harsh_events: number
  speeding_events: number
  night_fraction: number
  weather_exposure: number
  map_data?: {
    path: Array<{
      lat: number
      lon: number
      ts: string
    }>
  }
}

// UI Types
export interface BandColors {
  A: string
  B: string
  C: string
  D: string
  E: string
}

export const BAND_COLORS: BandColors = {
  A: 'text-green-600 bg-green-100',
  B: 'text-blue-600 bg-blue-100',
  C: 'text-yellow-600 bg-yellow-100',
  D: 'text-orange-600 bg-orange-100',
  E: 'text-red-600 bg-red-100',
}

export interface MapPoint {
  lat: number
  lon: number
  timestamp: string
  speed?: number
  event_type?: 'harsh_brake' | 'harsh_accel' | 'speeding' | 'normal'
}
