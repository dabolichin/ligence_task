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
    get_instruction_parser_dependency,
    get_test_container,
    get_verification_orchestrator_dependency,
    override_container_for_testing,
    restore_container,
)
from src.verification_service.app.services.instruction_retrieval import (
    InstructionRetrievalService,
)


@pytest.fixture
def mock_xor_algorithm():
    mock_algorithm = Mock(spec=ModificationAlgorithm)
    mock_algorithm.get_name.return_value = "xor_transform"
    mock_algorithm.get_operation_class.return_value = PixelOperation
    return mock_algorithm


@pytest.fixture
def instruction_parser():
    """Get InstructionParser from DI container."""
    test_container = get_test_container()
    override_container_for_testing(test_container)

    try:
        yield get_instruction_parser_dependency()
    finally:
        restore_container()


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
    return get_test_container()


@pytest.fixture
def mock_instruction_retrieval_service():
    from unittest.mock import AsyncMock

    mock = Mock(spec=InstructionRetrievalService)
    mock.get_modification_instructions = AsyncMock()
    return mock


@pytest.fixture
def container_with_mocks(test_container, mock_instruction_retrieval_service):
    test_container.set_instruction_retrieval_service(mock_instruction_retrieval_service)

    # Override global container for tests
    override_container_for_testing(test_container)

    yield test_container

    # Restore original container after test
    restore_container()


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
