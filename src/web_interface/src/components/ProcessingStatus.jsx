import React, { useState, useEffect } from 'react'
import axios from 'axios'

const ProcessingStatus = ({ processingId, status, onComplete }) => {
  const [progress, setProgress] = useState(0)
  const [statusDetails, setStatusDetails] = useState(null)

  useEffect(() => {
    if (!processingId || status === 'completed') return

    const pollStatus = async () => {
      try {
        const response = await axios.get(`http://localhost:8001/api/processing/${processingId}/status`)
        const data = response.data
        
        setProgress(data.progress || 0)
        setStatusDetails(data)
        
        if (data.status === 'completed') {
          onComplete(data)
        }
      } catch (error) {
        console.error('Error polling status:', error)
      }
    }

    const interval = setInterval(pollStatus, 2000)
    pollStatus() // Initial call

    return () => clearInterval(interval)
  }, [processingId, status, onComplete])

  const getStatusIcon = () => {
    switch (status) {
      case 'processing':
        return (
          <svg className="w-6 h-6 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )
      case 'completed':
        return (
          <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )
      case 'failed':
        return (
          <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )
      default:
        return (
          <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
    }
  }

  const getStatusText = () => {
    switch (status) {
      case 'processing':
        return 'Processing variants...'
      case 'completed':
        return 'Processing completed'
      case 'failed':
        return 'Processing failed'
      default:
        return 'Waiting to start...'
    }
  }

  const getStatusColor = () => {
    switch (status) {
      case 'processing':
        return 'text-blue-600'
      case 'completed':
        return 'text-green-600'
      case 'failed':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <div className="flex items-center space-x-3">
      {getStatusIcon()}
      <div>
        <p className={`font-medium ${getStatusColor()}`}>
          {getStatusText()}
        </p>
        {status === 'processing' && (
          <p className="text-sm text-gray-500">
            Progress: {progress}% ({statusDetails?.variants_completed || 0}/100 variants)
          </p>
        )}
      </div>
    </div>
  )
}

export default ProcessingStatus