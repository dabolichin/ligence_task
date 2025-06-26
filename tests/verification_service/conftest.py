from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from image_modification_algorithms import ModificationEngine
from image_modification_algorithms.types import (
    ModificationAlgorithm,
    PixelOperation,
)

from src.verification_service.app.api import internal, public
from src.verification_service.app.core.dependencies import (
    get_image_comparison_service,
    get_image_reversal_service,
    get_instruction_retrieval_service,
    get_modification_engine,
    get_verification_history_service,
    get_verification_orchestrator,
    get_verification_persistence,
)
from src.verification_service.app.services.image_comparison import (
    ImageComparisonService,
)
from src.verification_service.app.services.image_reversal import (
    ImageReversalService,
)
from src.verification_service.app.services.instruction_retrieval import (
    InstructionRetrievalService,
)
from src.verification_service.app.services.verification_history import (
    VerificationHistoryService,
)
from src.verification_service.app.services.verification_orchestrator import (
    VerificationOrchestrator,
)
from src.verification_service.app.services.verification_persistence import (
    VerificationPersistence,
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
def mock_modification_engine():
    mock = Mock(spec=ModificationEngine)
    mock.get_available_algorithms = Mock(return_value=["xor_transform"])
    mock.reverse_modifications = Mock()
    return mock


@pytest.fixture
def mock_instruction_retrieval_service():
    mock = Mock(spec=InstructionRetrievalService)
    mock.get_modification_instructions = AsyncMock()
    return mock


@pytest.fixture
def mock_image_comparison_service():
    mock = Mock(spec=ImageComparisonService)
    mock.compare_images = Mock(return_value=True)
    mock.compare_from_paths = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_image_reversal_service():
    mock = Mock(spec=ImageReversalService)
    mock.verify_modification_completely = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_verification_persistence():
    mock = Mock(spec=VerificationPersistence)
    mock.save_verification_result = AsyncMock()
    mock.get_verification_result = AsyncMock()
    return mock


@pytest.fixture
def mock_verification_orchestrator():
    mock = Mock(spec=VerificationOrchestrator)
    mock.verify_modification = AsyncMock()
    mock.execute_verification_background = AsyncMock()
    return mock


@pytest.fixture
def mock_verification_history_service():
    mock = Mock(spec=VerificationHistoryService)
    mock.get_verification_status = AsyncMock()
    mock.get_verification_statistics = AsyncMock()
    mock.get_verification_history = AsyncMock()
    mock.get_verifications_by_modification_id = AsyncMock()
    return mock


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
def test_client(
    mock_modification_engine,
    mock_instruction_retrieval_service,
    mock_image_comparison_service,
    mock_image_reversal_service,
    mock_verification_persistence,
    mock_verification_orchestrator,
    mock_verification_history_service,
):
    app = FastAPI()

    app.dependency_overrides[get_modification_engine] = lambda: mock_modification_engine
    app.dependency_overrides[get_instruction_retrieval_service] = (
        lambda: mock_instruction_retrieval_service
    )
    app.dependency_overrides[get_image_comparison_service] = (
        lambda: mock_image_comparison_service
    )
    app.dependency_overrides[get_image_reversal_service] = (
        lambda: mock_image_reversal_service
    )
    app.dependency_overrides[get_verification_persistence] = (
        lambda: mock_verification_persistence
    )
    app.dependency_overrides[get_verification_orchestrator] = (
        lambda: mock_verification_orchestrator
    )
    app.dependency_overrides[get_verification_history_service] = (
        lambda: mock_verification_history_service
    )

    app.include_router(public.router, prefix="/api", tags=["public"])
    app.include_router(internal.router, prefix="/internal", tags=["internal"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "verification"}

    return TestClient(app)


@pytest.fixture
def integration_client():
    from src.verification_service.app.services.image_comparison import (
        ImageComparisonService,
    )
    from src.verification_service.app.services.image_reversal import (
        ImageReversalService,
    )
    from src.verification_service.app.services.instruction_retrieval import (
        InstructionRetrievalService,
    )
    from src.verification_service.app.services.verification_history import (
        VerificationHistoryService,
    )
    from src.verification_service.app.services.verification_orchestrator import (
        VerificationOrchestrator,
    )
    from src.verification_service.app.services.verification_persistence import (
        VerificationPersistence,
    )

    modification_engine = ModificationEngine()
    image_comparison_service = ImageComparisonService()
    image_reversal_service = ImageReversalService(
        image_comparison_service=image_comparison_service
    )
    verification_persistence = VerificationPersistence()
    verification_history_service = VerificationHistoryService()

    # Mock only the external HTTP service
    mock_instruction_retrieval_service = Mock(spec=InstructionRetrievalService)
    mock_instruction_retrieval_service.get_modification_instructions = AsyncMock()

    verification_orchestrator = VerificationOrchestrator(
        instruction_retrieval_service=mock_instruction_retrieval_service,
        modification_engine=modification_engine,
        image_reversal_service=image_reversal_service,
        verification_persistence=verification_persistence,
    )

    app = FastAPI()

    # Override dependencies with real services (except external HTTP calls)
    app.dependency_overrides[get_modification_engine] = lambda: modification_engine
    app.dependency_overrides[get_instruction_retrieval_service] = (
        lambda: mock_instruction_retrieval_service
    )
    app.dependency_overrides[get_image_comparison_service] = (
        lambda: image_comparison_service
    )
    app.dependency_overrides[get_image_reversal_service] = (
        lambda: image_reversal_service
    )
    app.dependency_overrides[get_verification_persistence] = (
        lambda: verification_persistence
    )
    app.dependency_overrides[get_verification_orchestrator] = (
        lambda: verification_orchestrator
    )
    app.dependency_overrides[get_verification_history_service] = (
        lambda: verification_history_service
    )

    app.include_router(public.router, prefix="/api", tags=["public"])
    app.include_router(internal.router, prefix="/internal", tags=["internal"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "verification"}

    services = {
        "modification_engine": modification_engine,
        "instruction_retrieval_service": mock_instruction_retrieval_service,
        "image_comparison_service": image_comparison_service,
        "image_reversal_service": image_reversal_service,
        "verification_persistence": verification_persistence,
        "verification_orchestrator": verification_orchestrator,
        "verification_history_service": verification_history_service,
    }

    yield TestClient(app), services
