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
        self,
        test_container,
        mock_file_storage,
        mock_variant_generator,
        sample_image_data,
        mock_image_record,
    ):
        filename = "test_image.jpg"

        mock_file_storage.save_original_image.return_value = (
            "/fake/path/image.jpg",
            {"file_size": 1024, "width": 100, "height": 100, "format": "JPEG"},
        )

        test_container.set_file_storage(mock_file_storage)
        test_container.set_variant_generator(mock_variant_generator)
        orchestrator = test_container.get_processing_orchestrator()

        with patch.object(ImageModel, "create") as mock_create:
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

            mock_file_storage.save_original_image.assert_called_once_with(
                sample_image_data, filename, image_id
            )
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_image_processing_file_validation_error(
        self,
        test_container,
        mock_file_storage,
        mock_variant_generator,
        sample_image_data,
    ):
        invalid_data = b"not an image"
        filename = "invalid.txt"

        mock_file_storage.save_original_image.side_effect = ValueError(
            "Invalid image file"
        )

        test_container.set_file_storage(mock_file_storage)
        test_container.set_variant_generator(mock_variant_generator)
        orchestrator = test_container.get_processing_orchestrator()

        with pytest.raises(ValueError, match="Invalid image file"):
            await orchestrator.start_image_processing(invalid_data, filename)

    @pytest.mark.asyncio
    async def test_start_image_processing_io_error(
        self,
        test_container,
        mock_file_storage,
        mock_variant_generator,
        sample_image_data,
    ):
        filename = "test.jpg"

        mock_file_storage.save_original_image.side_effect = IOError("Disk full")

        test_container.set_file_storage(mock_file_storage)
        test_container.set_variant_generator(mock_variant_generator)
        orchestrator = test_container.get_processing_orchestrator()

        with pytest.raises(IOError, match="Disk full"):
            await orchestrator.start_image_processing(sample_image_data, filename)

        mock_file_storage.delete_image_and_variants.assert_called_once()

    @pytest.mark.asyncio
    async def test_processing_completes_after_upload(
        self,
        test_container,
        mock_file_storage,
        mock_variant_generator,
        sample_image_data,
        mock_image_record,
    ):
        filename = "test_image.jpg"

        mock_file_storage.save_original_image.return_value = (
            "/fake/path/image.jpg",
            {"file_size": 1024, "width": 100, "height": 100, "format": "JPEG"},
        )
        mock_file_storage.load_image.return_value = Image.new(
            "RGB", (100, 100), color="red"
        )

        test_container.set_file_storage(mock_file_storage)
        test_container.set_variant_generator(mock_variant_generator)
        orchestrator = test_container.get_processing_orchestrator()

        with (
            patch.object(ImageModel, "create") as mock_create,
            patch.object(orchestrator, "_notify_verification_service") as _,
        ):
            mock_create.return_value = mock_image_record

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

            mock_file_storage.save_original_image.assert_called_once()
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_processing_status_in_progress(
        self, test_container, mock_file_storage, mock_variant_generator
    ):
        image_id = str(uuid.uuid4())

        test_container.set_file_storage(mock_file_storage)
        test_container.set_variant_generator(mock_variant_generator)
        orchestrator = test_container.get_processing_orchestrator()

        async def mock_get_func(id):
            mock_record = MagicMock()
            mock_record.created_at = "2023-01-01T00:00:00"
            mock_record.updated_at = "2023-01-01T00:01:00"
            return mock_record

        async def mock_count_func():
            return 50

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
            assert status.status == "processing"
            assert status.progress == 50
            assert status.variants_completed == 50
            assert status.total_variants == 100

    @pytest.mark.asyncio
    async def test_get_processing_status_completed(
        self, test_container, mock_file_storage, mock_variant_generator
    ):
        image_id = str(uuid.uuid4())

        test_container.set_file_storage(mock_file_storage)
        test_container.set_variant_generator(mock_variant_generator)
        orchestrator = test_container.get_processing_orchestrator()

        async def mock_get_func(id):
            mock_record = MagicMock()
            mock_record.created_at = "2023-01-01T00:00:00"
            mock_record.updated_at = "2023-01-01T00:01:00"
            return mock_record

        async def mock_count_func():
            return 100

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
            assert status.status == "completed"
            assert status.progress == 100
            assert status.variants_completed == 100
            assert status.total_variants == 100

    @pytest.mark.asyncio
    async def test_get_processing_status_not_found(
        self, test_container, mock_file_storage, mock_variant_generator
    ):
        test_container.set_file_storage(mock_file_storage)
        test_container.set_variant_generator(mock_variant_generator)
        orchestrator = test_container.get_processing_orchestrator()

        with patch.object(ImageModel, "get") as mock_get:
            from tortoise.exceptions import DoesNotExist

            mock_get.side_effect = DoesNotExist(ImageModel)

            status = await orchestrator.get_processing_status("non-existent")
            assert status is None

    @pytest.mark.asyncio
    async def test_upload_validation_and_io_errors(
        self, test_container, mock_file_storage, mock_variant_generator
    ):
        test_container.set_file_storage(mock_file_storage)
        test_container.set_variant_generator(mock_variant_generator)
        orchestrator = test_container.get_processing_orchestrator()

        invalid_data = b"not an image"
        filename = "invalid.jpg"

        mock_file_storage.save_original_image.side_effect = ValueError(
            "Invalid image format"
        )

        with pytest.raises(ValueError, match="Invalid image format"):
            await orchestrator.start_image_processing(invalid_data, filename)

        # Reset mock call count before testing IO error
        mock_file_storage.delete_image_and_variants.reset_mock()

        valid_data = b"valid image data"
        mock_file_storage.save_original_image.side_effect = IOError("Disk full")

        with pytest.raises(IOError, match="Disk full"):
            await orchestrator.start_image_processing(valid_data, filename)

        mock_file_storage.delete_image_and_variants.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_image_processing(
        self,
        test_container,
        mock_file_storage,
        mock_variant_generator,
        sample_image_data,
    ):
        filenames = ["image1.jpg", "image2.jpg"]

        mock_file_storage.save_original_image.return_value = (
            "/fake/path",
            {"file_size": 1024, "width": 100, "height": 100, "format": "JPEG"},
        )

        test_container.set_file_storage(mock_file_storage)
        test_container.set_variant_generator(mock_variant_generator)
        orchestrator = test_container.get_processing_orchestrator()

        with (
            patch.object(ImageModel, "create") as mock_create,
            patch.object(orchestrator, "_generate_variants_background") as _,
        ):
            mock_create.return_value = AsyncMock()

            results = []
            for filename in filenames:
                result = await orchestrator.start_image_processing(
                    sample_image_data, filename
                )
                results.append(result)

            assert len(results) == 2
            image_ids = [result[0] for result in results]
            assert len(set(image_ids)) == 2  # All unique IDs
