import uuid

from loguru import logger

from ..models.verification_result import VerificationResult, VerificationStatus
from .domain import VerificationOutcome


class VerificationPersistence:
    def __init__(self):
        pass

    async def is_already_verified(self, modification_id: uuid.UUID) -> bool:
        existing = await VerificationResult.filter(
            modification_id=modification_id
        ).first()

        if existing:
            logger.info(
                f"Verification record already exists for modification {modification_id}"
            )
            return True

        return False

    async def create_verification_record(self, modification_id: uuid.UUID) -> None:
        await VerificationResult.create(
            modification_id=modification_id,
            status=VerificationStatus.PENDING,
        )

        logger.info(f"Created verification record for modification {modification_id}")

    async def save_verification_result(
        self, modification_id: uuid.UUID, result: VerificationOutcome
    ) -> None:
        verification_record = await VerificationResult.filter(
            modification_id=modification_id
        ).first()

        if verification_record:
            verification_record.status = VerificationStatus.COMPLETED
            verification_record.is_reversible = result.is_reversible
            verification_record.verified_with_hash = result.verified_with_hash
            verification_record.verified_with_pixels = result.verified_with_pixels
            await verification_record.save()

            logger.info(
                f"Saved verification result for modification {modification_id}: "
                f"reversible={result.is_reversible}"
            )
        else:
            logger.warning(
                f"No verification record found for modification {modification_id}"
            )

    async def mark_verification_failed(self, modification_id: uuid.UUID) -> None:
        try:
            verification_record = await VerificationResult.filter(
                modification_id=modification_id
            ).first()

            if verification_record:
                verification_record.status = VerificationStatus.COMPLETED
                verification_record.is_reversible = False
                verification_record.verified_with_hash = False
                verification_record.verified_with_pixels = False
                await verification_record.save()

                logger.info(
                    f"Marked verification as failed for modification {modification_id}"
                )
            else:
                logger.warning(
                    f"No verification record found to mark as failed for modification {modification_id}"
                )

        except Exception as cleanup_error:
            logger.error(
                f"Failed to mark verification as failed for modification {modification_id}: {cleanup_error}"
            )

    async def get_verification_record(
        self, modification_id: uuid.UUID
    ) -> VerificationResult | None:
        try:
            return await VerificationResult.filter(
                modification_id=modification_id
            ).first()
        except Exception as e:
            logger.error(
                f"Error retrieving verification record for {modification_id}: {e}"
            )
            return None

    async def get_verification_statistics(self) -> dict:
        try:
            total_count = await VerificationResult.all().count()
            completed_count = await VerificationResult.filter(
                status=VerificationStatus.COMPLETED
            ).count()
            pending_count = await VerificationResult.filter(
                status=VerificationStatus.PENDING
            ).count()
            successful_count = await VerificationResult.filter(
                status=VerificationStatus.COMPLETED, is_reversible=True
            ).count()
            failed_count = await VerificationResult.filter(
                status=VerificationStatus.COMPLETED, is_reversible=False
            ).count()

            return {
                "total": total_count,
                "completed": completed_count,
                "pending": pending_count,
                "successful": successful_count,
                "failed": failed_count,
                "success_rate": (
                    (successful_count / completed_count * 100)
                    if completed_count > 0
                    else 0
                ),
            }
        except Exception as e:
            logger.error(f"Error retrieving verification statistics: {e}")
            return {
                "total": 0,
                "completed": 0,
                "pending": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
            }
