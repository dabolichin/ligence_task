import React, { useState } from 'react'
import axios from 'axios'

const FileUpload = ({ onUploadSuccess, onError }) => {
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    const imageFile = files.find(file => file.type.startsWith('image/'))
    if (imageFile) {
      uploadFile(imageFile)
    } else {
      onError('Please upload an image file (JPEG, PNG, BMP)')
    }
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file && file.type.startsWith('image/')) {
      uploadFile(file)
    } else {
      onError('Please upload an image file (JPEG, PNG, BMP)')
    }
  }

  const uploadFile = async (file) => {
    if (file.size > 100 * 1024 * 1024) { // 100MB limit
      onError('File size must be less than 100MB')
      return
    }

    setUploading(true)
    setUploadProgress(0)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post('http://localhost:8001/api/modify', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          setUploadProgress(progress)
        }
      })

      setUploading(false)
      onUploadSuccess(response.data)
    } catch (error) {
      setUploading(false)
      const message = error.response?.data?.detail || 'Upload failed'
      onError(message)
    }
  }

  return (
    <div className="bg-white rounded-lg border-2 border-orange-400 px-4 py-2">
      <div className="flex items-center space-x-3">
        {uploading ? (
          <>
            <svg className="w-5 h-5 animate-spin text-orange-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="text-orange-600 font-medium">Uploading... {uploadProgress}%</span>
          </>
        ) : (
          <>
            <label className="cursor-pointer flex items-center space-x-2">
              <div className="bg-orange-500 text-white px-3 py-1 rounded text-sm font-medium hover:bg-orange-600 transition-colors">
                File Upload
              </div>
              <input
                type="file"
                className="hidden"
                accept="image/*"
                onChange={handleFileSelect}
              />
            </label>
            <span className="text-gray-600 text-sm">JPEG, PNG, BMP up to 100MB</span>
          </>
        )}
      </div>
      
      {/* Hidden drag drop area for better UX */}
      <div
        className={`
          absolute inset-0 pointer-events-none
          ${isDragging ? 'pointer-events-auto bg-blue-500 bg-opacity-10 border-2 border-blue-500 border-dashed' : ''}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      />
    </div>
  )
}

export default FileUpload