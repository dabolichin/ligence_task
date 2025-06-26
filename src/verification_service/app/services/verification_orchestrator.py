import uuid

from loguru import logger

from ..core.config import Settings
from .domain import VerificationOutcome
from .image_reversal import ImageReversalService
from .instruction_retrieval import InstructionRetrievalService
from .verification_persistence import VerificationPersistence


class VerificationOrchestrator:
    def __init__(
        self,
        instruction_retrieval_service: InstructionRetrievalService | None = None,
        modification_engine=None,
        image_reversal_service: ImageReversalService | None = None,
        verification_persistence: VerificationPersistence | None = None,
        settings: Settings = None,
    ):
        from ..core.config import get_settings

        self.settings = settings or get_settings()

        if instruction_retrieval_service is None:
            raise ValueError(
                "InstructionRetrievalService must be provided via dependency injection"
            )

        if modification_engine is None:
            raise ValueError(
                "ModificationEngine must be provided via dependency injection"
            )
        if image_reversal_service is None:
            raise ValueError(
                "ImageReversalService must be provided via dependency injection"
            )
        if verification_persistence is None:
            raise ValueError(
                "VerificationPersistence must be provided via dependency injection"
            )

        self.instruction_retrieval_service = instruction_retrieval_service

        self.modification_engine = modification_engine
        self.image_reversal_service = image_reversal_service
        self.verification_persistence = verification_persistence

    async def verify_modification(
        self, image_id: uuid.UUID, modification_id: uuid.UUID
    ) -> None:
        logger.info(
            f"Starting verification for modification {modification_id} (image {image_id})"
        )

        try:
            if await self.verification_persistence.is_already_verified(modification_id):
                return

            await self.verification_persistence.create_verification_record(
                modification_id
            )

            verification_result = await self._execute_verification(modification_id)

            await self.verification_persistence.save_verification_result(
                modification_id, verification_result
            )

            logger.info(
                f"Successfully completed verification for modification {modification_id}"
            )

        except Exception as e:
            logger.error(
                f"Error verifying modification {modification_id}: {e}",
                exc_info=True,
            )
            await self.verification_persistence.mark_verification_failed(
                modification_id
            )

    async def execute_verification_background(
        self, image_id: uuid.UUID, modification_id: uuid.UUID
    ) -> None:
        logger.info(
            f"Starting background verification for modification {modification_id} (image {image_id})"
        )

        try:
            verification_result = await self._execute_verification(modification_id)

            await self.verification_persistence.save_verification_result(
                modification_id, verification_result
            )

            logger.info(
                f"Successfully completed verification for modification {modification_id}"
            )

        except Exception as e:
            logger.error(
                f"Error in background verification for modification {modification_id}: {e}",
                exc_info=True,
            )
            await self.verification_persistence.mark_verification_failed(
                modification_id
            )

    async def _execute_verification(
        self, modification_id: uuid.UUID
    ) -> "VerificationOutcome":
        logger.info(f"Executing verification for modification {modification_id}")

        try:
            instruction_data = await self._retrieve_instructions(modification_id)
            modification_instructions = self._parse_instructions(instruction_data)

            comparison_result = (
                await self.image_reversal_service.verify_modification_completely(
                    instruction_data,
                    modification_instructions,
                    self.modification_engine,
                )
            )
            is_fully_reversible = comparison_result.pixel_match is True

            return VerificationOutcome(
                is_reversible=is_fully_reversible,
                verified_with_hash=comparison_result.hash_match or False,
                verified_with_pixels=comparison_result.pixel_match or False,
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
        return self.modification_engine.parse_instruction_data(instruction_data)
