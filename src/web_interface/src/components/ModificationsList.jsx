import React, { useState, useEffect } from 'react'
import axios from 'axios'

const ModificationsList = ({ selectedImage }) => {
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage] = useState(8)
  const [modifications, setModifications] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (selectedImage) {
      loadModifications()
      setCurrentPage(1)
    }
  }, [selectedImage])

  const loadModifications = async () => {
    if (!selectedImage) return
    
    setLoading(true)
    try {
      const response = await axios.get(`http://localhost:8001/api/images/${selectedImage.id}/variants`)
      const variants = response.data.variants || []
      
      // Transform API data to match component expectations
      const modsList = variants.map((variant, index) => ({
        id: variant.variant_id,
        name: `${selectedImage.name}Modification${index + 1}`,
        status: variant.status || 'COMPLETED',
        verificationResult: variant.verified ? 'Reversible' : 'Pending'
      }))
      
      setModifications(modsList)
    } catch (error) {
      console.error('Error loading modifications:', error)
      setModifications([])
    } finally {
      setLoading(false)
    }
  }

  const totalPages = Math.ceil(modifications.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const currentModifications = modifications.slice(startIndex, startIndex + itemsPerPage)

  const getStatusColor = (status) => {
    switch (status) {
      case 'PENDING': return 'text-yellow-600'
      case 'COMPLETED': return 'text-green-600'
      case 'FAILED': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getVerificationColor = (result) => {
    switch (result) {
      case 'Reversible': return 'text-green-600'
      case 'N/A': return 'text-gray-500'
      default: return 'text-gray-600'
    }
  }

  if (!selectedImage) {
    return (
      <div className="p-8 text-center text-gray-500">
        Select an image to view its modifications
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-3">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-2 p-4">
          {currentModifications.map((mod) => (
            <div key={mod.id} className="flex justify-between items-center p-3 hover:bg-gray-50 rounded">
              <div className="flex-1">
                <div className="font-medium text-gray-900">{mod.name}</div>
              </div>
              <div className="flex-1 text-center">
                <span className={`font-medium ${getStatusColor(mod.status)}`}>
                  {mod.status}
                </span>
              </div>
              <div className="flex-1 text-right">
                <span className={`font-medium ${getVerificationColor(mod.verificationResult)}`}>
                  {mod.verificationResult}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="border-t p-4 bg-gray-50">
          <div className="flex justify-center items-center space-x-2">
            <button
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50"
            >
              &lt;
            </button>
            
            {[...Array(Math.min(totalPages, 3))].map((_, i) => {
              const pageNum = i + 1
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`px-3 py-1 text-sm border rounded ${
                    currentPage === pageNum 
                      ? 'bg-green-100 text-green-700 border-green-300' 
                      : 'hover:bg-gray-100'
                  }`}
                >
                  {pageNum}
                </button>
              )
            })}
            
            {totalPages > 3 && (
              <>
                <span className="px-2 text-gray-500">...</span>
                <button
                  onClick={() => setCurrentPage(totalPages)}
                  className={`px-3 py-1 text-sm border rounded ${
                    currentPage === totalPages 
                      ? 'bg-green-100 text-green-700 border-green-300' 
                      : 'hover:bg-gray-100'
                  }`}
                >
                  Last
                </button>
              </>
            )}
            
            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50"
            >
              &gt;
            </button>
          </div>
          
          <div className="text-center mt-2 text-sm text-green-600">
            &lt; 1  2  3  ...  Last &gt;
          </div>
        </div>
      )}
    </div>
  )
}

export default ModificationsList