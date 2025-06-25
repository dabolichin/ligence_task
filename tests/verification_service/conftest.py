from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from image_modification_algorithms.types import (
    ModificationAlgorithm,
    PixelOperation,
)

from src.verification_service.app.api import internal, public
from src.verification_service.app.core.dependencies import (
    ServiceContainer,
    get_verification_orchestrator_dependency,
)
from src.verification_service.app.services.image_comparison import (
    ImageComparisonService,
)


@pytest.fixture
def mock_xor_algorithm():
    mock_algorithm = Mock(spec=ModificationAlgorithm)
    mock_algorithm.get_name.return_value = "xor_transform"
    mock_algorithm.get_operation_class.return_value = PixelOperation
    return mock_algorithm


@pytest.fixture
def sample_pixel_operations_data():
    return [
        {"row": 10, "col": 20, "channel": 1, "parameter": 255},
        {"row": 5, "col": 8, "channel": 0, "parameter": 128},
        {"row": 15, "col": 25},  # Missing optional fields
    ]


@pytest.fixture
def sample_grayscale_operations_data():
    return [
        {"row": 3, "col": 7, "parameter": 100},
        {"row": 12, "col": 18, "parameter": 200},
    ]


@pytest.fixture
def sample_custom_operations_data():
    return [
        {"value": 42},
        {"value": 100},
    ]


@pytest.fixture
def test_container():
    return ServiceContainer()


@pytest.fixture
def comparison_service():
    return ImageComparisonService()


@pytest.fixture
def sample_image_rgb():
    from PIL import Image

    image = Image.new("RGB", (10, 10), color=(255, 0, 0))  # Red 10x10 image
    return image


@pytest.fixture
def sample_image_grayscale():
    from PIL import Image

    image = Image.new("L", (5, 5), color=128)  # Gray 5x5 image
    return image


@pytest.fixture
def different_color_image():
    from PIL import Image

    return Image.new("RGB", (10, 10), color=(0, 255, 0))  # Green 10x10 image


@pytest.fixture
def different_size_image():
    from PIL import Image

    return Image.new("RGB", (5, 5), color=(255, 0, 0))  # Same color, different size


@pytest.fixture
def different_mode_image():
    from PIL import Image

    return Image.new("L", (10, 10), color=128)  # Grayscale instead of RGB


@pytest.fixture
def temp_image_paths(sample_image_rgb, different_color_image):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Save sample images to temporary files
        original_path = temp_dir / "original.png"
        different_path = temp_dir / "different.png"
        identical_path = temp_dir / "identical.png"

        sample_image_rgb.save(original_path)
        different_color_image.save(different_path)
        sample_image_rgb.copy().save(identical_path)

        yield {
            "original": original_path,
            "different": different_path,
            "identical": identical_path,
        }


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    from tortoise import Tortoise

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={
            "models": [
                "src.verification_service.app.models.verification_result",
            ]
        },
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture
def test_client(test_container):
    app = FastAPI()

    # Override FastAPI dependencies with test container services
    app.dependency_overrides[get_verification_orchestrator_dependency] = (
        lambda: test_container.verification_orchestrator
    )

    app.include_router(public.router, prefix="/api", tags=["public"])
    app.include_router(internal.router, prefix="/internal", tags=["internal"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "verification"}

    return TestClient(app)
