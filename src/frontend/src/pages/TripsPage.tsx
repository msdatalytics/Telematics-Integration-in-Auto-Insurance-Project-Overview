import React from 'react'
import { useQuery } from 'react-query'
import { apiClient } from '../utils/api'
import { Trip } from '../types'
import { MapPin, Clock, Speedometer, AlertTriangle } from 'lucide-react'
import { BAND_COLORS } from '../types'

export function TripsPage() {
  const { data: trips, isLoading, error } = useQuery<Trip[]>(
    'user-trips',
    () => apiClient.getUserTrips(0, 50)
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
        <div className="text-sm text-red-700">Failed to load trips</div>
      </div>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60)
    const mins = Math.floor(minutes % 60)
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Trips</h1>
        <p className="mt-1 text-sm text-gray-500">
          Your recent driving trips and behavior analysis
        </p>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {trips?.map((trip) => (
            <li key={trip.id}>
              <div className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <MapPin className="h-5 w-5 text-gray-400 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        Trip #{trip.id}
                      </p>
                      <p className="text-sm text-gray-500">
                        {formatDate(trip.start_ts)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <p className="text-sm text-gray-900">
                        {trip.distance_km.toFixed(1)} km
                      </p>
                      <p className="text-sm text-gray-500">
                        {formatDuration(trip.duration_minutes)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-900">
                        {trip.mean_speed_kph.toFixed(0)} km/h
                      </p>
                      <p className="text-sm text-gray-500">avg speed</p>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center space-x-1">
                        {trip.harsh_brake_events > 0 && (
                          <AlertTriangle className="h-4 w-4 text-red-500" />
                        )}
                        {trip.speeding_events > 0 && (
                          <Speedometer className="h-4 w-4 text-yellow-500" />
                        )}
                      </div>
                      <p className="text-sm text-gray-500">
                        {trip.harsh_brake_events + trip.harsh_accel_events} events
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
