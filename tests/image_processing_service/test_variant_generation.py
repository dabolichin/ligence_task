import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.image_processing_service.app.services.variant_generation import (
    VariantGenerationService,
)


@pytest.fixture
def temp_storage_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_settings(temp_storage_dir):
    settings = MagicMock()
    settings.absolute_original_images_dir = str(Path(temp_storage_dir) / "original")
    settings.absolute_modified_images_dir = str(Path(temp_storage_dir) / "modified")
    settings.absolute_temp_dir = str(Path(temp_storage_dir) / "temp")
    settings.ALLOWED_IMAGE_FORMATS = ["jpeg", "png", "bmp"]
    settings.MAX_FILE_SIZE = 100 * 1024 * 1024
    settings.VARIANTS_COUNT = 100
    settings.MIN_MODIFICATIONS_PER_VARIANT = 100
    return settings


@pytest.fixture
def mock_image_record():
    record = MagicMock()
    record.id = str(uuid.uuid4())
    record.format = "JPEG"
    return record


@pytest.fixture
def sample_image():
    return Image.new("RGB", (100, 100), color="red")


@pytest.fixture
def small_sample_image():
    return Image.new("RGB", (10, 10), color="blue")


@pytest.fixture
def variant_service(mock_settings):
    with patch(
        "src.image_processing_service.app.services.variant_generation.get_settings",
        return_value=mock_settings,
    ):
        return VariantGenerationService()


class TestGenerateVariants:
    @pytest.mark.asyncio
    async def test_generate_exactly_100_variants(
        self, variant_service, sample_image, mock_image_record
    ):
        with (
            patch.object(
                variant_service.file_storage, "save_variant_image"
            ) as mock_save,
            patch(
                "src.image_processing_service.app.services.variant_generation.Modification.create"
            ) as mock_create,
        ):
            mock_save.return_value = "/path/to/variant.jpg"
            mock_modification = MagicMock()
            mock_modification.id = str(uuid.uuid4())
            mock_create.return_value = mock_modification

            variants = await variant_service.generate_variants(
                sample_image, mock_image_record
            )

            assert len(variants) == 100

            variant_numbers = [v["variant_number"] for v in variants]
            assert len(set(variant_numbers)) == 100  # All unique
            assert min(variant_numbers) == 1
            assert max(variant_numbers) == 100

            assert mock_save.call_count == 100

            assert mock_create.call_count == 100

    @pytest.mark.asyncio
    async def test_generate_variants_with_small_image(
        self, variant_service, small_sample_image, mock_image_record
    ):
        with (
            patch.object(
                variant_service.file_storage, "save_variant_image"
            ) as mock_save,
            patch(
                "src.image_processing_service.app.services.variant_generation.Modification.create"
            ) as mock_create,
        ):
            mock_save.return_value = "/path/to/variant.jpg"
            mock_modification = MagicMock()
            mock_modification.id = str(uuid.uuid4())
            mock_create.return_value = mock_modification

            variants = await variant_service.generate_variants(
                small_sample_image, mock_image_record
            )

            assert len(variants) == 100

            for variant in variants:
                assert variant["num_modifications"] >= 1

    @pytest.mark.asyncio
    async def test_generate_variants_input_validation(self, variant_service):
        mock_image_record = MagicMock()

        with pytest.raises(ValueError, match="Original image cannot be None"):
            await variant_service.generate_variants(None, mock_image_record)

        sample_image = Image.new("RGB", (10, 10), color="red")
        with pytest.raises(ValueError, match="Image record cannot be None"):
            await variant_service.generate_variants(sample_image, None)

    @pytest.mark.asyncio
    async def test_variant_structure(
        self, variant_service, sample_image, mock_image_record
    ):
        with (
            patch.object(
                variant_service.file_storage, "save_variant_image"
            ) as mock_save,
            patch(
                "src.image_processing_service.app.services.variant_generation.Modification.create"
            ) as mock_create,
        ):
            mock_save.return_value = "/path/to/variant.jpg"
            mock_modification = MagicMock()
            mock_modification.id = str(uuid.uuid4())
            mock_create.return_value = mock_modification

            variants = await variant_service.generate_variants(
                sample_image, mock_image_record
            )

            variant = variants[0]
            required_keys = [
                "variant_number",
                "storage_path",
                "modification_id",
                "num_modifications",
                "algorithm_type",
            ]

            for key in required_keys:
                assert key in variant

            assert variant["algorithm_type"] == "xor_transform"
            assert isinstance(variant["variant_number"], int)
            assert isinstance(variant["num_modifications"], int)
            assert variant["num_modifications"] >= 100

    @pytest.mark.asyncio
    async def test_cleanup_on_failure(
        self, variant_service, sample_image, mock_image_record
    ):
        with (
            patch.object(
                variant_service.file_storage, "save_variant_image"
            ) as mock_save,
            patch.object(
                variant_service.file_storage, "delete_image_and_variants"
            ) as mock_cleanup,
            patch(
                "src.image_processing_service.app.services.variant_generation.Modification.filter"
            ) as mock_filter,
        ):
            mock_save.side_effect = [
                "/path/to/variant1.jpg",
                "/path/to/variant2.jpg",
                Exception("Storage failed"),
            ]

            mock_delete = MagicMock()
            mock_filter.return_value = mock_delete

            with pytest.raises(IOError, match="Failed to generate variants"):
                await variant_service.generate_variants(sample_image, mock_image_record)

            mock_cleanup.assert_called_once()
            mock_delete.delete.assert_called_once()


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_very_small_image(self, variant_service, mock_image_record):
        tiny_image = Image.new("RGB", (1, 1), color="white")

        with (
            patch.object(
                variant_service.file_storage, "save_variant_image"
            ) as mock_save,
            patch(
                "src.image_processing_service.app.services.variant_generation.Modification.create"
            ) as mock_create,
        ):
            mock_save.return_value = "/path/to/variant.jpg"
            mock_modification = MagicMock()
            mock_modification.id = str(uuid.uuid4())
            mock_create.return_value = mock_modification

            variants = await variant_service.generate_variants(
                tiny_image, mock_image_record
            )

            assert len(variants) == 100

            # All variants should have at least 1 modification
            # For 1x1 RGB image (3 total pixels), modifications should be 1-3
            for variant in variants:
                assert variant["num_modifications"] >= 1
                assert variant["num_modifications"] <= 3  # 1x1x3 RGB channels max

    @pytest.mark.asyncio
    async def test_grayscale_image(self, variant_service, mock_image_record):
        gray_image = Image.new("L", (50, 50), color=128)

        with (
            patch.object(
                variant_service.file_storage, "save_variant_image"
            ) as mock_save,
            patch(
                "src.image_processing_service.app.services.variant_generation.Modification.create"
            ) as mock_create,
        ):
            mock_save.return_value = "/path/to/variant.jpg"
            mock_modification = MagicMock()
            mock_modification.id = str(uuid.uuid4())
            mock_create.return_value = mock_modification

            variants = await variant_service.generate_variants(
                gray_image, mock_image_record
            )

            assert len(variants) == 100
            for variant in variants:
                assert 100 <= variant["num_modifications"] <= 50 * 50 * 1
