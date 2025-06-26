import React, { useState } from 'react'
import FileUpload from './components/FileUpload'
import ProcessingStatus from './components/ProcessingStatus'
import ImagesList from './components/ImagesList'
import ModificationsList from './components/ModificationsList'
import VerificationList from './components/VerificationList'
import VerificationStats from './components/VerificationStats'
import Toast from './components/Toast'

function App() {
  const [processingId, setProcessingId] = useState(null)
  const [processingStatus, setProcessingStatus] = useState('idle')
  const [selectedImage, setSelectedImage] = useState(null)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 5000)
  }

  const handleUploadSuccess = (data) => {
    setProcessingId(data.processing_id)
    setProcessingStatus('processing')
    showToast('Upload successful! Processing started...', 'success')
  }

  const handleProcessingComplete = (data) => {
    setProcessingStatus('completed')
    showToast('Processing completed!', 'success')
  }

  const handleImageSelect = (image) => {
    setSelectedImage(image)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <FileUpload 
              onUploadSuccess={handleUploadSuccess}
              onError={(message) => showToast(message, 'error')}
            />
            {processingId && (
              <ProcessingStatus 
                processingId={processingId}
                status={processingStatus}
                onComplete={handleProcessingComplete}
              />
            )}
          </div>
        </div>
      </header>

      {/* Main Content - Three Column Layout */}
      <main className="h-[calc(100vh-80px)] flex">
        {/* Left Column - Images */}
        <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b bg-blue-50">
            <h2 className="font-semibold text-blue-700">Images modified</h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            <ImagesList 
              processingId={processingId}
              onImageSelect={handleImageSelect}
              selectedImage={selectedImage}
            />
          </div>
        </div>

        {/* Middle Column - Modifications */}
        <div className="flex-1 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b bg-blue-50 flex justify-between items-center">
            <h2 className="font-semibold text-blue-700">Modifications</h2>
            <h3 className="font-semibold text-blue-700">Verification status</h3>
          </div>
          <div className="flex-1 overflow-y-auto">
            <ModificationsList 
              selectedImage={selectedImage}
            />
          </div>
        </div>

        {/* Right Column - Verification Results & Stats */}
        <div className="w-80 bg-white flex flex-col">
          <div className="p-4 border-b bg-blue-50">
            <h2 className="font-semibold text-blue-700">Verification result</h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            <VerificationList selectedImage={selectedImage} />
          </div>
          <div className="border-t p-4">
            <h3 className="font-semibold text-blue-700 mb-4">Verification statistics</h3>
            <VerificationStats />
          </div>
        </div>
      </main>

      {/* Toast Notifications */}
      {toast && (
        <Toast 
          message={toast.message} 
          type={toast.type} 
          onClose={() => setToast(null)} 
        />
      )}
    </div>
  )
}

export default App