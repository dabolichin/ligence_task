from uuid import UUID

from fastapi import APIRouter, HTTPException
from tortoise.exceptions import DoesNotExist

from ..models import Modification
from ..schemas.image import ModificationInstructions

router = APIRouter()


@router.get(
    "/modifications/{modification_id}/instructions",
    response_model=ModificationInstructions,
)
async def get_modification_instructions(modification_id: UUID):
    """
    Get complete modification instructions for a specific variant.
    """
    try:
        modification = await Modification.get(id=modification_id).select_related(
            "image"
        )

        return ModificationInstructions(
            modification_id=modification.id,
            image_id=modification.image.id,
            variant_number=modification.variant_number,
            algorithm_type=modification.algorithm_type.value,
            instructions=modification.instructions,
            storage_path=modification.storage_path,
            original_filename=modification.image.original_filename,
            created_at=modification.created_at,
        )

    except DoesNotExist:
        raise HTTPException(
            status_code=404, detail=f"Modification {modification_id} not found"
        )
    except Exception:
        # Handle other database errors
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving modification instructions",
        )
