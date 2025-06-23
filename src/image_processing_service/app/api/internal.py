from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from tortoise.exceptions import DoesNotExist

from ..core.dependencies import get_variant_generator
from ..models import Modification
from ..schemas.image import ModificationInstructions
from ..services.variant_generation import VariantGenerationService

router = APIRouter()


@router.get(
    "/modifications/{modification_id}/instructions",
    response_model=ModificationInstructions,
)
async def get_modification_instructions(
    modification_id: UUID,
    variant_generator: VariantGenerationService = Depends(get_variant_generator),
):
    """
    Get complete modification instructions for a specific variant.
    """
    logger.info(f"Retrieving modification instructions for {modification_id}")

    try:
        modification = await Modification.get(id=modification_id).select_related(
            "image"
        )

        return ModificationInstructions(
            modification_id=modification.id,
            image_id=modification.image.id,
            original_filename=modification.image.original_filename,
            variant_number=modification.variant_number,
            algorithm_type=modification.algorithm_type.value,
            instructions=modification.instructions,
            storage_path=modification.storage_path,
            created_at=modification.created_at,
        )

    except DoesNotExist:
        logger.warning(f"Modification {modification_id} not found")
        raise HTTPException(
            status_code=404, detail=f"Modification {modification_id} not found"
        )
    except Exception as e:
        logger.error(f"Error retrieving modification instructions: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving modification instructions",
        )
