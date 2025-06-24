from typing import Dict
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger
from pydantic import BaseModel

from ..models.verification_result import VerificationResult, VerificationStatus

router = APIRouter()


class VerificationRequest(BaseModel):
    image_id: UUID
    modification_id: UUID


async def process_verification(image_id: UUID, modification_id: UUID):
    logger.info(
        f"Processing verification for modification {modification_id} (image {image_id})"
    )

    try:
        existing = await VerificationResult.filter(
            modification_id=modification_id
        ).first()

        if existing:
            logger.info(
                f"Verification record already exists for modification {modification_id}"
            )
            return

        await VerificationResult.create(
            modification_id=modification_id,
            status=VerificationStatus.PENDING,
        )

        logger.info(f"Created verification record for modification {modification_id}")

        # TODO: Implement actual verification logic
        # For now, just mark as completed
        verification_result = await VerificationResult.filter(
            modification_id=modification_id
        ).first()

        if verification_result:
            verification_result.status = VerificationStatus.COMPLETED
            verification_result.is_reversible = True
            verification_result.verified_with_hash = True
            verification_result.verified_with_pixels = True
            await verification_result.save()

    except Exception as e:
        logger.error(
            f"Error processing verification for modification {modification_id}: {e}",
            exc_info=True,
        )


@router.post("/verify")
async def receive_verification_request(
    request: VerificationRequest,
    background_tasks: BackgroundTasks,
) -> Dict:
    """Receive verification request from Image Processing Service."""
    logger.info(
        f"Received verification request for modification {request.modification_id}"
    )

    try:
        background_tasks.add_task(
            process_verification, request.image_id, request.modification_id
        )

        return {
            "status": "accepted",
            "modification_id": str(request.modification_id),
            "message": "Verification request queued successfully",
        }
    except Exception as e:
        logger.error(f"Error processing verification request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
