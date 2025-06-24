from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger

from ..core.dependencies import get_verification_orchestrator_dependency
from ..models.verification_result import VerificationResult, VerificationStatus
from ..schemas import VerificationRequestData as VerificationRequest
from ..services.verification_orchestrator import VerificationOrchestrator

router = APIRouter()


@router.post("/verify")
async def receive_verification_request(
    request: VerificationRequest,
    background_tasks: BackgroundTasks,
    verification_orchestrator: VerificationOrchestrator = Depends(
        get_verification_orchestrator_dependency
    ),
) -> dict:
    """Receive verification request from Image Processing Service."""
    logger.info(
        f"Received verification request for modification {request.modification_id}"
    )

    try:
        existing_verification = await VerificationResult.filter(
            modification_id=request.modification_id
        ).first()

        if existing_verification:
            logger.info(
                f"Verification already exists for modification {request.modification_id}"
            )
            return {
                "status": "accepted",
                "modification_id": str(request.modification_id),
                "message": "Verification request already exists",
            }

        verification_record = await VerificationResult.create(
            modification_id=request.modification_id,
            status=VerificationStatus.PENDING,
        )

        logger.info(
            f"Created verification record {verification_record.id} for modification {request.modification_id}"
        )

        background_tasks.add_task(
            verification_orchestrator.execute_verification_background,
            request.image_id,
            request.modification_id,
        )

        return {
            "status": "accepted",
            "modification_id": str(request.modification_id),
            "message": "Verification request queued successfully",
        }
    except Exception as e:
        logger.error(f"Error processing verification request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
