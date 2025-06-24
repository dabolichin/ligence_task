import io
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from image_modification_algorithms import XORTransformAlgorithm
from PIL import Image
from tortoise import Tortoise

from src.image_processing_service.app.api.internal import router as internal_router
from src.image_processing_service.app.api.public import router as public_router
from src.image_processing_service.app.core.dependencies import (
    ServiceContainer,
    get_file_storage,
    get_processing_orchestrator,
    get_variant_generator,
    override_container_for_testing,
    restore_container,
)
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
def test_container():
    """Create a fresh service container for each test."""
    container = ServiceContainer()
    override_container_for_testing(container)
    yield container
    restore_container()


@pytest.fixture
def mock_file_storage():
    """Create a mock FileStorageService."""
    mock = Mock(spec=FileStorageService)
    # Set up common return values
    mock.save_original_image = AsyncMock(
        return_value=(
            "/fake/path/image.jpg",
            {"file_size": 1024, "width": 100, "height": 100, "format": "JPEG"},
        )
    )
    mock.save_variant_image = AsyncMock(return_value="/fake/path/variant.jpg")
    mock.load_image = AsyncMock(return_value=Image.new("RGB", (100, 100), color="red"))
    mock.delete_image = AsyncMock(return_value=True)
    mock.delete_image_and_variants = AsyncMock(return_value=4)
    mock.file_exists = AsyncMock(return_value=True)
    mock.generate_variant_path = Mock(return_value="/fake/path/variant_001.jpg")
    mock.generate_variant_filename = Mock(return_value="test_variant_001.jpg")
    return mock


@pytest.fixture
def mock_xor_algorithm():
    """Create a mock XORTransformAlgorithm."""
    from dataclasses import dataclass
    from typing import Any

    @dataclass
    class MockInstructions:
        algorithm_type: str
        image_mode: str
        operations: list[dict[str, Any]]

    @dataclass
    class MockModificationResult:
        modified_image: Any
        instructions: MockInstructions

    def mock_apply_modifications(original_image, num_modifications):
        """Dynamic mock that adapts to input image mode."""
        image_mode = original_image.mode

        # Create appropriate operations based on image mode
        if image_mode == "RGB":
            operations = [{"row": 0, "col": 0, "channel": 0, "parameter": 128}]
        else:  # Grayscale (L mode)
            operations = [{"row": 0, "col": 0, "parameter": 128}]

        instructions = MockInstructions(
            algorithm_type="xor_transform", image_mode=image_mode, operations=operations
        )

        modified_image = Image.new(image_mode, original_image.size)

        return MockModificationResult(
            modified_image=modified_image, instructions=instructions
        )

    mock = Mock(spec=XORTransformAlgorithm)
    mock.apply_modifications = Mock(side_effect=mock_apply_modifications)
    mock.reverse_transformation = Mock(return_value=Image.new("RGB", (100, 100)))
    return mock


@pytest.fixture
def mock_modification_engine():
    from dataclasses import dataclass
    from typing import Any

    from image_modification_algorithms import ModificationEngine

    @dataclass
    class MockInstructions:
        algorithm_type: str
        image_mode: str
        operations: list[dict[str, Any]]

    @dataclass
    class MockModificationResult:
        modified_image: Any
        instructions: MockInstructions

    def mock_apply_modifications(image, algorithm_name, num_modifications, seed=None):
        image_mode = image.mode

        if image_mode == "RGB":
            operations = [{"row": 0, "col": 0, "channel": 0, "parameter": 128}]
        else:
            operations = [{"row": 0, "col": 0, "parameter": 128}]

        instructions = MockInstructions(
            algorithm_type="xor_transform", image_mode=image_mode, operations=operations
        )

        modified_image = Image.new(image_mode, image.size)

        return MockModificationResult(
            modified_image=modified_image, instructions=instructions
        )

    mock = Mock(spec=ModificationEngine)
    mock.get_available_algorithms = Mock(return_value=["xor_transform"])
    mock.apply_modifications = Mock(side_effect=mock_apply_modifications)
    mock.reverse_modifications = Mock(return_value=Image.new("RGB", (100, 100)))
    mock.get_algorithm_info = Mock(
        return_value={
            "name": "xor_transform",
            "description": "XOR Transform algorithm",
            "supports_seeding": True,
        }
    )
    return mock


@pytest.fixture
def mock_variant_generator():
    mock = Mock(spec=VariantGenerationService)
    mock.generate_variants = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_processing_orchestrator():
    mock = Mock(spec=ProcessingOrchestrator)
    mock.start_image_processing = AsyncMock(
        return_value=("image_id", {"message": "success"})
    )
    mock.get_processing_status = AsyncMock(return_value=None)
    mock.get_modification_details = AsyncMock(return_value=None)
    mock.get_image_variants = AsyncMock(return_value=[])
    return mock


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
def grayscale_image():
    return Image.new("L", (50, 50), color=128)


@pytest.fixture
def variant_service(test_container, mock_file_storage, mock_modification_engine):
    test_container.set_file_storage(mock_file_storage)
    test_container.set_modification_engine(mock_modification_engine)
    return test_container.variant_generator


@pytest.fixture
def sample_image_bytes():
    image = Image.new("RGB", (50, 50), color="blue")
    img_bytes = io.BytesIO()
    image.save(img_bytes, format="JPEG")
    return img_bytes.getvalue()


@pytest.fixture
def test_client(test_container):
    app = FastAPI()

    # Override FastAPI dependencies with test container services
    app.dependency_overrides[get_file_storage] = lambda: test_container.file_storage
    app.dependency_overrides[get_variant_generator] = (
        lambda: test_container.variant_generator
    )
    app.dependency_overrides[get_processing_orchestrator] = (
        lambda: test_container.processing_orchestrator
    )

    app.include_router(public_router, prefix="/api")
    app.include_router(internal_router, prefix="/internal")

    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "service": "image-processing"}

    return TestClient(app)


@pytest.fixture
def file_storage_service(test_container, mock_settings):
    file_storage = FileStorageService(settings=mock_settings)
    test_container.set_file_storage(file_storage)
    return file_storage


@pytest.fixture
def processing_orchestrator(test_container, mock_file_storage, mock_variant_generator):
    test_container.set_file_storage(mock_file_storage)
    test_container.set_variant_generator(mock_variant_generator)
    return test_container.processing_orchestrator


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


@pytest.fixture(autouse=True)
def mock_verification_service_calls():
    """Automatically mock verification service HTTP calls for all tests."""
    with patch(
        "src.image_processing_service.app.services.variant_generation.VariantGenerationService._notify_verification_service"
    ) as mock_notify:
        mock_notify.return_value = None
        yield mock_notify
