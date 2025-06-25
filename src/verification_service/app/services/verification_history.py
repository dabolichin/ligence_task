from uuid import UUID

from loguru import logger

from ..models.verification_result import VerificationResult, VerificationStatus
from ..schemas.verification import (
    VerificationHistoryItem,
    VerificationHistoryResponse,
    VerificationsByModificationResponse,
    VerificationStatisticsResponse,
    VerificationStatusResponse,
)


class VerificationHistoryService:
    async def get_verification_status(
        self, verification_id: str
    ) -> VerificationStatusResponse:
        logger.info(f"Getting verification status for ID: {verification_id}")

        try:
            modification_id = UUID(verification_id)

            verification_result = await VerificationResult.filter(
                modification_id=modification_id
            ).first()

            if not verification_result:
                return VerificationStatusResponse(
                    verification_id=verification_id,
                    status="not_found",
                    message=f"No verification found for ID {verification_id}",
                )

            return VerificationStatusResponse(
                verification_id=verification_id,
                status=verification_result.status.value,
                is_reversible=verification_result.is_reversible,
                verified_with_hash=verification_result.verified_with_hash,
                verified_with_pixels=verification_result.verified_with_pixels,
                created_at=verification_result.created_at.isoformat()
                if verification_result.created_at
                else None,
                completed_at=verification_result.updated_at.isoformat()
                if verification_result.updated_at
                and verification_result.status == VerificationStatus.COMPLETED
                else None,
            )

        except ValueError:
            return VerificationStatusResponse(
                verification_id=verification_id,
                status="invalid",
                message="Invalid verification ID format",
            )
        except Exception as e:
            logger.error(
                f"Error getting verification status for {verification_id}: {e}"
            )
            return VerificationStatusResponse(
                verification_id=verification_id,
                status="error",
                message="Internal server error",
            )

    async def get_verification_statistics(self) -> VerificationStatisticsResponse:
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

            return VerificationStatisticsResponse(
                total_verifications=total_verifications,
                successful_verifications=successful_verifications,
                failed_verifications=failed_verifications,
                pending_verifications=pending_verifications,
                success_rate=round(success_rate, 2),
            )

        except Exception as e:
            logger.error(f"Error getting verification statistics: {e}")
            return VerificationStatisticsResponse(
                total_verifications=0,
                successful_verifications=0,
                failed_verifications=0,
                pending_verifications=0,
                success_rate=0.0,
                error="Failed to retrieve statistics",
            )

    async def get_verification_history(
        self, limit: int = 50, offset: int = 0
    ) -> VerificationHistoryResponse:
        logger.info(f"Getting verification history with limit={limit}, offset={offset}")

        try:
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
                    VerificationHistoryItem(
                        modification_id=str(result.modification_id),
                        status=result.status.value,
                        is_reversible=result.is_reversible,
                        verified_with_hash=result.verified_with_hash,
                        verified_with_pixels=result.verified_with_pixels,
                        created_at=result.created_at.isoformat()
                        if result.created_at
                        else None,
                        completed_at=result.updated_at.isoformat()
                        if result.updated_at
                        and result.status == VerificationStatus.COMPLETED
                        else None,
                    )
                )

            return VerificationHistoryResponse(
                verifications=verifications,
                total_count=total_count,
                limit=limit,
                offset=offset,
            )

        except Exception as e:
            logger.error(f"Error getting verification history: {e}")
            return VerificationHistoryResponse(
                verifications=[],
                total_count=0,
                limit=limit,
                offset=offset,
                error="Failed to retrieve verification history",
            )

    async def get_verifications_by_modification_id(
        self, modification_id: str
    ) -> VerificationsByModificationResponse:
        logger.info(f"Getting all verifications for modification ID: {modification_id}")

        try:
            modification_uuid = UUID(modification_id)

            verification_results = await VerificationResult.filter(
                modification_id=modification_uuid
            ).order_by("-created_at")

            verifications = []
            for result in verification_results:
                verifications.append(
                    VerificationHistoryItem(
                        modification_id=str(result.modification_id),
                        status=result.status.value,
                        is_reversible=result.is_reversible,
                        verified_with_hash=result.verified_with_hash,
                        verified_with_pixels=result.verified_with_pixels,
                        created_at=result.created_at.isoformat()
                        if result.created_at
                        else None,
                        completed_at=result.updated_at.isoformat()
                        if result.updated_at
                        and result.status == VerificationStatus.COMPLETED
                        else None,
                    )
                )

            return VerificationsByModificationResponse(
                modification_id=modification_id,
                verifications=verifications,
                total_count=len(verifications),
            )

        except ValueError:
            return VerificationsByModificationResponse(
                modification_id=modification_id,
                verifications=[],
                total_count=0,
                error="Invalid modification ID format",
            )
        except Exception as e:
            logger.error(
                f"Error getting verifications for modification {modification_id}: {e}"
            )
            return VerificationsByModificationResponse(
                modification_id=modification_id,
                verifications=[],
                total_count=0,
                error="Failed to retrieve verifications for modification",
            )
