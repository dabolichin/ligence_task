from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModificationInstructionData(BaseModel):
    """Modification instructions retrieved from Image Processing Service."""

    modification_id: UUID = Field(..., description="Modification identifier")
    image_id: UUID = Field(..., description="Associated image identifier")
    original_filename: str = Field(..., description="Original image filename")
    variant_number: int = Field(..., description="Variant number (1-100)")
    algorithm_type: str = Field(..., description="Algorithm used for modification")
    instructions: dict[str, Any] = Field(
        ..., description="Complete modification instructions"
    )
    storage_path: str = Field(..., description="Path to modified image file")
    created_at: datetime = Field(..., description="When modification was created")


class VerificationRequestData(BaseModel):
    """Schema for verification request data sent between services."""

    image_id: UUID = Field(..., description="Image identifier")
    modification_id: UUID = Field(..., description="Modification identifier")


class VerificationStatusResponse(BaseModel):
    """Response schema for verification status endpoint."""

    verification_id: str = Field(..., description="Verification identifier")
    status: str = Field(..., description="Verification status")
    is_reversible: Optional[bool] = Field(
        None, description="Whether modification is reversible"
    )
    verified_with_hash: Optional[bool] = Field(
        None, description="Whether hash verification passed"
    )
    verified_with_pixels: Optional[bool] = Field(
        None, description="Whether pixel verification passed"
    )
    created_at: Optional[str] = Field(None, description="When verification was created")
    completed_at: Optional[str] = Field(
        None, description="When verification was completed"
    )
    message: Optional[str] = Field(None, description="Status message or error details")


class VerificationStatisticsResponse(BaseModel):
    """Response schema for verification statistics endpoint."""

    total_verifications: int = Field(..., description="Total number of verifications")
    successful_verifications: int = Field(
        ..., description="Number of successful verifications"
    )
    failed_verifications: int = Field(..., description="Number of failed verifications")
    pending_verifications: int = Field(
        ..., description="Number of pending verifications"
    )
    success_rate: float = Field(..., description="Success rate as percentage")
    error: Optional[str] = Field(
        None, description="Error message if statistics retrieval failed"
    )


class VerificationHistoryItem(BaseModel):
    """Schema for individual verification history item."""

    modification_id: str = Field(..., description="Modification identifier")
    status: str = Field(..., description="Verification status")
    is_reversible: Optional[bool] = Field(
        None, description="Whether modification is reversible"
    )
    verified_with_hash: Optional[bool] = Field(
        None, description="Whether hash verification passed"
    )
    verified_with_pixels: Optional[bool] = Field(
        None, description="Whether pixel verification passed"
    )
    created_at: Optional[str] = Field(None, description="When verification was created")
    completed_at: Optional[str] = Field(
        None, description="When verification was completed"
    )


class VerificationHistoryResponse(BaseModel):
    """Response schema for verification history endpoint."""

    verifications: list[VerificationHistoryItem] = Field(
        ..., description="List of verification records"
    )
    total_count: int = Field(..., description="Total number of verification records")
    limit: int = Field(..., description="Number of records requested")
    offset: int = Field(..., description="Starting offset for pagination")
    error: Optional[str] = Field(
        None, description="Error message if history retrieval failed"
    )


class VerificationsByModificationResponse(BaseModel):
    """Response schema for verifications by modification ID endpoint."""

    modification_id: str = Field(..., description="Modification identifier")
    verifications: list[VerificationHistoryItem] = Field(
        ..., description="List of verification records for this modification"
    )
    total_count: int = Field(
        ..., description="Total number of verifications for this modification"
    )
    error: Optional[str] = Field(None, description="Error message if retrieval failed")
