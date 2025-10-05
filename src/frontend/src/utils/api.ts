import axios, { AxiosInstance, AxiosResponse } from 'axios'
import {
  User,
  Vehicle,
  Policy,
  Trip,
  TelematicsEvent,
  RiskScore,
  PremiumAdjustment,
  LoginRequest,
  LoginResponse,
  PricingQuoteRequest,
  PricingQuoteResponse,
  DashboardStats,
  TripInsights,
} from '../types'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add auth token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    // Handle auth errors
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // Auth endpoints
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response: AxiosResponse<LoginResponse> = await this.client.post(
      '/api/v1/users/login',
      credentials
    )
    return response.data
  }

  async register(userData: {
    email: string
    password: string
    first_name?: string
    last_name?: string
  }): Promise<User> {
    const response: AxiosResponse<User> = await this.client.post(
      '/api/v1/users/register',
      userData
    )
    return response.data
  }

  // User endpoints
  async getCurrentUser(): Promise<User> {
    const response: AxiosResponse<User> = await this.client.get('/api/v1/users/me')
    return response.data
  }

  async getUserVehicles(): Promise<Vehicle[]> {
    const response: AxiosResponse<Vehicle[]> = await this.client.get('/api/v1/users/me/vehicles')
    return response.data
  }

  async getUserPolicies(): Promise<Policy[]> {
    const response: AxiosResponse<Policy[]> = await this.client.get('/api/v1/users/me/policies')
    return response.data
  }

  async getUserTrips(skip = 0, limit = 100): Promise<Trip[]> {
    const response: AxiosResponse<Trip[]> = await this.client.get(
      `/api/v1/users/me/trips?skip=${skip}&limit=${limit}`
    )
    return response.data
  }

  async getDashboardStats(): Promise<DashboardStats> {
    const response: AxiosResponse<DashboardStats> = await this.client.get('/api/v1/users/me/dashboard')
    return response.data
  }

  // Telematics endpoints
  async getTrip(tripId: number): Promise<Trip> {
    const response: AxiosResponse<Trip> = await this.client.get(`/api/v1/telematics/trips/${tripId}`)
    return response.data
  }

  async getTripEvents(tripId: number): Promise<TelematicsEvent[]> {
    const response: AxiosResponse<TelematicsEvent[]> = await this.client.get(
      `/api/v1/telematics/trips/${tripId}/events`
    )
    return response.data
  }

  async getTripPath(tripId: number): Promise<{ trip_id: number; path: any[] }> {
    const response = await this.client.get(`/api/v1/telematics/trips/${tripId}/path`)
    return response.data
  }

  async simulateTrips(data: {
    user_id: number
    vehicle_id: number
    num_trips: number
    days_back: number
  }): Promise<Trip[]> {
    const response: AxiosResponse<Trip[]> = await this.client.post(
      '/api/v1/telematics/trips/simulate',
      data
    )
    return response.data
  }

  // Scoring endpoints
  async getUserLatestScore(userId: number): Promise<RiskScore> {
    const response: AxiosResponse<RiskScore> = await this.client.get(
      `/api/v1/score/user/${userId}/latest`
    )
    return response.data
  }

  async getTripScore(tripId: number): Promise<RiskScore> {
    const response: AxiosResponse<RiskScore> = await this.client.get(`/api/v1/score/trip/${tripId}`)
    return response.data
  }

  async getUserScoreHistory(userId: number, days = 30): Promise<RiskScore[]> {
    const response: AxiosResponse<RiskScore[]> = await this.client.get(
      `/api/v1/score/user/${userId}/history?days=${days}`
    )
    return response.data
  }

  async getUserScoreTrend(userId: number, days = 30): Promise<{ user_id: number; trend: any[] }> {
    const response = await this.client.get(`/api/v1/score/user/${userId}/trend?days=${days}`)
    return response.data
  }

  // Pricing endpoints
  async getPricingQuote(request: PricingQuoteRequest): Promise<PricingQuoteResponse> {
    const response: AxiosResponse<PricingQuoteResponse> = await this.client.post(
      '/api/v1/pricing/quote',
      request
    )
    return response.data
  }

  async getPolicyAdjustments(policyId: number): Promise<PremiumAdjustment[]> {
    const response: AxiosResponse<PremiumAdjustment[]> = await this.client.get(
      `/api/v1/pricing/policy/${policyId}/adjustments`
    )
    return response.data
  }

  async getCurrentPremium(policyId: number): Promise<{
    policy_id: number
    base_premium: number
    current_premium: number
    delta_pct: number
    last_adjustment_date?: string
  }> {
    const response = await this.client.get(`/api/v1/pricing/policy/${policyId}/current-premium`)
    return response.data
  }

  // Admin endpoints
  async getAllUsers(skip = 0, limit = 100): Promise<User[]> {
    const response: AxiosResponse<User[]> = await this.client.get(
      `/api/v1/users/admin/users?skip=${skip}&limit=${limit}`
    )
    return response.data
  }

  async computeDailyScores(): Promise<{
    message: string
    total_users: number
    successful: number
  }> {
    const response = await this.client.post('/api/v1/score/compute/daily')
    return response.data
  }

  async getScoringMetrics(): Promise<{
    model_version: string
    last_training_date?: string
    total_scores_computed: number
    average_score: number
    score_distribution: Record<string, number>
    model_performance: Record<string, any>
  }> {
    const response = await this.client.get('/api/v1/score/admin/metrics')
    return response.data
  }
}

export const apiClient = new ApiClient()
