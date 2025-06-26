import React, { useState, useEffect } from 'react'
import axios from 'axios'

const ImagesList = ({ processingId, onImageSelect, selectedImage }) => {
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (processingId) {
      loadImages()
    }
  }, [processingId])

  const loadImages = async () => {
    if (!processingId) return
    
    setLoading(true)
    try {
      const response = await axios.get(`http://localhost:8001/api/processing/${processingId}/status`)
      const data = response.data
      
      if (data.status === 'completed') {
        // Create image object from processing data
        const imageData = {
          id: processingId,
          name: `Image (${data.processing_id.substring(0, 8)})`,
          status: data.status,
          variants: data.variants_completed || 0
        }
        setImages([imageData])
        
        // Auto-select this image
        if (!selectedImage) {
          onImageSelect(imageData)
        }
      }
    } catch (error) {
      console.error('Error loading images:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-8 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-2">
      {images.map((image) => (
        <div
          key={image.id}
          className={`
            p-3 m-1 rounded cursor-pointer transition-colors
            ${selectedImage?.id === image.id 
              ? 'bg-blue-100 border-2 border-blue-500' 
              : 'hover:bg-gray-50 border-2 border-transparent'
            }
          `}
          onClick={() => onImageSelect(image)}
        >
          <div className="font-medium text-gray-900">{image.name}</div>
          <div className="text-sm text-gray-500 mt-1">
            {image.variants} variants
          </div>
        </div>
      ))}
      
      {images.length === 0 && !loading && (
        <div className="p-4 text-center text-gray-500">
          No images uploaded yet
        </div>
      )}
    </div>
  )
}

export default ImagesList