from uuid import UUID

from fastapi import APIRouter, Depends
from loguru import logger

from ..core.dependencies import get_service_container
from ..models.verification_result import VerificationResult, VerificationStatus

router = APIRouter()


@router.get("/verification/{verification_id}/status")
async def get_verification_status(
    verification_id: str,
    container=Depends(get_service_container),
) -> dict:
    """Get verification status for a specific verification ID."""
    logger.info(f"Getting verification status for ID: {verification_id}")

    try:
        modification_id = UUID(verification_id)

        verification_result = await VerificationResult.filter(
            modification_id=modification_id
        ).first()

        if not verification_result:
            return {
                "verification_id": verification_id,
                "status": "not_found",
                "message": f"No verification found for ID {verification_id}",
            }

        return {
            "verification_id": verification_id,
            "status": verification_result.status.value,
            "is_reversible": verification_result.is_reversible,
            "verified_with_hash": verification_result.verified_with_hash,
            "verified_with_pixels": verification_result.verified_with_pixels,
            "created_at": verification_result.created_at.isoformat()
            if verification_result.created_at
            else None,
            "completed_at": verification_result.completed_at.isoformat()
            if verification_result.completed_at
            else None,
        }

    except ValueError:
        return {
            "verification_id": verification_id,
            "status": "invalid",
            "message": "Invalid verification ID format",
        }
    except Exception as e:
        logger.error(f"Error getting verification status for {verification_id}: {e}")
        return {
            "verification_id": verification_id,
            "status": "error",
            "message": "Internal server error",
        }


@router.get("/verification/statistics")
async def get_verification_statistics(
    container=Depends(get_service_container),
) -> dict:
    """Get overall verification metrics and statistics."""
    logger.info("Getting verification statistics")

    try:
        total_verifications = await VerificationResult.all().count()
        successful_verifications = await VerificationResult.filter(
            status=VerificationStatus.COMPLETED, is_reversible=True
        ).count()
        failed_verifications = await VerificationResult.filter(
            status=VerificationStatus.COMPLETED, is_reversible=False
        ).count()
        pending_verifications = await VerificationResult.filter(
            status=VerificationStatus.PENDING
        ).count()

        success_rate = (
            (successful_verifications / total_verifications * 100.0)
            if total_verifications > 0
            else 0.0
        )

        return {
            "total_verifications": total_verifications,
            "successful_verifications": successful_verifications,
            "failed_verifications": failed_verifications,
            "pending_verifications": pending_verifications,
            "success_rate": round(success_rate, 2),
        }

    except Exception as e:
        logger.error(f"Error getting verification statistics: {e}")
        return {
            "total_verifications": 0,
            "successful_verifications": 0,
            "failed_verifications": 0,
            "pending_verifications": 0,
            "success_rate": 0.0,
            "error": "Failed to retrieve statistics",
        }


@router.get("/verification/history")
async def get_verification_history(
    limit: int = 50,
    offset: int = 0,
    container=Depends(get_service_container),
) -> dict:
    """Get verification audit trail and history."""
    logger.info(f"Getting verification history with limit={limit}, offset={offset}")

    try:
        # Validate parameters
        limit = min(max(limit, 1), 100)  # Between 1 and 100
        offset = max(offset, 0)  # At least 0

        total_count = await VerificationResult.all().count()

        verification_results = (
            await VerificationResult.all()
            .offset(offset)
            .limit(limit)
            .order_by("-created_at")
        )

        verifications = []
        for result in verification_results:
            verifications.append(
                {
                    "modification_id": str(result.modification_id),
                    "status": result.status.value,
                    "is_reversible": result.is_reversible,
                    "verified_with_hash": result.verified_with_hash,
                    "verified_with_pixels": result.verified_with_pixels,
                    "created_at": result.created_at.isoformat()
                    if result.created_at
                    else None,
                    "completed_at": result.completed_at.isoformat()
                    if result.completed_at
                    else None,
                }
            )

        return {
            "verifications": verifications,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Error getting verification history: {e}")
        return {
            "verifications": [],
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "error": "Failed to retrieve verification history",
        }
