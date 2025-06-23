import io
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from tortoise import Tortoise

from src.image_processing_service.app.api.internal import router as internal_router
from src.image_processing_service.app.api.public import router as public_router
from src.image_processing_service.app.models import Image as ImageModel
from src.image_processing_service.app.services.file_storage import FileStorageService
from src.image_processing_service.app.services.processing_orchestrator import (
    ProcessingOrchestrator,
)
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
    record.original_filename = "test_image.jpg"
    record.format = "JPEG"
    record.file_size = 1024
    record.width = 100
    record.height = 100
    record.storage_path = "/fake/path/to/image.jpg"
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


@pytest.fixture
def sample_image_bytes():
    image = Image.new("RGB", (50, 50), color="blue")
    img_bytes = io.BytesIO()
    image.save(img_bytes, format="JPEG")
    return img_bytes.getvalue()


@pytest.fixture
def sample_png_bytes():
    """Create a sample PNG image for testing"""
    img = Image.new("RGB", (200, 150), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    return img_bytes.getvalue()


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    app = FastAPI()
    app.include_router(public_router, prefix="/api")
    app.include_router(internal_router, prefix="/internal")

    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "service": "image-processing"}

    return TestClient(app)


@pytest.fixture
def file_storage(mock_settings):
    with patch(
        "src.image_processing_service.app.services.file_storage.get_settings",
        return_value=mock_settings,
    ):
        return FileStorageService()


@pytest.fixture
def orchestrator(mock_settings):
    with patch(
        "src.image_processing_service.app.services.processing_orchestrator.get_settings",
        return_value=mock_settings,
    ):
        return ProcessingOrchestrator()


@pytest.fixture(scope="session", autouse=True)
async def setup_tortoise():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={
            "models": [
                "src.image_processing_service.app.models.image",
                "src.image_processing_service.app.models.modification",
            ]
        },
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()
