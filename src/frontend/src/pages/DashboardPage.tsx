import React from 'react'
import { useQuery } from 'react-query'
import { apiClient } from '../utils/api'
import { DashboardStats } from '../types'
import { TrendingUp, TrendingDown, Car, MapPin, Shield, DollarSign } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { BAND_COLORS } from '../types'

export function DashboardPage() {
  const { data: stats, isLoading, error } = useQuery<DashboardStats>(
    'dashboard-stats',
    () => apiClient.getDashboardStats(),
    {
      refetchInterval: 30000, // Refetch every 30 seconds
    }
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <div className="text-sm text-red-700">Failed to load dashboard data</div>
      </div>
    )
  }

  if (!stats) return null

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount)
  }

  const formatDistance = (km: number) => {
    return `${km.toFixed(1)} km`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Your driving behavior and insurance overview
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {/* Current Premium */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <DollarSign className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Current Premium
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {formatCurrency(stats.current_premium)}
                  </dd>
                </dl>
              </div>
            </div>
            <div className="mt-3">
              <div className={`flex items-center text-sm ${
                stats.premium_delta >= 0 ? 'text-red-600' : 'text-green-600'
              }`}>
                {stats.premium_delta >= 0 ? (
                  <TrendingUp className="h-4 w-4 mr-1" />
                ) : (
                  <TrendingDown className="h-4 w-4 mr-1" />
                )}
                {Math.abs(stats.premium_delta_pct * 100).toFixed(1)}% change
              </div>
            </div>
          </div>
        </div>

        {/* Risk Score */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Shield className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Risk Score
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {stats.current_score.toFixed(1)}
                  </dd>
                </dl>
              </div>
            </div>
            <div className="mt-3">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                BAND_COLORS[stats.current_band]
              }`}>
                Band {stats.current_band}
              </span>
            </div>
          </div>
        </div>

        {/* Total Trips */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Car className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Trips
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {stats.total_trips}
                  </dd>
                </dl>
              </div>
            </div>
            <div className="mt-3">
              <div className="text-sm text-gray-500">
                {formatDistance(stats.total_distance_km)} driven
              </div>
            </div>
          </div>
        </div>

        {/* Average Score */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <TrendingUp className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Avg Score (30d)
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {stats.avg_score.toFixed(1)}
                  </dd>
                </dl>
              </div>
            </div>
            <div className="mt-3">
              <div className="text-sm text-gray-500">
                Last 30 days
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Score Trend Chart */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            Risk Score Trend
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats.score_trend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(value) => new Date(value).toLocaleDateString()}
                />
                <YAxis domain={[0, 100]} />
                <Tooltip 
                  labelFormatter={(value) => new Date(value).toLocaleDateString()}
                  formatter={(value: number) => [value.toFixed(1), 'Score']}
                />
                <Line 
                  type="monotone" 
                  dataKey="score" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            Recent Activity
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-gray-200">
              <div className="flex items-center">
                <Shield className="h-5 w-5 text-blue-500 mr-3" />
                <span className="text-sm text-gray-900">Daily risk score updated</span>
              </div>
              <span className="text-sm text-gray-500">Today</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-gray-200">
              <div className="flex items-center">
                <Car className="h-5 w-5 text-green-500 mr-3" />
                <span className="text-sm text-gray-900">New trip recorded</span>
              </div>
              <span className="text-sm text-gray-500">2 hours ago</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center">
                <DollarSign className="h-5 w-5 text-yellow-500 mr-3" />
                <span className="text-sm text-gray-900">Premium adjustment applied</span>
              </div>
              <span className="text-sm text-gray-500">1 day ago</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
