import React from 'react'
import { Gift, Star, Trophy, Target } from 'lucide-react'

export function RewardsPage() {
  const achievements = [
    {
      icon: Star,
      title: 'Safe Driver',
      description: 'No harsh braking events for 7 days',
      points: 100,
      earned: true,
      date: '2024-01-15'
    },
    {
      icon: Target,
      title: 'Speed Master',
      description: 'Maintained speed limit for 30 trips',
      points: 150,
      earned: true,
      date: '2024-01-10'
    },
    {
      icon: Trophy,
      title: 'Consistency Champion',
      description: 'Score above 80 for 14 consecutive days',
      points: 200,
      earned: false,
      progress: 12
    },
    {
      icon: Gift,
      title: 'Weekend Warrior',
      description: 'Complete 10 weekend trips safely',
      points: 75,
      earned: false,
      progress: 6
    }
  ]

  const totalPoints = achievements
    .filter(a => a.earned)
    .reduce((sum, a) => sum + a.points, 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Rewards</h1>
        <p className="mt-1 text-sm text-gray-500">
          Earn points and achievements for safe driving
        </p>
      </div>

      {/* Points Summary */}
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow-lg">
        <div className="px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">Total Points</h2>
              <p className="text-blue-100 mt-1">Keep driving safely to earn more!</p>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold text-white">{totalPoints}</div>
              <div className="text-blue-100">points earned</div>
            </div>
          </div>
        </div>
      </div>

      {/* Achievements */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {achievements.map((achievement, index) => {
          const Icon = achievement.icon
          return (
            <div key={index} className={`bg-white overflow-hidden shadow rounded-lg border-2 ${
              achievement.earned ? 'border-green-200' : 'border-gray-200'
            }`}>
              <div className="p-6">
                <div className="flex items-center">
                  <div className={`flex-shrink-0 p-3 rounded-full ${
                    achievement.earned ? 'bg-green-100' : 'bg-gray-100'
                  }`}>
                    <Icon className={`h-6 w-6 ${
                      achievement.earned ? 'text-green-600' : 'text-gray-400'
                    }`} />
                  </div>
                  <div className="ml-4 flex-1">
                    <h3 className="text-lg font-medium text-gray-900">
                      {achievement.title}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">
                      {achievement.description}
                    </p>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="text-sm font-medium text-blue-600">
                        {achievement.points} points
                      </span>
                      {achievement.earned ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Earned
                        </span>
                      ) : (
                        <span className="text-sm text-gray-500">
                          {achievement.progress}/10
                        </span>
                      )}
                    </div>
                    {achievement.earned && (
                      <p className="text-xs text-gray-400 mt-1">
                        Earned on {new Date(achievement.date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
                {!achievement.earned && (
                  <div className="mt-4">
                    <div className="bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${(achievement.progress! / 10) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Rewards Program Info */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            How Rewards Work
          </h3>
          <div className="space-y-3">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
              </div>
              <div className="ml-3">
                <p className="text-sm text-gray-700">
                  Earn points for safe driving behaviors like smooth acceleration, maintaining speed limits, and avoiding harsh braking.
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
              </div>
              <div className="ml-3">
                <p className="text-sm text-gray-700">
                  Complete achievements to unlock bonus points and special rewards.
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
              </div>
              <div className="ml-3">
                <p className="text-sm text-gray-700">
                  Points can be redeemed for premium discounts and other benefits.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
