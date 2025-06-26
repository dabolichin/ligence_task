from fastapi import APIRouter, Depends

from ..core.dependencies import get_verification_history_service
from ..schemas.verification import (
    VerificationHistoryResponse,
    VerificationsByModificationResponse,
    VerificationStatisticsResponse,
    VerificationStatusResponse,
)
from ..services.verification_history import VerificationHistoryService

router = APIRouter()


@router.get("/verification/{verification_id}/status")
async def get_verification_status(
    verification_id: str,
    verification_history_service: VerificationHistoryService = Depends(
        get_verification_history_service
    ),
) -> VerificationStatusResponse:
    """Get verification status for a specific verification ID."""
    return await verification_history_service.get_verification_status(verification_id)


@router.get("/verification/statistics")
async def get_verification_statistics(
    verification_history_service: VerificationHistoryService = Depends(
        get_verification_history_service
    ),
) -> VerificationStatisticsResponse:
    """Get overall verification metrics and statistics."""
    return await verification_history_service.get_verification_statistics()


@router.get("/verification/history")
async def get_verification_history(
    limit: int = 50,
    offset: int = 0,
    verification_history_service: VerificationHistoryService = Depends(
        get_verification_history_service
    ),
) -> VerificationHistoryResponse:
    """Get verification audit trail and history."""
    return await verification_history_service.get_verification_history(
        limit=limit, offset=offset
    )


@router.get("/verification/modifications/{modification_id}")
async def get_verifications_by_modification(
    modification_id: str,
    verification_history_service: VerificationHistoryService = Depends(
        get_verification_history_service
    ),
) -> VerificationsByModificationResponse:
    """Get all verifications for a specific modification ID."""
    return await verification_history_service.get_verifications_by_modification_id(
        modification_id
    )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "verification"}
