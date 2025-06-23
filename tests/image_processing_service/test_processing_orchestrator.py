import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from src.image_processing_service.app.models import Image as ImageModel
from src.image_processing_service.app.models import Modification


@pytest.fixture
def sample_image_data():
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


class TestProcessingOrchestrator:
    @pytest.mark.asyncio
    async def test_start_image_processing_success(
        self, orchestrator, sample_image_data, mock_image_record
    ):
        filename = "test_image.jpg"

        with (
            patch.object(orchestrator.file_storage, "save_original_image") as mock_save,
            patch.object(ImageModel, "create") as mock_create,
            patch.object(orchestrator, "_generate_variants_background") as _,
        ):
            mock_save.return_value = (
                "/fake/path/image.jpg",
                {"file_size": 1024, "width": 100, "height": 100, "format": "JPEG"},
            )

            mock_create.return_value = mock_image_record

            image_id, processing_info = await orchestrator.start_image_processing(
                sample_image_data, filename
            )

            assert uuid.UUID(image_id)
            assert (
                processing_info["message"]
                == "Image upload successful, processing started"
            )
            assert processing_info["original_filename"] == filename
            assert processing_info["file_size"] == 1024

            mock_save.assert_called_once_with(sample_image_data, filename, image_id)
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_image_processing_file_validation_error(
        self, orchestrator, sample_image_data
    ):
        invalid_data = b"not an image"
        filename = "invalid.txt"

        with patch.object(
            orchestrator.file_storage, "save_original_image"
        ) as mock_save:
            mock_save.side_effect = ValueError("Invalid image file")

            with pytest.raises(ValueError, match="Invalid image file"):
                await orchestrator.start_image_processing(invalid_data, filename)

    @pytest.mark.asyncio
    async def test_start_image_processing_io_error(
        self, orchestrator, sample_image_data
    ):
        filename = "test.jpg"

        with (
            patch.object(orchestrator.file_storage, "save_original_image") as mock_save,
            patch.object(
                orchestrator.file_storage, "delete_image_and_variants"
            ) as mock_cleanup,
        ):
            mock_save.side_effect = IOError("Disk full")

            with pytest.raises(IOError, match="Disk full"):
                await orchestrator.start_image_processing(sample_image_data, filename)

            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_processing_completes_after_upload(
        self, orchestrator, sample_image_data, mock_image_record
    ):
        filename = "test_image.jpg"

        with (
            patch.object(orchestrator.file_storage, "save_original_image") as mock_save,
            patch.object(orchestrator.file_storage, "load_image") as mock_load,
            patch.object(ImageModel, "create") as mock_create,
            patch.object(orchestrator.variant_generator, "generate_variants") as _,
            patch.object(orchestrator, "_notify_verification_service") as _,
        ):
            mock_save.return_value = (
                "/fake/path/image.jpg",
                {"file_size": 1024, "width": 100, "height": 100, "format": "JPEG"},
            )
            mock_create.return_value = mock_image_record
            mock_load.return_value = Image.new("RGB", (100, 100), color="red")

            image_id, processing_info = await orchestrator.start_image_processing(
                sample_image_data, filename
            )

            import asyncio

            await asyncio.sleep(0.1)

            assert uuid.UUID(image_id)
            assert (
                processing_info["message"]
                == "Image upload successful, processing started"
            )

            mock_save.assert_called_once()
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "variants_count,expected_status,expected_progress",
        [
            (50, "processing", 50),  # In progress
            (100, "completed", 100),  # Completed
            (0, "processing", 0),  # Just started
        ],
    )
    async def test_get_processing_status(
        self, orchestrator, variants_count, expected_status, expected_progress
    ):
        image_id = str(uuid.uuid4())

        async def mock_get_func(id):
            mock_record = MagicMock()
            mock_record.created_at = "2023-01-01T00:00:00"
            mock_record.updated_at = "2023-01-01T00:01:00"
            return mock_record

        async def mock_count_func():
            return variants_count

        with (
            patch.object(ImageModel, "get", side_effect=mock_get_func) as _,
            patch.object(Modification, "filter") as mock_filter,
        ):
            mock_filter_result = MagicMock()
            mock_filter_result.count = mock_count_func
            mock_filter.return_value = mock_filter_result

            status = await orchestrator.get_processing_status(image_id)

            assert status is not None
            assert status.processing_id == image_id
            assert status.status == expected_status
            assert status.progress == expected_progress
            assert status.variants_completed == variants_count
            assert status.total_variants == 100

    @pytest.mark.asyncio
    async def test_get_processing_status_not_found(self, orchestrator):
        with patch.object(ImageModel, "get") as mock_get:
            from tortoise.exceptions import DoesNotExist

            mock_get.side_effect = DoesNotExist(ImageModel)

            status = await orchestrator.get_processing_status("non-existent")
            assert status is None

    @pytest.mark.asyncio
    async def test_upload_validation_errors(self, orchestrator):
        invalid_data = b"not an image"
        filename = "invalid.jpg"

        with patch.object(
            orchestrator.file_storage, "save_original_image"
        ) as mock_save:
            mock_save.side_effect = ValueError("Invalid image format")

            with pytest.raises(ValueError, match="Invalid image format"):
                await orchestrator.start_image_processing(invalid_data, filename)

            mock_save.assert_called_once_with(
                invalid_data, filename, mock_save.call_args[0][2]
            )

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, orchestrator, sample_image_data):
        filenames = ["image1.jpg", "image2.jpg", "image3.jpg"]

        with (
            patch.object(orchestrator.file_storage, "save_original_image") as mock_save,
            patch.object(ImageModel, "create") as mock_create,
            patch.object(orchestrator, "_generate_variants_background") as _,
        ):
            mock_save.return_value = (
                "/fake/path",
                {"file_size": 1024, "width": 100, "height": 100, "format": "JPEG"},
            )
            mock_create.return_value = AsyncMock()

            import asyncio

            tasks = [
                orchestrator.start_image_processing(sample_image_data, filename)
                for filename in filenames
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 3

            image_ids = [result[0] for result in results]
            assert len(set(image_ids)) == 3
