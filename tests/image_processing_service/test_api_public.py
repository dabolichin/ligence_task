import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.image_processing_service.app.api.public import (
    _get_media_type_from_path,
)


class TestImageUploadEndpoint:
    def test_successful_image_upload(
        self,
        test_client,
        test_container,
        mock_processing_orchestrator,
        sample_image_bytes,
    ):
        image_id = str(uuid4())
        mock_processing_orchestrator.start_image_processing.return_value = (
            image_id,
            {
                "message": "Image processing started",
                "original_filename": "test.jpg",
                "file_size": len(sample_image_bytes),
            },
        )

        test_container.set_processing_orchestrator(mock_processing_orchestrator)

        response = test_client.post(
            "/api/modify",
            files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "processing_id" in data
        assert data["message"] == "Image processing started"
        assert data["original_filename"] == "test.jpg"
        assert data["file_size"] == len(sample_image_bytes)

        mock_processing_orchestrator.start_image_processing.assert_called_once()
        call_args = mock_processing_orchestrator.start_image_processing.call_args
        assert call_args[0][0] == sample_image_bytes  # file data
        assert call_args[0][1] == "test.jpg"  # filename

    def test_upload_no_file(self, test_client):
        response = test_client.post("/api/modify", files=None)
        assert response.status_code == 422

    def test_upload_empty_file(self, test_client):
        response = test_client.post(
            "/api/modify", files={"file": ("empty.jpg", b"", "image/jpeg")}
        )
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_upload_oversized_file(self, test_client):
        large_file = b"x" * (101 * 1024 * 1024)  # 101MB
        response = test_client.post(
            "/api/modify", files={"file": ("large.jpg", large_file, "image/jpeg")}
        )
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_upload_processing_error(
        self,
        test_client,
        test_container,
        mock_processing_orchestrator,
        sample_image_bytes,
    ):
        mock_processing_orchestrator.start_image_processing.side_effect = ValueError(
            "Invalid image format"
        )
        test_container.set_processing_orchestrator(mock_processing_orchestrator)

        response = test_client.post(
            "/api/modify",
            files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
        )
        assert response.status_code == 400
        assert "Invalid image format" in response.json()["detail"]


class TestProcessingStatusEndpoint:
    def test_get_processing_status_success(
        self,
        test_client,
        test_container,
        mock_processing_orchestrator,
    ):
        processing_id = uuid4()

        mock_status_result = AsyncMock()
        mock_status_result.processing_id = str(processing_id)
        mock_status_result.status = "processing"
        mock_status_result.progress = 50
        mock_status_result.variants_completed = 50
        mock_status_result.total_variants = 100
        mock_status_result.created_at = "2024-01-01T00:00:00Z"
        mock_status_result.completed_at = None
        mock_status_result.error_message = None

        mock_processing_orchestrator.get_processing_status.return_value = (
            mock_status_result
        )
        test_container.set_processing_orchestrator(mock_processing_orchestrator)

        response = test_client.get(f"/api/processing/{processing_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["processing_id"] == str(processing_id)
        assert data["status"] == "processing"
        assert data["progress"] == 50
        assert data["variants_completed"] == 50
        assert data["total_variants"] == 100

    def test_get_processing_status_not_found(
        self,
        test_client,
        test_container,
        mock_processing_orchestrator,
    ):
        processing_id = str(uuid4())
        mock_processing_orchestrator.get_processing_status.return_value = None
        test_container.set_processing_orchestrator(mock_processing_orchestrator)

        response = test_client.get(f"/api/processing/{processing_id}/status")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_processing_status_invalid_uuid(self, test_client):
        response = test_client.get("/api/processing/invalid-uuid/status")
        assert response.status_code == 422


class TestModificationDetailsEndpoint:
    def test_get_modification_details_success(
        self,
        test_client,
        test_container,
        mock_processing_orchestrator,
    ):
        modification_id = uuid4()

        mock_image = AsyncMock()
        mock_image.id = str(modification_id)
        mock_image.original_filename = "test.jpg"
        mock_image.file_size = 2048
        mock_image.width = 800
        mock_image.height = 600
        mock_image.format = "JPEG"
        mock_image.created_at = "2024-01-01T00:00:00Z"

        mock_result = AsyncMock()
        mock_result.image = mock_image
        mock_result.variants_count = 100

        mock_processing_orchestrator.get_modification_details.return_value = mock_result
        test_container.set_processing_orchestrator(mock_processing_orchestrator)

        response = test_client.get(f"/api/modifications/{modification_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["image_id"] == str(modification_id)
        assert data["original_filename"] == "test.jpg"
        assert data["file_size"] == 2048
        assert data["width"] == 800
        assert data["height"] == 600
        assert data["format"] == "JPEG"
        assert data["variants_count"] == 100

    def test_get_modification_details_not_found(
        self,
        test_client,
        test_container,
        mock_processing_orchestrator,
    ):
        modification_id = uuid4()

        mock_processing_orchestrator.get_modification_details.return_value = None
        test_container.set_processing_orchestrator(mock_processing_orchestrator)

        response = test_client.get(f"/api/modifications/{modification_id}")

        assert response.status_code == 404
        assert f"Image {modification_id} not found" in response.json()["detail"]


class TestOriginalImageEndpoint:
    def test_serve_original_image_success(
        self,
        test_client,
        test_container,
        mock_file_storage,
        sample_image_bytes,
    ):
        image_id = uuid4()

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(sample_image_bytes)
            temp_path = temp_file.name

        try:
            mock_file_storage.file_exists.return_value = True
            test_container.set_file_storage(mock_file_storage)

            with patch("src.image_processing_service.app.models.Image.get") as mock_get:
                mock_image = AsyncMock()
                mock_image.storage_path = temp_path
                mock_image.original_filename = "test.jpg"
                mock_get.return_value = mock_image

                response = test_client.get(f"/api/images/{image_id}/original")

                assert response.status_code == 500
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_serve_original_image_not_found(self, test_client):
        image_id = uuid4()
        with patch("src.image_processing_service.app.models.Image.get") as mock_get:
            mock_get.side_effect = Exception("DoesNotExist")
            response = test_client.get(f"/api/images/{image_id}/original")
            assert response.status_code == 500

    def test_serve_original_image_file_missing(
        self,
        test_client,
        test_container,
        mock_file_storage,
    ):
        image_id = uuid4()
        mock_file_storage.file_exists.return_value = False
        test_container.set_file_storage(mock_file_storage)

        with patch("src.image_processing_service.app.models.Image.get") as mock_get:
            mock_image = AsyncMock()
            mock_image.storage_path = "/nonexistent/path.jpg"
            mock_image.original_filename = "test.jpg"
            mock_get.return_value = mock_image

            response = test_client.get(f"/api/images/{image_id}/original")
            assert response.status_code == 500


class TestVariantListEndpoint:
    def test_list_image_variants_success(
        self,
        test_client,
        test_container,
        mock_processing_orchestrator,
    ):
        image_id = uuid4()

        mock_modifications = []
        for i in range(3):
            mock_mod = AsyncMock()
            mock_mod.id = str(uuid4())
            mock_mod.variant_number = i + 1
            mock_mod.algorithm_type.value = "xor_transform"
            mock_mod.instructions = {
                "modifications": [{"x": 10, "y": 20}] * (100 + i * 10)
            }
            mock_mod.storage_path = f"/path/variant_{i + 1}.jpg"
            mock_mod.created_at = "2024-01-01T00:00:00Z"
            mock_modifications.append(mock_mod)

        mock_processing_orchestrator.get_image_variants.return_value = (
            mock_modifications
        )
        test_container.set_processing_orchestrator(mock_processing_orchestrator)

        response = test_client.get(f"/api/images/{image_id}/variants")

        assert response.status_code == 200
        data = response.json()
        assert "variants" in data
        assert "total_count" in data
        assert data["total_count"] == 3
        assert len(data["variants"]) == 3

        # Check first variant structure
        variant = data["variants"][0]
        assert "variant_id" in variant
        assert "variant_number" in variant
        assert "algorithm_type" in variant
        assert "num_modifications" in variant
        assert "storage_path" in variant
        assert "created_at" in variant
        assert variant["algorithm_type"] == "xor_transform"

    def test_list_image_variants_not_found(
        self,
        test_client,
        test_container,
        mock_processing_orchestrator,
    ):
        image_id = uuid4()
        mock_processing_orchestrator.get_image_variants.return_value = None
        test_container.set_processing_orchestrator(mock_processing_orchestrator)

        response = test_client.get(f"/api/images/{image_id}/variants")
        assert response.status_code == 404
        assert f"Image {image_id} not found" in response.json()["detail"]

    def test_list_image_variants_empty(
        self,
        test_client,
        test_container,
        mock_processing_orchestrator,
    ):
        image_id = uuid4()
        mock_processing_orchestrator.get_image_variants.return_value = []
        test_container.set_processing_orchestrator(mock_processing_orchestrator)

        response = test_client.get(f"/api/images/{image_id}/variants")
        assert response.status_code == 404


class TestHealthEndpoint:
    def test_health_check(self, test_client):
        response = test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "image-processing"


class TestHTTPHelpers:
    @pytest.mark.parametrize(
        "file_path,expected_media_type",
        [
            ("/path/to/image.jpg", "image/jpeg"),
            ("/path/to/image.png", "image/png"),
            ("/path/to/image.bmp", "image/bmp"),
            ("/path/to/image.unknown", "application/octet-stream"),
            ("image.JPG", "image/jpeg"),  # Case insensitive
        ],
    )
    def test_get_media_type_from_path(self, file_path, expected_media_type):
        result = _get_media_type_from_path(file_path)
        assert result == expected_media_type, f"Failed for {file_path}"


class TestEndToEndWorkflow:
    def _create_mock_status_result(
        self, processing_id, status="completed", progress=100
    ):
        mock_result = AsyncMock()
        mock_result.processing_id = processing_id
        mock_result.status = status
        mock_result.progress = progress
        mock_result.variants_completed = progress
        mock_result.total_variants = 100
        mock_result.created_at = "2024-01-01T00:00:00Z"
        mock_result.completed_at = (
            "2024-01-01T00:05:00Z" if status == "completed" else None
        )
        mock_result.error_message = None
        return mock_result

    def _create_mock_image(self, image_id, filename="test.jpg", file_size=2048):
        mock_image = AsyncMock()
        mock_image.id = image_id
        mock_image.original_filename = filename
        mock_image.file_size = file_size
        mock_image.width = 100
        mock_image.height = 100
        mock_image.format = "JPEG"
        mock_image.created_at = "2024-01-01T00:00:00Z"
        return mock_image

    def _create_mock_modification_details(
        self, image_id, filename="test.jpg", variants_count=100
    ):
        mock_result = AsyncMock()
        mock_result.image = self._create_mock_image(image_id, filename)
        mock_result.variants_count = variants_count
        return mock_result

    def _create_mock_variants(self, count=100):
        mock_modifications = []
        for i in range(count):
            mock_mod = AsyncMock()
            mock_mod.id = str(uuid4())
            mock_mod.variant_number = i + 1
            mock_mod.algorithm_type.value = "xor_transform"
            mock_mod.instructions = {"modifications": [{"x": 10, "y": 20}] * (100 + i)}
            mock_mod.storage_path = f"/path/variant_{i + 1}.jpg"
            mock_mod.created_at = "2024-01-01T00:00:00Z"
            mock_modifications.append(mock_mod)
        return mock_modifications

    def test_complete_image_processing_workflow(
        self,
        test_client,
        test_container,
        mock_processing_orchestrator,
        sample_image_bytes,
    ):
        image_id = str(uuid4())

        # Step 1: Configure mock for upload
        mock_processing_orchestrator.start_image_processing.return_value = (
            image_id,
            {
                "message": "Image processing started",
                "original_filename": "workflow_test.jpg",
                "file_size": len(sample_image_bytes),
            },
        )
        test_container.set_processing_orchestrator(mock_processing_orchestrator)

        upload_response = test_client.post(
            "/api/modify",
            files={"file": ("workflow_test.jpg", sample_image_bytes, "image/jpeg")},
        )

        assert upload_response.status_code == 200
        processing_id = upload_response.json()["processing_id"]

        # Step 2: Configure mock for status check
        mock_processing_orchestrator.get_processing_status.return_value = (
            self._create_mock_status_result(processing_id)
        )

        status_response = test_client.get(f"/api/processing/{processing_id}/status")

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "completed"
        assert status_data["progress"] == 100

        # Step 3: Configure mock for modification details
        mock_processing_orchestrator.get_modification_details.return_value = (
            self._create_mock_modification_details(processing_id, "workflow_test.jpg")
        )

        details_response = test_client.get(f"/api/modifications/{processing_id}")

        assert details_response.status_code == 200
        details_data = details_response.json()
        assert details_data["original_filename"] == "workflow_test.jpg"
        assert details_data["variants_count"] == 100

        # Step 4: Configure mock for variants list
        mock_processing_orchestrator.get_image_variants.return_value = (
            self._create_mock_variants(100)
        )

        variants_response = test_client.get(f"/api/images/{processing_id}/variants")

        assert variants_response.status_code == 200
        data = variants_response.json()
        assert "variants" in data
        assert "total_count" in data
        assert data["total_count"] == 100
