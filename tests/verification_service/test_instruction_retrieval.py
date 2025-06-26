import json
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from src.verification_service.app.core.config import Settings
from src.verification_service.app.schemas import ModificationInstructionData
from src.verification_service.app.services.instruction_retrieval import (
    InstructionRetrievalError,
    InstructionRetrievalService,
)


@pytest.fixture
def mock_settings():
    settings = Mock(spec=Settings)
    settings.IMAGE_PROCESSING_SERVICE_URL = "http://localhost:8001"
    return settings


@pytest.fixture
def instruction_retrieval_service(mock_settings):
    return InstructionRetrievalService(settings=mock_settings)


@pytest.fixture
def sample_modification_id():
    return uuid4()


@pytest.fixture
def sample_response_data():
    return {
        "modification_id": str(uuid4()),
        "image_id": str(uuid4()),
        "original_filename": "test_image.jpg",
        "variant_number": 42,
        "algorithm_type": "xor_transform",
        "instructions": {
            "algorithm_type": "xor_transform",
            "image_mode": "RGB",
            "operations": [{"row": 10, "col": 20, "channel": 1, "parameter": 255}],
        },
        "storage_path": "/path/to/variant.jpg",
        "created_at": "2024-01-15T12:00:00Z",
    }


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=httpx.AsyncClient)


class TestInstructionRetrievalService:
    @pytest.mark.asyncio
    async def test_get_modification_instructions_success(
        self,
        instruction_retrieval_service,
        sample_modification_id,
        sample_response_data,
        mock_http_client,
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_response_data
        mock_http_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            result = await instruction_retrieval_service.get_modification_instructions(
                sample_modification_id
            )

            assert isinstance(result, ModificationInstructionData)
            assert result.modification_id == UUID(
                sample_response_data["modification_id"]
            )
            assert result.image_id == UUID(sample_response_data["image_id"])
            assert result.original_filename == sample_response_data["original_filename"]
            assert result.variant_number == sample_response_data["variant_number"]
            assert result.algorithm_type == sample_response_data["algorithm_type"]
            assert result.instructions == sample_response_data["instructions"]
            assert result.storage_path == sample_response_data["storage_path"]

            expected_url = f"http://localhost:8001/internal/modifications/{sample_modification_id}/instructions"
            mock_http_client.get.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_get_modification_instructions_not_found(
        self, instruction_retrieval_service, sample_modification_id, mock_http_client
    ):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_http_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            with pytest.raises(InstructionRetrievalError) as exc_info:
                await instruction_retrieval_service.get_modification_instructions(
                    sample_modification_id
                )

            assert f"Modification {sample_modification_id} not found" in str(
                exc_info.value
            )

    @pytest.mark.asyncio
    async def test_get_modification_instructions_http_error(
        self, instruction_retrieval_service, sample_modification_id, mock_http_client
    ):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_http_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            with pytest.raises(InstructionRetrievalError) as exc_info:
                await instruction_retrieval_service.get_modification_instructions(
                    sample_modification_id
                )

            assert "HTTP 500: Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_modification_instructions_network_error(
        self, instruction_retrieval_service, sample_modification_id, mock_http_client
    ):
        mock_http_client.get.side_effect = httpx.RequestError("Connection failed")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            with pytest.raises(InstructionRetrievalError) as exc_info:
                await instruction_retrieval_service.get_modification_instructions(
                    sample_modification_id
                )

            assert "Network error: Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_modification_instructions_timeout(
        self, instruction_retrieval_service, sample_modification_id, mock_http_client
    ):
        mock_http_client.get.side_effect = httpx.TimeoutException("Request timeout")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            with pytest.raises(InstructionRetrievalError) as exc_info:
                await instruction_retrieval_service.get_modification_instructions(
                    sample_modification_id
                )

            assert "Request timeout: Request timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_modification_instructions_json_decode_error(
        self, instruction_retrieval_service, sample_modification_id, mock_http_client
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        mock_http_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            with pytest.raises(InstructionRetrievalError) as exc_info:
                await instruction_retrieval_service.get_modification_instructions(
                    sample_modification_id
                )

            assert "Unexpected error:" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_modification_instructions_pydantic_validation_error(
        self, instruction_retrieval_service, sample_modification_id, mock_http_client
    ):
        invalid_data = {"invalid_field": "invalid_value"}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = invalid_data
        mock_http_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            with pytest.raises(InstructionRetrievalError) as exc_info:
                await instruction_retrieval_service.get_modification_instructions(
                    sample_modification_id
                )

            # Pydantic ValidationError gets wrapped in InstructionRetrievalError
            assert "unexpected error:" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_modification_instructions_missing_required_fields(
        self, instruction_retrieval_service, sample_modification_id, mock_http_client
    ):
        incomplete_data = {
            "modification_id": str(uuid4()),
        }
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = incomplete_data
        mock_http_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            with pytest.raises(InstructionRetrievalError) as exc_info:
                await instruction_retrieval_service.get_modification_instructions(
                    sample_modification_id
                )

            # Pydantic ValidationError gets wrapped in InstructionRetrievalError
            assert "unexpected error:" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_modification_instructions_invalid_uuid_format(
        self, instruction_retrieval_service, sample_modification_id, mock_http_client
    ):
        invalid_uuid_data = {
            "modification_id": "not-a-valid-uuid",
            "image_id": str(uuid4()),
            "original_filename": "test.jpg",
            "variant_number": 1,
            "algorithm_type": "xor_transform",
            "instructions": {},
            "storage_path": "/path",
            "created_at": "2024-01-15T12:00:00Z",
        }
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = invalid_uuid_data
        mock_http_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            with pytest.raises(InstructionRetrievalError) as exc_info:
                await instruction_retrieval_service.get_modification_instructions(
                    sample_modification_id
                )

            assert "Unexpected error:" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_modification_instructions_with_minimal_valid_data(
        self, instruction_retrieval_service, sample_modification_id, mock_http_client
    ):
        minimal_data = {
            "modification_id": str(uuid4()),
            "image_id": str(uuid4()),
            "original_filename": "minimal.png",
            "variant_number": 1,
            "algorithm_type": "test_algorithm",
            "instructions": {},
            "storage_path": "/minimal/path",
            "created_at": "2024-01-15T12:00:00Z",
        }
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = minimal_data
        mock_http_client.get.return_value = mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            result = await instruction_retrieval_service.get_modification_instructions(
                sample_modification_id
            )

            assert isinstance(result, ModificationInstructionData)
            assert result.modification_id == UUID(minimal_data["modification_id"])
            assert result.original_filename == "minimal.png"
            assert result.variant_number == 1
            assert result.algorithm_type == "test_algorithm"
            assert result.instructions == {}

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(
        self, instruction_retrieval_service, sample_modification_id, mock_http_client
    ):
        mock_http_client.get.side_effect = RuntimeError("Unexpected error occurred")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_http_client
            mock_client_class.return_value.__aexit__.return_value = None

            with pytest.raises(InstructionRetrievalError) as exc_info:
                await instruction_retrieval_service.get_modification_instructions(
                    sample_modification_id
                )

            assert "Unexpected error: Unexpected error occurred" in str(exc_info.value)
