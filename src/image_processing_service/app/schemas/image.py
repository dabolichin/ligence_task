from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ImageUploadResponse(BaseModel):
    """Response model for successful image upload"""

    processing_id: UUID = Field(
        ..., description="Unique identifier for the processing task"
    )
    message: str = Field(..., description="Success message")
    original_filename: str = Field(
        ..., description="Original filename of uploaded image"
    )
    file_size: int = Field(..., description="File size in bytes")


class ProcessingStatus(BaseModel):
    """Processing status response model"""

    processing_id: UUID = Field(..., description="Processing task identifier")
    status: str = Field(
        ...,
        description="Current processing status (pending, processing, completed, failed)",
    )
    progress: int = Field(..., description="Processing progress as percentage (0-100)")
    variants_completed: int = Field(..., description="Number of variants completed")
    total_variants: int = Field(
        default=100, description="Total number of variants to generate"
    )
    created_at: datetime = Field(..., description="When processing started")
    completed_at: datetime | None = Field(None, description="When processing completed")
    error_message: str | None = Field(
        None, description="Error message if status is failed"
    )


class ModificationDetails(BaseModel):
    """Detailed modification information"""

    image_id: UUID = Field(..., description="Image identifier")
    original_filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="Original file size in bytes")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    format: str = Field(..., description="Image format")
    variants_count: int = Field(..., description="Number of generated variants")
    created_at: datetime = Field(..., description="When image was uploaded")


class VariantInfo(BaseModel):
    """Information about a single variant"""

    variant_id: UUID = Field(..., description="Variant identifier")
    variant_number: int = Field(..., description="Variant number (1-100)")
    algorithm_type: str = Field(..., description="Algorithm used for modification")
    num_modifications: int = Field(
        ..., description="Number of pixel modifications applied"
    )
    storage_path: str = Field(..., description="Path to variant image file")
    created_at: datetime = Field(..., description="When variant was created")


class VariantListResponse(BaseModel):
    """Response model for listing image variants"""

    image_id: UUID = Field(..., description="Image identifier")
    variants: list[VariantInfo] = Field(..., description="List of all variants")
    total_count: int = Field(..., description="Total number of variants")


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: str | None = Field(None, description="Additional error details")


class ModificationInstructions(BaseModel):
    """Internal API response model for modification instructions"""

    modification_id: UUID = Field(..., description="Modification identifier")
    image_id: UUID = Field(..., description="Associated image identifier")
    variant_number: int = Field(..., description="Variant number (1-100)")
    algorithm_type: str = Field(..., description="Algorithm used for modification")
    instructions: dict[str, Any] = Field(
        ..., description="Complete modification instructions"
    )
    storage_path: str = Field(..., description="Path to modified image file")
    original_filename: str = Field(..., description="Original image filename")
    created_at: datetime = Field(..., description="When modification was created")
