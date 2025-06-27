import React, { useState, useEffect } from 'react'
import axios from 'axios'

const ImagesList = ({ processingId, onImageSelect, selectedImage, processingStatus }) => {
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Load all images on component mount
    loadAllImages()
  }, [])

  useEffect(() => {
    if (processingId) {
      loadImages()
    }
  }, [processingId, processingStatus])

  const loadAllImages = async () => {
    setLoading(true)
    try {
      const response = await axios.get('http://localhost:8001/api/images')
      const data = response.data
      
      const imageList = data.images.map(img => ({
        id: img.image_id,
        name: `${img.original_filename} (${img.image_id.toString().substring(0, 8)})`,
        status: img.status,
        variants: img.variants_count,
        created_at: img.created_at
      }))
      
      setImages(imageList)
    } catch (error) {
      console.error('Error loading all images:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadImages = async () => {
    if (!processingId) return
    
    setLoading(true)
    try {
      const response = await axios.get(`http://localhost:8001/api/processing/${processingId}/status`)
      const data = response.data
      
      if (data.status === 'completed' || data.status === 'processing') {
        // Create image object from processing data
        const imageData = {
          id: processingId,
          name: `Image (${processingId.toString().substring(0, 8)})`,
          status: data.status,
          variants: data.variants_completed || 0
        }
        
        // Update existing images or add new one
        setImages(prevImages => {
          const existingIndex = prevImages.findIndex(img => img.id === processingId)
          if (existingIndex >= 0) {
            const updated = [...prevImages]
            updated[existingIndex] = imageData
            return updated
          } else {
            return [imageData, ...prevImages]
          }
        })
        
        // Auto-select this image when completed
        if (data.status === 'completed' && !selectedImage) {
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
            {image.status === 'processing' ? (
              <span className="text-blue-600">Processing... ({image.variants}/100)</span>
            ) : (
              <span>{image.variants} variants complete</span>
            )}
          </div>
          {image.status === 'processing' && (
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                style={{ width: `${(image.variants / 100) * 100}%` }}
              ></div>
            </div>
          )}
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