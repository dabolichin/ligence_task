import uuid
from unittest.mock import AsyncMock, patch

import pytest
from tortoise.exceptions import DoesNotExist


class TestInternalModificationInstructionsEndpoint:
    @pytest.mark.asyncio
    async def test_get_modification_instructions_success(self, test_client):
        modification_id = uuid.uuid4()
        image_id = uuid.uuid4()

        mock_modification = AsyncMock()
        mock_modification.id = modification_id
        mock_modification.variant_number = 42
        mock_modification.algorithm_type.value = "xor_transform"
        mock_modification.instructions = {
            "algorithm_type": "xor_transform",
            "image_mode": "RGB",
            "operations": [
                {"row": 10, "col": 20, "channel": 0, "parameter": 128},
                {"row": 15, "col": 25, "channel": 1, "parameter": 64},
            ],
        }
        mock_modification.storage_path = "/storage/modified/test_variant_042.jpg"
        mock_modification.created_at = "2024-01-01T00:00:00Z"

        mock_image = AsyncMock()
        mock_image.id = image_id
        mock_image.original_filename = "test_image.jpg"
        mock_modification.image = mock_image

        with patch(
            "src.image_processing_service.app.api.internal.Modification.get"
        ) as mock_get:
            mock_query = AsyncMock()
            mock_query.select_related.return_value = mock_modification
            mock_get.return_value = mock_query

            response = test_client.get(
                f"/internal/modifications/{modification_id}/instructions"
            )

            assert response.status_code == 200
            data = response.json()

            assert data["modification_id"] == str(modification_id)
            assert data["image_id"] == str(image_id)
            assert data["variant_number"] == 42
            assert data["algorithm_type"] == "xor_transform"
            assert data["original_filename"] == "test_image.jpg"
            assert data["instructions"]["algorithm_type"] == "xor_transform"
            assert len(data["instructions"]["operations"]) == 2

            mock_get.assert_called_once_with(id=modification_id)

    @pytest.mark.asyncio
    async def test_get_modification_instructions_with_complex_data(self, test_client):
        modification_id = uuid.uuid4()
        image_id = uuid.uuid4()

        mock_modification = AsyncMock()
        mock_modification.id = modification_id
        mock_modification.variant_number = 1
        mock_modification.algorithm_type.value = "xor_transform"
        mock_modification.instructions = {
            "algorithm_type": "xor_transform",
            "image_mode": "RGB",
            "operations": [
                {"row": 0, "col": 0, "channel": 0, "parameter": 255},
                {"row": 10, "col": 20, "channel": 1, "parameter": 128},
                {"row": 50, "col": 75, "channel": 2, "parameter": 64},
            ],
            "metadata": {
                "total_operations": 3,
                "image_dimensions": [100, 100, 3],
                "modification_seed": 12345,
            },
        }
        mock_modification.storage_path = "/storage/modified/complex_variant_001.jpg"
        mock_modification.created_at = "2024-01-01T12:00:00Z"

        mock_image = AsyncMock()
        mock_image.id = image_id
        mock_image.original_filename = "complex_image.png"
        mock_modification.image = mock_image

        with patch(
            "src.image_processing_service.app.api.internal.Modification.get"
        ) as mock_get:
            mock_query = AsyncMock()
            mock_query.select_related.return_value = mock_modification
            mock_get.return_value = mock_query

            response = test_client.get(
                f"/internal/modifications/{modification_id}/instructions"
            )

            assert response.status_code == 200
            data = response.json()

            instructions = data["instructions"]
            assert instructions["metadata"]["total_operations"] == 3
            assert instructions["metadata"]["modification_seed"] == 12345
            assert len(instructions["operations"]) == 3

            first_op = instructions["operations"][0]
            assert first_op["row"] == 0
            assert first_op["parameter"] == 255

    @pytest.mark.asyncio
    async def test_get_modification_instructions_not_found(self, test_client):
        modification_id = uuid.uuid4()

        with patch(
            "src.image_processing_service.app.api.internal.Modification.get"
        ) as mock_get:
            mock_get.side_effect = DoesNotExist("Modification not found")

            response = test_client.get(
                f"/internal/modifications/{modification_id}/instructions"
            )

            assert response.status_code == 404
            data = response.json()
            assert f"Modification {modification_id} not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_modification_instructions_database_error(self, test_client):
        modification_id = uuid.uuid4()

        with patch(
            "src.image_processing_service.app.api.internal.Modification.get"
        ) as mock_get:
            mock_get.side_effect = Exception("Database connection failed")

            response = test_client.get(
                f"/internal/modifications/{modification_id}/instructions"
            )

            assert response.status_code == 500
            data = response.json()
            assert (
                "Internal server error retrieving modification instructions"
                in data["detail"]
            )

    @pytest.mark.asyncio
    async def test_get_modification_instructions_invalid_uuid(self, test_client):
        invalid_id = "not-a-valid-uuid"

        response = test_client.get(f"/internal/modifications/{invalid_id}/instructions")

        assert response.status_code == 422
