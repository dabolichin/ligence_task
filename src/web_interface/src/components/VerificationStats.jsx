import React, { useState, useEffect } from 'react'
import axios from 'axios'

const VerificationStats = () => {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get('http://localhost:8002/api/verification/statistics')
        setStats(response.data)
        setError(null)
      } catch (err) {
        console.error('Error fetching verification stats:', err)
        setError('Failed to load statistics')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 10000) // Refresh every 10 seconds

    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        <div className="space-y-2">
          <div className="h-3 bg-gray-200 rounded"></div>
          <div className="h-3 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-4">
        <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="text-gray-500 text-sm">{error}</p>
      </div>
    )
  }

  const successRate = stats ? Math.round((stats.successful_verifications / Math.max(stats.total_verifications, 1)) * 100) : 0

  return (
    <div className="space-y-3">
      {/* Compact Stats */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="text-center">
          <div className="font-bold text-blue-600 text-lg">
            {stats?.total_verifications || 0}
          </div>
          <div className="text-gray-600">Total</div>
        </div>
        
        <div className="text-center">
          <div className="font-bold text-green-600 text-lg">
            {stats?.successful_verifications || 0}
          </div>
          <div className="text-gray-600">Success</div>
        </div>
        
        <div className="text-center">
          <div className="font-bold text-purple-600 text-lg">
            {successRate}%
          </div>
          <div className="text-gray-600">Rate</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-gray-600">
          <span>Success Rate</span>
          <span>{successRate}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-gradient-to-r from-green-500 to-green-600 h-2 rounded-full transition-all duration-500"
            style={{ width: `${successRate}%` }}
          />
        </div>
      </div>

      {/* Status */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center space-x-1">
          <div className={`w-2 h-2 rounded-full ${successRate >= 95 ? 'bg-green-500' : successRate >= 80 ? 'bg-yellow-500' : 'bg-red-500'}`}></div>
          <span className="font-medium">
            {successRate >= 95 ? 'Excellent' : successRate >= 80 ? 'Good' : 'Needs Attention'}
          </span>
        </div>
        <div className="text-gray-500">
          {new Date().toLocaleTimeString()}
        </div>
      </div>
    </div>
  )
}

export default VerificationStats