import asyncio
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.image_processing_service.app.services.file_storage import FileStorageService


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
    settings.MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    return settings


@pytest.fixture
def file_storage(mock_settings):
    with patch(
        "src.image_processing_service.app.services.file_storage.get_settings",
        return_value=mock_settings,
    ):
        return FileStorageService()


@pytest.fixture
def sample_image():
    image = Image.new("RGB", (100, 100), color="red")
    return image


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes for testing."""
    image = Image.new("RGB", (50, 50), color="blue")
    import io

    img_bytes = io.BytesIO()
    image.save(img_bytes, format="JPEG")
    return img_bytes.getvalue()


class TestFileStorageService:
    def test_init_creates_directories(self, temp_storage_dir, mock_settings):
        original_dir = Path(mock_settings.absolute_original_images_dir)
        modified_dir = Path(mock_settings.absolute_modified_images_dir)
        temp_dir = Path(mock_settings.absolute_temp_dir)

        assert not original_dir.exists()
        assert not modified_dir.exists()
        assert not temp_dir.exists()


class TestPathGeneration:
    def test_generate_variant_path(self, file_storage):
        """Test variant image path generation."""
        image_id = "test-789"
        variant_number = 42
        extension = ".png"

        path = file_storage.generate_variant_path(image_id, variant_number, extension)

        assert "test-789_variant_042.png" in path
        assert "modified" in path

    def test_generate_variant_path_with_zero_padding(self, file_storage):
        """Test variant path generation with proper zero padding."""
        image_id = "test-001"
        variant_number = 5
        extension = ".bmp"

        path = file_storage.generate_variant_path(image_id, variant_number, extension)

        assert "test-001_variant_005.bmp" in path


class TestSaveOriginalImage:
    @pytest.mark.asyncio
    async def test_save_original_image_success(self, file_storage, sample_image_bytes):
        image_id = str(uuid.uuid4())
        filename = "test.jpg"

        storage_path, metadata = await file_storage.save_original_image(
            sample_image_bytes, filename, image_id
        )

        assert Path(storage_path).exists()
        assert f"{image_id}_original.jpg" in storage_path

        assert metadata["width"] == 50
        assert metadata["height"] == 50
        assert metadata["format"] == "JPEG"
        assert metadata["file_size"] > 0

    @pytest.mark.asyncio
    async def test_save_original_image_with_invalid_data(self, file_storage):
        image_id = str(uuid.uuid4())
        filename = "test.jpg"
        invalid_data = b"not an image"

        with pytest.raises(ValueError, match="Invalid image file"):
            await file_storage.save_original_image(invalid_data, filename, image_id)


class TestSaveVariantImage:
    @pytest.mark.asyncio
    async def test_save_variant_image_success(self, file_storage, sample_image):
        image_id = str(uuid.uuid4())
        variant_number = 15
        extension = ".png"

        storage_path = await file_storage.save_variant_image(
            sample_image, image_id, variant_number, extension
        )

        assert Path(storage_path).exists()
        assert f"{image_id}_variant_015.png" in storage_path

    @pytest.mark.asyncio
    async def test_save_variant_image_cleanup_on_error(self, file_storage):
        image_id = str(uuid.uuid4())
        variant_number = 99
        extension = ".jpg"

        mock_image = MagicMock()
        mock_image.save.side_effect = Exception("Save failed")

        with pytest.raises(IOError):
            await file_storage.save_variant_image(
                mock_image, image_id, variant_number, extension
            )

        expected_path = file_storage.generate_variant_path(
            image_id, variant_number, extension
        )
        assert not Path(expected_path).exists()


class TestLoadImage:
    @pytest.mark.asyncio
    async def test_load_image_success(self, file_storage, sample_image):
        image_id = str(uuid.uuid4())
        variant_number = 1
        original_filename = "test.jpg"

        storage_path = await file_storage.save_variant_image(
            sample_image, image_id, variant_number, original_filename
        )

        loaded_image = await file_storage.load_image(storage_path)

        assert isinstance(loaded_image, Image.Image)
        assert loaded_image.size == (100, 100)

    @pytest.mark.asyncio
    async def test_load_image_file_not_found(self, file_storage):
        non_existent_path = "/path/to/nowhere.jpg"

        with pytest.raises(FileNotFoundError):
            await file_storage.load_image(non_existent_path)

    @pytest.mark.asyncio
    async def test_load_image_invalid_file(self, file_storage, temp_storage_dir):
        invalid_path = Path(temp_storage_dir) / "invalid.jpg"
        invalid_path.write_text("not an image")

        with pytest.raises(IOError):
            await file_storage.load_image(str(invalid_path))


class TestFileOperations:
    @pytest.mark.asyncio
    async def test_delete_image_success(self, file_storage, sample_image):
        image_id = str(uuid.uuid4())
        storage_path = await file_storage.save_variant_image(
            sample_image, image_id, 1, "test.jpg"
        )

        assert Path(storage_path).exists()

        result = await file_storage.delete_image(storage_path)

        assert result is True
        assert not Path(storage_path).exists()

    @pytest.mark.asyncio
    async def test_delete_image_not_exists(self, file_storage):
        non_existent_path = "/path/to/nowhere.jpg"

        result = await file_storage.delete_image(non_existent_path)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_image_and_variants(
        self, file_storage, sample_image, sample_image_bytes
    ):
        image_id = str(uuid.uuid4())

        original_path, _ = await file_storage.save_original_image(
            sample_image_bytes, "test.jpg", image_id
        )

        variant_paths = []
        for i in range(1, 4):
            path = await file_storage.save_variant_image(
                sample_image, image_id, i, ".jpg"
            )
            variant_paths.append(path)

        assert Path(original_path).exists()
        for path in variant_paths:
            assert Path(path).exists()

        deleted_count = await file_storage.delete_image_and_variants(image_id)

        assert deleted_count == 4  # 1 original + 3 variants
        assert not Path(original_path).exists()
        for path in variant_paths:
            assert not Path(path).exists()


class TestMetadataExtraction:
    @pytest.mark.asyncio
    async def test_extract_image_metadata_success(
        self, file_storage, sample_image_bytes
    ):
        image_id = str(uuid.uuid4())
        filename = "test.jpg"

        storage_path, metadata = await file_storage.save_original_image(
            sample_image_bytes, filename, image_id
        )

        assert metadata["width"] == 50
        assert metadata["height"] == 50
        assert metadata["format"] == "JPEG"
        assert metadata["mode"] is not None
        assert metadata["file_size"] > 0


class TestAsyncOperations:
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, file_storage):
        image_id = str(uuid.uuid4())

        # Run multiple save operations concurrently with fresh images
        tasks = []
        for i in range(5):
            # Create fresh image for each task to avoid sharing issues
            fresh_image = Image.new("RGB", (100, 100), color="red")
            task = file_storage.save_variant_image(fresh_image, image_id, i + 1, ".jpg")
            tasks.append(task)

        # Wait for all to complete
        paths = await asyncio.gather(*tasks)

        assert len(paths) == 5
        for path in paths:
            assert Path(path).exists()

    @pytest.mark.asyncio
    async def test_async_context_safety(self, file_storage, sample_image_bytes):
        image_id = str(uuid.uuid4())
        filename = "context_test.jpg"

        # This should not raise any context-related errors
        storage_path, metadata = await file_storage.save_original_image(
            sample_image_bytes, filename, image_id
        )

        loaded_image = await file_storage.load_image(storage_path)

        assert isinstance(loaded_image, Image.Image)
        assert loaded_image.size == (50, 50)


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_permission_error_handling(self, file_storage):
        with patch(
            "pathlib.Path.unlink", side_effect=PermissionError("Permission denied")
        ):
            result = await file_storage._safe_delete_file("/some/path.jpg")
            assert result is False

    @pytest.mark.asyncio
    async def test_disk_full_simulation(self, file_storage, sample_image_bytes):
        image_id = str(uuid.uuid4())
        filename = "test.jpg"

        with patch("aiofiles.open", side_effect=OSError("No space left on device")):
            with pytest.raises(IOError, match="Failed to save original image"):
                await file_storage.save_original_image(
                    sample_image_bytes, filename, image_id
                )

    @pytest.mark.asyncio
    async def test_corrupted_file_handling(self, file_storage, temp_storage_dir):
        corrupted_path = Path(temp_storage_dir) / "corrupted.jpg"
        corrupted_path.write_bytes(b"corrupted image data")

        with pytest.raises(IOError):
            await file_storage.load_image(str(corrupted_path))
