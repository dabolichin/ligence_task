import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from src.image_processing_service.app.models import Image as ImageModel
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
    settings.storage_path = temp_storage_dir
    settings.ALLOWED_IMAGE_FORMATS = ["jpeg", "png", "bmp"]
    settings.MAX_FILE_SIZE = 100 * 1024 * 1024
    settings.VARIANTS_COUNT = 100
    settings.MIN_MODIFICATIONS_PER_VARIANT = 100
    return settings


@pytest.fixture
def mock_image_record():
    record = AsyncMock(spec=ImageModel)
    record.id = str(uuid.uuid4())
    record.filename = "test_image.jpg"
    record.format = "JPEG"
    record.size = 1024
    record.width = 100
    record.height = 100
    return record


@pytest.fixture
def sample_image():
    return Image.new("RGB", (100, 100), color="red")


@pytest.fixture
def small_sample_image():
    return Image.new("RGB", (10, 10), color="blue")


@pytest.fixture
def tiny_image():
    return Image.new("RGB", (1, 1), color="white")


@pytest.fixture
def grayscale_image():
    return Image.new("L", (50, 50), color=128)


@pytest.fixture
def small_grayscale_image():
    return Image.new("L", (8, 8), color=128)


@pytest.fixture
def variant_service(mock_settings):
    with patch(
        "src.image_processing_service.app.services.variant_generation.get_settings",
        return_value=mock_settings,
    ):
        return VariantGenerationService()


@pytest.fixture
def mock_modification_record():
    mock_modification = AsyncMock()
    mock_modification.id = str(uuid.uuid4())
    mock_modification.variant_number = 1
    mock_modification.algorithm_type = "xor_transform"
    mock_modification.instructions = {}
    mock_modification.storage_path = "/path/to/variant.jpg"
    return mock_modification
