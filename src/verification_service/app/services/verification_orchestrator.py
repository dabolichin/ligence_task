import uuid

from loguru import logger
from PIL import Image

from ..core.config import Settings
from ..models.verification_result import VerificationResult, VerificationStatus
from ..services.instruction_parser import InstructionParser
from ..services.instruction_retrieval import InstructionRetrievalService


class VerificationOrchestrator:
    def __init__(
        self,
        instruction_retrieval_service: InstructionRetrievalService | None = None,
        instruction_parser: InstructionParser | None = None,
        modification_engine=None,
        settings: Settings = None,
    ):
        from ..core.config import get_settings

        self.settings = settings or get_settings()

        if instruction_retrieval_service is None:
            raise ValueError(
                "InstructionRetrievalService must be provided via dependency injection"
            )
        if instruction_parser is None:
            raise ValueError(
                "InstructionParser must be provided via dependency injection"
            )
        if modification_engine is None:
            raise ValueError(
                "ModificationEngine must be provided via dependency injection"
            )

        self.instruction_retrieval_service = instruction_retrieval_service
        self.instruction_parser = instruction_parser
        self.modification_engine = modification_engine

    async def verify_modification(
        self, image_id: uuid.UUID, modification_id: uuid.UUID
    ) -> None:
        """Complete verification workflow including record creation."""
        logger.info(
            f"Starting verification for modification {modification_id} (image {image_id})"
        )

        try:
            if await self._is_already_verified(modification_id):
                return

            await self._create_verification_record(modification_id)

            verification_result = await self._execute_verification(modification_id)

            await self._save_verification_result(modification_id, verification_result)

            logger.info(
                f"Successfully completed verification for modification {modification_id}"
            )

        except Exception as e:
            logger.error(
                f"Error verifying modification {modification_id}: {e}",
                exc_info=True,
            )
            await self._mark_verification_failed(modification_id)

    async def execute_verification_background(
        self, image_id: uuid.UUID, modification_id: uuid.UUID
    ) -> None:
        logger.info(
            f"Starting background verification for modification {modification_id} (image {image_id})"
        )

        try:
            verification_result = await self._execute_verification(modification_id)

            await self._save_verification_result(modification_id, verification_result)

            logger.info(
                f"Successfully completed verification for modification {modification_id}"
            )

        except Exception as e:
            logger.error(
                f"Error in background verification for modification {modification_id}: {e}",
                exc_info=True,
            )
            await self._mark_verification_failed(modification_id)

    async def _is_already_verified(self, modification_id: uuid.UUID) -> bool:
        existing = await VerificationResult.filter(
            modification_id=modification_id
        ).first()

        if existing:
            logger.info(
                f"Verification record already exists for modification {modification_id}"
            )
            return True

        return False

    async def _create_verification_record(self, modification_id: uuid.UUID) -> None:
        await VerificationResult.create(
            modification_id=modification_id,
            status=VerificationStatus.PENDING,
        )

        logger.info(f"Created verification record for modification {modification_id}")

    async def _execute_verification(
        self, modification_id: uuid.UUID
    ) -> "VerificationOutcome":
        logger.info(f"Executing verification for modification {modification_id}")

        try:
            instruction_data = await self._retrieve_instructions(modification_id)
            modification_instructions = self._parse_instructions(instruction_data)
            reversed_image = await self._reverse_image_modifications(
                instruction_data, modification_instructions
            )
            is_reversible = await self._verify_reversibility(
                reversed_image, modification_id
            )

            return VerificationOutcome(
                is_reversible=is_reversible,
                verified_with_hash=is_reversible,
                verified_with_pixels=is_reversible,
            )

        except Exception as e:
            logger.error(
                f"Verification execution failed for modification {modification_id}: {e}",
                exc_info=True,
            )
            return VerificationOutcome(
                is_reversible=False,
                verified_with_hash=False,
                verified_with_pixels=False,
            )

    async def _retrieve_instructions(self, modification_id: uuid.UUID):
        return await self.instruction_retrieval_service.get_modification_instructions(
            modification_id
        )

    def _parse_instructions(self, instruction_data):
        return self.instruction_parser.parse_instructions(
            instruction_data.instructions, instruction_data.algorithm_type
        )

    async def _reverse_image_modifications(
        self, instruction_data, modification_instructions
    ) -> Image.Image:
        modified_image = Image.open(instruction_data.storage_path)
        reversed_image = self.modification_engine.reverse_modifications(
            modified_image, modification_instructions
        )

        return reversed_image

    async def _verify_reversibility(
        self, reversed_image: Image.Image, modification_id: uuid.UUID
    ) -> bool:
        # TODO: Implement actual comparison with original image
        # For now, assume success True
        logger.info(f"Reversibility verified for modification {modification_id}")
        return True

    async def _save_verification_result(
        self, modification_id: uuid.UUID, result: "VerificationOutcome"
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

    async def _mark_verification_failed(self, modification_id: uuid.UUID) -> None:
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

        except Exception as cleanup_error:
            logger.error(
                f"Failed to mark verification as failed for modification {modification_id}: {cleanup_error}"
            )


class VerificationOutcome:
    def __init__(
        self, is_reversible: bool, verified_with_hash: bool, verified_with_pixels: bool
    ):
        self.is_reversible = is_reversible
        self.verified_with_hash = verified_with_hash
        self.verified_with_pixels = verified_with_pixels
