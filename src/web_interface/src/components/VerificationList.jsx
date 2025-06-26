import React, { useState, useEffect } from 'react'
import axios from 'axios'

const VerificationList = ({ selectedImage }) => {
  const [verificationResults, setVerificationResults] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (selectedImage) {
      loadVerificationResults()
    }
  }, [selectedImage])

  const loadVerificationResults = async () => {
    if (!selectedImage) return
    
    setLoading(true)
    try {
      const response = await axios.get(`http://localhost:8002/api/verification/modifications/${selectedImage.id}`)
      const verifications = response.data.verifications || []
      
      // Transform API data to match component expectations
      const results = verifications.map((verification, index) => ({
        id: verification.verification_id,
        modificationId: verification.modification_id,
        result: verification.result ? 'Reversible' : 'Failed',
        status: verification.status,
        timestamp: verification.completed_at
      }))
      
      setVerificationResults(results)
    } catch (error) {
      console.error('Error loading verification results:', error)
      setVerificationResults([])
    } finally {
      setLoading(false)
    }
  }

  const getResultColor = (result, status) => {
    if (status === 'pending') return 'text-yellow-600'
    if (status === 'failed') return 'text-red-600'
    if (result === 'Reversible') return 'text-green-600'
    return 'text-gray-500'
  }

  const getResultIcon = (result, status) => {
    if (status === 'pending') {
      return (
        <svg className="w-4 h-4 animate-spin text-yellow-600" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )
    }
    
    if (status === 'failed') {
      return (
        <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      )
    }
    
    if (result === 'Reversible') {
      return (
        <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      )
    }
    
    return (
      <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )
  }

  if (!selectedImage) {
    return (
      <div className="p-8 text-center text-gray-500">
        Select an image to view verification results
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-3">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-3">
      {verificationResults.map((verification, index) => (
        <div key={verification.id} className="p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {getResultIcon(verification.result, verification.status)}
              <span className={`font-medium ${getResultColor(verification.result, verification.status)}`}>
                {verification.result}
              </span>
            </div>
            <div className="text-xs text-gray-500">
              Mod #{index + 1}
            </div>
          </div>
          
          {verification.timestamp && (
            <div className="text-xs text-gray-400 mt-1">
              {verification.timestamp}
            </div>
          )}
          
          <div className="mt-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Status:</span>
              <span className={`font-medium ${getResultColor(verification.result, verification.status)}`}>
                {verification.status.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      ))}
      
      {verificationResults.length === 0 && (
        <div className="text-center text-gray-500 py-8">
          No verification results available
        </div>
      )}
    </div>
  )
}

export default VerificationList