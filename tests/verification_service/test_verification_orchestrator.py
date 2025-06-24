import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.verification_service.app.models.verification_result import (
    VerificationResult,
    VerificationStatus,
)
from src.verification_service.app.services.verification_orchestrator import (
    VerificationOrchestrator,
    VerificationOutcome,
)


class TestVerificationOrchestratorInitialization:
    def test_service_initialization_with_dependencies(self):
        mock_instruction_retrieval = Mock()
        mock_instruction_parser = Mock()
        mock_modification_engine = Mock()

        service = VerificationOrchestrator(
            instruction_retrieval_service=mock_instruction_retrieval,
            instruction_parser=mock_instruction_parser,
            modification_engine=mock_modification_engine,
        )

        assert service.instruction_retrieval_service == mock_instruction_retrieval
        assert service.instruction_parser == mock_instruction_parser
        assert service.modification_engine == mock_modification_engine


class TestVerificationOrchestratorStartVerification:
    @pytest.fixture
    def mock_dependencies(self):
        return {
            "instruction_retrieval_service": AsyncMock(),
            "instruction_parser": Mock(),
            "modification_engine": Mock(),
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
        mock_instruction_data.instructions = {"operations": []}
        mock_instruction_data.algorithm_type = "xor_transform"
        mock_instruction_data.storage_path = "/mock/path/image.jpg"

        mock_dependencies[
            "instruction_retrieval_service"
        ].get_modification_instructions.return_value = mock_instruction_data

        mock_modification_instructions = Mock()
        mock_dependencies[
            "instruction_parser"
        ].parse_instructions.return_value = mock_modification_instructions

        mock_reversed_image = Mock()
        mock_dependencies[
            "modification_engine"
        ].reverse_modifications.return_value = mock_reversed_image

        mock_verification_record = AsyncMock()
        mock_verification_record.status = VerificationStatus.PENDING
        mock_verification_record.save = AsyncMock()

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(
                side_effect=[None, mock_verification_record]
            )

            with patch.object(
                VerificationResult, "create", return_value=mock_verification_record
            ) as mock_create:
                with patch("PIL.Image.open") as mock_image_open:
                    mock_image = Mock()
                    mock_image_open.return_value = mock_image

                    await verification_service.verify_modification(
                        image_id, modification_id
                    )

                    mock_create.assert_called_once_with(
                        modification_id=modification_id,
                        status=VerificationStatus.PENDING,
                    )

                    mock_dependencies[
                        "instruction_retrieval_service"
                    ].get_modification_instructions.assert_called_once_with(
                        modification_id
                    )

                    mock_dependencies[
                        "instruction_parser"
                    ].parse_instructions.assert_called_once_with(
                        mock_instruction_data.instructions,
                        mock_instruction_data.algorithm_type,
                    )

                    mock_image_open.assert_called_once_with(
                        mock_instruction_data.storage_path
                    )
                    mock_dependencies[
                        "modification_engine"
                    ].reverse_modifications.assert_called_once_with(
                        mock_image, mock_modification_instructions
                    )

                    assert (
                        mock_verification_record.status == VerificationStatus.COMPLETED
                    )
                    assert mock_verification_record.is_reversible is True
                    assert mock_verification_record.verified_with_hash is True
                    assert mock_verification_record.verified_with_pixels is True
                    mock_verification_record.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_modification_existing_record_skipped(
        self, verification_service, mock_dependencies
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        existing_record = Mock()
        existing_record.modification_id = modification_id

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(return_value=existing_record)

            with patch.object(VerificationResult, "create") as mock_create:
                await verification_service.verify_modification(
                    image_id, modification_id
                )

                mock_create.assert_not_called()

                mock_dependencies[
                    "instruction_retrieval_service"
                ].get_modification_instructions.assert_not_called()
                mock_dependencies[
                    "instruction_parser"
                ].parse_instructions.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_modification_instruction_retrieval_error(
        self, verification_service, mock_dependencies
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_dependencies[
            "instruction_retrieval_service"
        ].get_modification_instructions.side_effect = Exception(
            "Failed to retrieve instructions"
        )

        mock_verification_record = AsyncMock()
        mock_verification_record.status = VerificationStatus.PENDING
        mock_verification_record.save = AsyncMock()

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(
                side_effect=[None, mock_verification_record]
            )

            with patch.object(
                VerificationResult, "create", return_value=mock_verification_record
            ):
                await verification_service.verify_modification(
                    image_id, modification_id
                )

                # Should mark verification as failed
                assert mock_verification_record.status == VerificationStatus.COMPLETED
                assert mock_verification_record.is_reversible is False
                assert mock_verification_record.verified_with_hash is False
                assert mock_verification_record.verified_with_pixels is False
                mock_verification_record.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_modification_instruction_parsing_error(
        self, verification_service, mock_dependencies
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_instruction_data = Mock()
        mock_instruction_data.instructions = {"operations": []}
        mock_instruction_data.algorithm_type = "xor_transform"
        mock_instruction_data.storage_path = "/mock/path/image.jpg"

        mock_dependencies[
            "instruction_retrieval_service"
        ].get_modification_instructions.return_value = mock_instruction_data

        mock_dependencies[
            "instruction_parser"
        ].parse_instructions.side_effect = Exception("Failed to parse instructions")

        mock_verification_record = AsyncMock()
        mock_verification_record.status = VerificationStatus.PENDING
        mock_verification_record.save = AsyncMock()

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(
                side_effect=[None, mock_verification_record]
            )

            with patch.object(
                VerificationResult, "create", return_value=mock_verification_record
            ):
                await verification_service.verify_modification(
                    image_id, modification_id
                )

                assert mock_verification_record.status == VerificationStatus.COMPLETED
                assert mock_verification_record.is_reversible is False
                mock_verification_record.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_modification_image_loading_error(
        self, verification_service, mock_dependencies
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        # Mock instruction data
        mock_instruction_data = Mock()
        mock_instruction_data.instructions = {"operations": []}
        mock_instruction_data.algorithm_type = "xor_transform"
        mock_instruction_data.storage_path = "/invalid/path/image.jpg"

        mock_dependencies[
            "instruction_retrieval_service"
        ].get_modification_instructions.return_value = mock_instruction_data

        mock_modification_instructions = Mock()
        mock_dependencies[
            "instruction_parser"
        ].parse_instructions.return_value = mock_modification_instructions

        # Mock image loading failure
        with patch("PIL.Image.open") as mock_image_open:
            mock_image_open.side_effect = Exception("Cannot load image")

            mock_verification_record = AsyncMock()
            mock_verification_record.status = VerificationStatus.PENDING
            mock_verification_record.save = AsyncMock()

            with patch.object(VerificationResult, "filter") as mock_filter:
                mock_filter.return_value.first = AsyncMock(
                    side_effect=[None, mock_verification_record]
                )

                with patch.object(
                    VerificationResult, "create", return_value=mock_verification_record
                ):
                    await verification_service.verify_modification(
                        image_id, modification_id
                    )

                    # Should mark verification as failed
                    assert (
                        mock_verification_record.status == VerificationStatus.COMPLETED
                    )
                    assert mock_verification_record.is_reversible is False
                    mock_verification_record.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_modification_reverse_modification_error(
        self, verification_service, mock_dependencies
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_instruction_data = Mock()
        mock_instruction_data.instructions = {"operations": []}
        mock_instruction_data.algorithm_type = "xor_transform"
        mock_instruction_data.storage_path = "/mock/path/image.jpg"

        mock_dependencies[
            "instruction_retrieval_service"
        ].get_modification_instructions.return_value = mock_instruction_data

        mock_modification_instructions = Mock()
        mock_dependencies[
            "instruction_parser"
        ].parse_instructions.return_value = mock_modification_instructions

        mock_dependencies[
            "modification_engine"
        ].reverse_modifications.side_effect = Exception(
            "Failed to reverse modifications"
        )

        mock_verification_record = AsyncMock()
        mock_verification_record.status = VerificationStatus.PENDING
        mock_verification_record.save = AsyncMock()

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(
                side_effect=[None, mock_verification_record]
            )

            with patch.object(
                VerificationResult, "create", return_value=mock_verification_record
            ):
                with patch("PIL.Image.open") as mock_image_open:
                    mock_image = Mock()
                    mock_image_open.return_value = mock_image

                    await verification_service.verify_modification(
                        image_id, modification_id
                    )

                    # Should mark verification as failed
                    assert (
                        mock_verification_record.status == VerificationStatus.COMPLETED
                    )
                    assert mock_verification_record.is_reversible is False
                    mock_verification_record.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_modification_database_save_error(
        self, verification_service, mock_dependencies
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_verification_record = AsyncMock()
        mock_verification_record.status = VerificationStatus.PENDING
        mock_verification_record.save = AsyncMock(
            side_effect=Exception("Database save failed")
        )

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(
                side_effect=[None, mock_verification_record]
            )

            with patch.object(
                VerificationResult, "create", return_value=mock_verification_record
            ):
                # Should handle the exception gracefully
                await verification_service.verify_modification(
                    image_id, modification_id
                )

    @pytest.mark.asyncio
    async def test_verify_modification_create_record_error_handling(
        self, verification_service, mock_dependencies
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(return_value=None)

            with patch.object(VerificationResult, "create") as mock_create:
                mock_create.side_effect = Exception("Failed to create record")

                # Should handle the exception gracefully
                await verification_service.verify_modification(
                    image_id, modification_id
                )

                mock_create.assert_called_once()


class TestVerificationOrchestratorPerformVerification:
    @pytest.fixture
    def mock_dependencies(self):
        return {
            "instruction_retrieval_service": AsyncMock(),
            "instruction_parser": Mock(),
            "modification_engine": Mock(),
        }

    @pytest.fixture
    def verification_service(self, mock_dependencies):
        return VerificationOrchestrator(**mock_dependencies)

    @pytest.mark.asyncio
    async def test_execute_verification_success(
        self, verification_service, mock_dependencies
    ):
        modification_id = uuid.uuid4()

        mock_instruction_data = Mock()
        mock_instruction_data.instructions = {"operations": []}
        mock_instruction_data.algorithm_type = "xor_transform"
        mock_instruction_data.storage_path = "/mock/path/image.jpg"

        mock_dependencies[
            "instruction_retrieval_service"
        ].get_modification_instructions.return_value = mock_instruction_data

        mock_modification_instructions = Mock()
        mock_dependencies[
            "instruction_parser"
        ].parse_instructions.return_value = mock_modification_instructions

        mock_reversed_image = Mock()
        mock_dependencies[
            "modification_engine"
        ].reverse_modifications.return_value = mock_reversed_image

        with patch("PIL.Image.open") as mock_image_open:
            mock_image = Mock()
            mock_image_open.return_value = mock_image

            result = await verification_service._execute_verification(modification_id)

            assert isinstance(result, VerificationOutcome)
            assert result.is_reversible is True
            assert result.verified_with_hash is True
            assert result.verified_with_pixels is True

    @pytest.mark.asyncio
    async def test_execute_verification_failure(
        self, verification_service, mock_dependencies
    ):
        modification_id = uuid.uuid4()

        mock_dependencies[
            "instruction_retrieval_service"
        ].get_modification_instructions.side_effect = Exception("Retrieval failed")

        result = await verification_service._execute_verification(modification_id)

        assert isinstance(result, VerificationOutcome)
        assert result.is_reversible is False
        assert result.verified_with_hash is False
        assert result.verified_with_pixels is False


class TestVerificationOutcome:
    def test_verification_outcome_initialization(self):
        result = VerificationOutcome(
            is_reversible=True, verified_with_hash=True, verified_with_pixels=False
        )

        assert result.is_reversible is True
        assert result.verified_with_hash is True
        assert result.verified_with_pixels is False

    def test_verification_outcome_all_false(self):
        result = VerificationOutcome(
            is_reversible=False, verified_with_hash=False, verified_with_pixels=False
        )

        assert result.is_reversible is False
        assert result.verified_with_hash is False
        assert result.verified_with_pixels is False


class TestVerificationOrchestratorIntegration:
    @pytest.mark.asyncio
    async def test_complete_verification_workflow_mock_dependencies(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_instruction_retrieval = AsyncMock()
        mock_instruction_parser = Mock()
        mock_modification_engine = Mock()

        service = VerificationOrchestrator(
            instruction_retrieval_service=mock_instruction_retrieval,
            instruction_parser=mock_instruction_parser,
            modification_engine=mock_modification_engine,
        )

        mock_instruction_data = Mock()
        mock_instruction_data.instructions = {"operations": [{"type": "xor"}]}
        mock_instruction_data.algorithm_type = "xor_transform"
        mock_instruction_data.storage_path = "/test/image.jpg"

        mock_instruction_retrieval.get_modification_instructions.return_value = (
            mock_instruction_data
        )

        mock_instructions = Mock()
        mock_instruction_parser.parse_instructions.return_value = mock_instructions

        mock_reversed_image = Mock()
        mock_modification_engine.reverse_modifications.return_value = (
            mock_reversed_image
        )

        mock_verification_record = AsyncMock()
        mock_verification_record.status = VerificationStatus.PENDING
        mock_verification_record.save = AsyncMock()

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(
                side_effect=[None, mock_verification_record]
            )

            with patch.object(
                VerificationResult, "create", return_value=mock_verification_record
            ):
                with patch("PIL.Image.open") as mock_image_open:
                    mock_image = Mock()
                    mock_image_open.return_value = mock_image

                    await service.verify_modification(image_id, modification_id)

                    mock_instruction_retrieval.get_modification_instructions.assert_called_once_with(
                        modification_id
                    )
                    mock_instruction_parser.parse_instructions.assert_called_once_with(
                        mock_instruction_data.instructions,
                        mock_instruction_data.algorithm_type,
                    )
                    mock_image_open.assert_called_once_with(
                        mock_instruction_data.storage_path
                    )
                    mock_modification_engine.reverse_modifications.assert_called_once_with(
                        mock_image, mock_instructions
                    )

                    # Verify final state
                    assert (
                        mock_verification_record.status == VerificationStatus.COMPLETED
                    )
                    assert mock_verification_record.is_reversible is True
                    mock_verification_record.save.assert_called_once()

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
            instruction_parser=Mock(),
            modification_engine=Mock(),
        )

        mock_verification_record = AsyncMock()
        mock_verification_record.status = VerificationStatus.PENDING
        mock_verification_record.save = AsyncMock()

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first = AsyncMock(
                side_effect=[None, mock_verification_record]
            )

            with patch.object(
                VerificationResult, "create", return_value=mock_verification_record
            ):
                await service.verify_modification(image_id, modification_id)

                assert mock_verification_record.status == VerificationStatus.COMPLETED
                assert mock_verification_record.is_reversible is False
                assert mock_verification_record.verified_with_hash is False
                assert mock_verification_record.verified_with_pixels is False
                mock_verification_record.save.assert_called_once()
