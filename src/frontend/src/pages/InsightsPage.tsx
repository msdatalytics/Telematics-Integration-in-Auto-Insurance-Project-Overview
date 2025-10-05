import React from 'react'
import { useQuery } from 'react-query'
import { apiClient } from '../utils/api'
import { RiskScore } from '../types'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Shield, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'

export function InsightsPage() {
  const { data: scoreHistory, isLoading } = useQuery<RiskScore[]>(
    'score-history',
    () => apiClient.getUserScoreHistory(1, 30)
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // Process data for charts
  const bandDistribution = scoreHistory?.reduce((acc, score) => {
    acc[score.band] = (acc[score.band] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const pieData = Object.entries(bandDistribution || {}).map(([band, count]) => ({
    name: `Band ${band}`,
    value: count,
    color: band === 'A' ? '#10B981' : band === 'B' ? '#3B82F6' : band === 'C' ? '#F59E0B' : band === 'D' ? '#F97316' : '#EF4444'
  }))

  const insights = [
    {
      icon: CheckCircle,
      title: 'Good Speed Compliance',
      description: 'You maintain appropriate speeds most of the time',
      type: 'positive' as const
    },
    {
      icon: AlertTriangle,
      title: 'Night Driving Detected',
      description: 'Consider reducing night driving for better scores',
      type: 'warning' as const
    },
    {
      icon: TrendingUp,
      title: 'Improving Trend',
      description: 'Your scores have been improving over the last week',
      type: 'positive' as const
    }
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Insights</h1>
        <p className="mt-1 text-sm text-gray-500">
          Driving behavior analysis and recommendations
        </p>
      </div>

      {/* Insights Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {insights.map((insight, index) => {
          const Icon = insight.icon
          return (
            <div key={index} className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <Icon className={`h-6 w-6 ${
                      insight.type === 'positive' ? 'text-green-500' : 
                      insight.type === 'warning' ? 'text-yellow-500' : 'text-red-500'
                    }`} />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-900 truncate">
                        {insight.title}
                      </dt>
                      <dd className="text-sm text-gray-500">
                        {insight.description}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Score Distribution */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Score Band Distribution
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Score Trends */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Score Trends
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={scoreHistory?.slice(-7)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="computed_at" tickFormatter={(value) => new Date(value).toLocaleDateString()} />
                  <YAxis domain={[0, 100]} />
                  <Tooltip 
                    labelFormatter={(value) => new Date(value).toLocaleDateString()}
                    formatter={(value: number) => [value.toFixed(1), 'Score']}
                  />
                  <Bar dataKey="score_value" fill="#3B82F6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            Recommendations
          </h3>
          <div className="space-y-4">
            <div className="flex items-start">
              <CheckCircle className="h-5 w-5 text-green-500 mr-3 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium text-gray-900">Maintain Safe Following Distance</h4>
                <p className="text-sm text-gray-500">Keep a safe distance from other vehicles to reduce harsh braking events.</p>
              </div>
            </div>
            <div className="flex items-start">
              <CheckCircle className="h-5 w-5 text-green-500 mr-3 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium text-gray-900">Smooth Acceleration</h4>
                <p className="text-sm text-gray-500">Gradually accelerate to avoid harsh acceleration events.</p>
              </div>
            </div>
            <div className="flex items-start">
              <AlertTriangle className="h-5 w-5 text-yellow-500 mr-3 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium text-gray-900">Reduce Night Driving</h4>
                <p className="text-sm text-gray-500">Consider planning trips during daylight hours when possible.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
