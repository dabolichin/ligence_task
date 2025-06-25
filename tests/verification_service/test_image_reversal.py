import uuid
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from src.verification_service.app.services.domain import (
    ComparisonMethod,
    ComparisonResult,
)
from src.verification_service.app.services.image_reversal import ImageReversalService


@pytest.fixture
def mock_comparison_service():
    """Mock image comparison service."""
    mock_service = Mock()
    mock_service.compare_images.return_value = ComparisonResult(
        hash_match=True,
        pixel_match=True,
        original_hash="hash1",
        reversed_hash="hash1",
        method_used="both",
    )
    return mock_service


@pytest.fixture
def image_reversal_service(mock_comparison_service):
    return ImageReversalService(mock_comparison_service)


@pytest.fixture
def mock_instruction_data():
    mock_data = Mock()
    mock_data.modification_id = uuid.uuid4()
    mock_data.image_id = uuid.uuid4()
    mock_data.original_filename = "original.png"
    mock_data.storage_path = "/mock/path/modified.png"
    mock_data.instructions = {
        "original_image_path": "/mock/path/original.png",
        "operations": [],
        "image_mode": "RGB",
    }
    return mock_data


class TestImageReversalService:
    async def test_reverse_image_modifications_success(
        self, image_reversal_service, mock_instruction_data, sample_image_rgb
    ):
        mock_engine = Mock()
        mock_engine.reverse_modifications.return_value = sample_image_rgb

        with patch("PIL.Image.open") as mock_open:
            mock_open.return_value = sample_image_rgb

            result = await image_reversal_service.reverse_image_modifications(
                mock_instruction_data, [], mock_engine
            )

            assert isinstance(result, Image.Image)
            mock_open.assert_called_once_with(mock_instruction_data.storage_path)
            mock_engine.reverse_modifications.assert_called_once_with(
                sample_image_rgb, []
            )

    async def test_verify_reversibility_success(
        self, image_reversal_service, mock_instruction_data, sample_image_rgb, tmp_path
    ):
        original_path = tmp_path / "original.png"
        sample_image_rgb.save(original_path)
        mock_instruction_data.instructions["original_image_path"] = str(original_path)

        image_reversal_service.image_comparison_service.compare_images.return_value = (
            ComparisonResult(
                hash_match=True,
                pixel_match=True,
                original_hash="hash1",
                reversed_hash="hash1",
                method_used="both",
            )
        )

        result = await image_reversal_service.verify_reversibility(
            sample_image_rgb, mock_instruction_data
        )

        assert result.hash_match is True
        assert result.pixel_match is True
        assert result.method_used == "both"

        call_args = (
            image_reversal_service.image_comparison_service.compare_images.call_args
        )
        assert call_args.kwargs.get("method") == ComparisonMethod.BOTH

    async def test_verify_reversibility_handles_comparison_errors(
        self, image_reversal_service, mock_instruction_data, sample_image_rgb
    ):
        mock_instruction_data.instructions["original_image_path"] = (
            "/non/existent/path.png"
        )

        image_reversal_service.image_comparison_service.compare_images.side_effect = (
            FileNotFoundError("Original image not found")
        )

        result = await image_reversal_service.verify_reversibility(
            sample_image_rgb, mock_instruction_data
        )

        assert result.hash_match is False
        assert result.pixel_match is False
        assert result.method_used == "both"

    async def test_verify_modification_completely_success(
        self, image_reversal_service, mock_instruction_data, sample_image_rgb, tmp_path
    ):
        original_path = tmp_path / "original.png"
        sample_image_rgb.save(original_path)
        mock_instruction_data.instructions["original_image_path"] = str(original_path)

        mock_engine = Mock()
        mock_engine.reverse_modifications.return_value = sample_image_rgb

        with patch("PIL.Image.open") as mock_open:
            mock_open.return_value = sample_image_rgb

            result = await image_reversal_service.verify_modification_completely(
                mock_instruction_data, [], mock_engine
            )

            assert result.hash_match is True
            assert result.pixel_match is True

    async def test_verify_modification_completely_error(
        self, image_reversal_service, mock_instruction_data
    ):
        mock_engine = Mock()

        with patch("PIL.Image.open") as mock_open:
            mock_open.side_effect = Exception("Failed to load image")

            result = await image_reversal_service.verify_modification_completely(
                mock_instruction_data, [], mock_engine
            )

            assert result.hash_match is False
            assert result.pixel_match is False

    async def test_verify_reversibility_cleanup_on_temp_file_creation_error(
        self, image_reversal_service, mock_instruction_data, sample_image_rgb
    ):
        with patch.object(image_reversal_service, "_save_temporary_image") as mock_save:
            mock_save.side_effect = Exception("Failed to create temp file")

            result = await image_reversal_service.verify_reversibility(
                sample_image_rgb, mock_instruction_data
            )

            assert result.hash_match is False
            assert result.pixel_match is False

    async def test_verify_reversibility_cleanup_called_on_success(
        self, image_reversal_service, mock_instruction_data, sample_image_rgb, tmp_path
    ):
        original_path = tmp_path / "original.png"
        sample_image_rgb.save(original_path)
        mock_instruction_data.instructions["original_image_path"] = str(original_path)

        with patch.object(
            image_reversal_service, "_cleanup_temporary_file"
        ) as mock_cleanup:
            await image_reversal_service.verify_reversibility(
                sample_image_rgb, mock_instruction_data
            )

            mock_cleanup.assert_called_once()
