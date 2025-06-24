from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModificationInstructionData(BaseModel):
    """Pydantic schema for modification instructions retrieved from Image Processing Service."""

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
    """Pydantic schema for verification request data sent between services."""

    image_id: UUID = Field(..., description="Image identifier")
    modification_id: UUID = Field(..., description="Modification identifier")
