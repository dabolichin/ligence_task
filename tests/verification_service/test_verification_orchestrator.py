import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from src.verification_service.app.services.image_comparison import ComparisonResult
from src.verification_service.app.services.verification_orchestrator import (
    VerificationOrchestrator,
)


class TestVerificationOrchestrator:
    @pytest.fixture
    def mock_dependencies(self):
        return {
            "instruction_retrieval_service": AsyncMock(),
            "modification_engine": Mock(),
            "image_reversal_service": AsyncMock(),
            "verification_persistence": AsyncMock(),
        }

    @pytest.fixture
    def verification_service(self, mock_dependencies):
        return VerificationOrchestrator(**mock_dependencies)

    @pytest.mark.asyncio
    async def test_verify_modification_successful_flow(
        self, verification_service, mock_dependencies
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_instruction_data = Mock()
        mock_instruction_data.instructions = {"operations": [], "image_mode": "RGB"}
        mock_instruction_data.algorithm_type = "xor_transform"
        mock_instruction_data.storage_path = "/mock/path/image.jpg"

        mock_dependencies[
            "verification_persistence"
        ].is_already_verified.return_value = False
        mock_dependencies[
            "instruction_retrieval_service"
        ].get_modification_instructions.return_value = mock_instruction_data

        mock_modification_instructions = Mock()
        mock_dependencies[
            "modification_engine"
        ].parse_instruction_data.return_value = mock_modification_instructions

        mock_comparison_result = ComparisonResult(
            hash_match=True,
            pixel_match=True,
            original_hash="hash1",
            reversed_hash="hash1",
            method_used="both",
        )
        mock_dependencies[
            "image_reversal_service"
        ].verify_modification_completely.return_value = mock_comparison_result

        await verification_service.verify_modification(image_id, modification_id)

        mock_dependencies[
            "verification_persistence"
        ].is_already_verified.assert_called_once_with(modification_id)
        mock_dependencies[
            "verification_persistence"
        ].create_verification_record.assert_called_once_with(modification_id)
        mock_dependencies[
            "instruction_retrieval_service"
        ].get_modification_instructions.assert_called_once_with(modification_id)
        mock_dependencies[
            "modification_engine"
        ].parse_instruction_data.assert_called_once_with(mock_instruction_data)
        mock_dependencies[
            "image_reversal_service"
        ].verify_modification_completely.assert_called_once()
        mock_dependencies[
            "verification_persistence"
        ].save_verification_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_modification_existing_record_skipped(
        self, verification_service, mock_dependencies
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_dependencies[
            "verification_persistence"
        ].is_already_verified.return_value = True

        await verification_service.verify_modification(image_id, modification_id)

        mock_dependencies[
            "verification_persistence"
        ].is_already_verified.assert_called_once_with(modification_id)
        mock_dependencies[
            "verification_persistence"
        ].create_verification_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_modification_error_handling(
        self, verification_service, mock_dependencies
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_dependencies[
            "verification_persistence"
        ].is_already_verified.return_value = False
        mock_dependencies[
            "instruction_retrieval_service"
        ].get_modification_instructions.side_effect = Exception(
            "Failed to retrieve instructions"
        )

        await verification_service.verify_modification(image_id, modification_id)

        mock_dependencies[
            "verification_persistence"
        ].is_already_verified.assert_called_once_with(modification_id)
        mock_dependencies[
            "verification_persistence"
        ].create_verification_record.assert_called_once_with(modification_id)
        mock_dependencies[
            "verification_persistence"
        ].save_verification_result.assert_called_once()


class TestVerificationOrchestratorIntegration:
    @pytest.mark.asyncio
    async def test_error_handling_saves_failed_state(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_instruction_retrieval = AsyncMock()
        mock_instruction_retrieval.get_modification_instructions.side_effect = (
            RuntimeError("Service unavailable")
        )

        service = VerificationOrchestrator(
            instruction_retrieval_service=mock_instruction_retrieval,
            modification_engine=Mock(),
            image_reversal_service=AsyncMock(),
            verification_persistence=AsyncMock(),
        )

        mock_verification_persistence = AsyncMock()
        service.verification_persistence = mock_verification_persistence
        mock_verification_persistence.is_already_verified.return_value = False

        await service.verify_modification(image_id, modification_id)

        mock_verification_persistence.is_already_verified.assert_called_once_with(
            modification_id
        )
        mock_verification_persistence.create_verification_record.assert_called_once_with(
            modification_id
        )
        mock_verification_persistence.save_verification_result.assert_called_once()
