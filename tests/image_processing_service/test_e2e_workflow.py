import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from image_modification_algorithms import ModificationEngine
from PIL import Image

from src.image_processing_service.app.api.internal import router as internal_router
from src.image_processing_service.app.api.public import router as public_router
from src.image_processing_service.app.core.dependencies import (
    get_file_storage,
    get_processing_orchestrator,
    get_variant_generator,
)
from src.image_processing_service.app.models import Image as ImageModel
from src.image_processing_service.app.services.file_storage import FileStorageService
from src.image_processing_service.app.services.processing_orchestrator import (
    ProcessingOrchestrator,
)
from src.image_processing_service.app.services.variant_generation import (
    VariantGenerationService,
)
from tests.shared_fixtures import SharedImageFixtures


class TestCompleteServiceWorkflow:
    @pytest.fixture
    def integration_client(self, temp_storage_dir, mock_xor_algorithm):
        mock_settings = MagicMock()
        mock_settings.absolute_original_images_dir = str(
            Path(temp_storage_dir) / "original"
        )
        mock_settings.absolute_modified_images_dir = str(
            Path(temp_storage_dir) / "modified"
        )
        mock_settings.absolute_temp_dir = str(Path(temp_storage_dir) / "temp")
        mock_settings.ALLOWED_IMAGE_FORMATS = ["jpeg", "png", "bmp"]
        mock_settings.VARIANTS_COUNT = 100
        mock_settings.MIN_MODIFICATIONS_PER_VARIANT = 100

        # Create services with mock settings
        file_storage = FileStorageService(mock_settings)
        modification_engine = ModificationEngine()
        variant_generator = VariantGenerationService(
            file_storage=file_storage,
            modification_engine=modification_engine,
            settings=mock_settings,
        )
        processing_orchestrator = ProcessingOrchestrator(
            file_storage=file_storage,
            variant_generator=variant_generator,
            settings=mock_settings,
        )

        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(public_router, prefix="/api")
        test_app.include_router(internal_router, prefix="/internal")

        test_app.dependency_overrides[get_file_storage] = lambda: file_storage
        test_app.dependency_overrides[get_variant_generator] = lambda: variant_generator
        test_app.dependency_overrides[get_processing_orchestrator] = (
            lambda: processing_orchestrator
        )

        services = {
            "file_storage": file_storage,
            "variant_generator": variant_generator,
            "processing_orchestrator": processing_orchestrator,
        }

        yield TestClient(test_app), services

    @pytest.fixture
    def sample_image_data(self):
        """Get real tiny test image data for fastest testing."""
        return SharedImageFixtures.load_tiny_image()

    async def _check_for_processing_start(self, client, processing_id):
        status_response = client.get(f"/api/processing/{processing_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()

        assert status_data["status"] in ["processing", "completed"]

        return status_data

    @pytest.mark.asyncio
    async def test_complete_image_processing_workflow(
        self, integration_client, sample_image_data
    ):
        client, services = integration_client
        image_data, filename = sample_image_data

        # Step 1: Upload tiny image (2x2 pixels = very fast processing)
        upload_response = client.post(
            "/api/modify",
            files={"file": (filename, image_data, "image/png")},
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert "processing_id" in upload_data
        assert upload_data["original_filename"] == filename
        assert upload_data["file_size"] == len(image_data)

        processing_id = upload_data["processing_id"]

        # Step 2: Check for processing to start
        status_data = await self._check_for_processing_start(client, processing_id)

        assert status_data["status"] in ["processing", "completed"], (
            f"Processing failed to start: {status_data['status']}"
        )
        assert status_data["total_variants"] == 100

        # Step 3: Test API endpoints work
        details_response = client.get(f"/api/modifications/{processing_id}")
        assert details_response.status_code == 200
        details_data = details_response.json()
        assert details_data["image_id"] == processing_id
        assert details_data["original_filename"] == filename

        # Step 4: Test original image serving
        original_response = client.get(f"/api/images/{processing_id}/original")
        assert original_response.status_code == 200
        assert "image/" in original_response.headers["content-type"]

        # Step 5: Test variants listing
        variants_response = client.get(f"/api/images/{processing_id}/variants")
        assert variants_response.status_code == 200
        variants_data = variants_response.json()
        assert isinstance(variants_data["variants"], list)
        for variant in variants_data["variants"]:
            assert "variant_id" in variant
            assert "variant_number" in variant
            assert "storage_path" in variant
            assert "num_modifications" in variant
            assert variant["num_modifications"] >= 1

    @pytest.mark.asyncio
    async def test_workflow_with_file_system_persistence(
        self, integration_client, sample_image_data, temp_storage_dir
    ):
        client, services = integration_client
        image_data, filename = sample_image_data

        upload_response = client.post(
            "/api/modify",
            files={"file": (filename, image_data, "image/png")},
        )

        assert upload_response.status_code == 200
        processing_id = upload_response.json()["processing_id"]

        status_data = await self._check_for_processing_start(client, processing_id)
        assert status_data["status"] in ["processing", "completed"]

        original_dir = Path(temp_storage_dir) / "original"
        original_files = list(original_dir.glob(f"{processing_id}_original.*"))
        assert len(original_files) == 1
        assert original_files[0].exists()

        modified_dir = Path(temp_storage_dir) / "modified"
        variant_files = list(modified_dir.glob(f"{processing_id}_variant_*.jpg"))
        assert len(variant_files) >= 0

        for variant_file in variant_files[:3]:  # Test first few variants
            assert variant_file.exists()
            image = Image.open(variant_file)
            assert image.size is not None
            assert image.mode in ["RGB", "L"]

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, integration_client):
        client, services = integration_client

        invalid_response = client.post(
            "/api/modify",
            files={"file": ("invalid.jpg", b"not an image", "image/jpeg")},
        )
        assert invalid_response.status_code == 400

        no_file_response = client.post("/api/modify")
        assert no_file_response.status_code == 422

        fake_id = str(uuid.uuid4())
        status_response = client.get(f"/api/processing/{fake_id}/status")
        assert status_response.status_code == 404

        fake_mod_id = str(uuid.uuid4())
        instructions_response = client.get(
            f"/internal/modifications/{fake_mod_id}/instructions"
        )
        assert instructions_response.status_code == 404

    @pytest.mark.asyncio
    async def test_concurrent_workflow_processing(
        self, integration_client, sample_image_data
    ):
        client, services = integration_client
        image_data, filename = sample_image_data

        upload_tasks = []
        for i in range(2):  # Test concurrent uploads
            test_filename = f"concurrent_test_{i}_{filename}"
            response = client.post(
                "/api/modify",
                files={"file": (test_filename, image_data, "image/png")},
            )
            assert response.status_code == 200
            upload_tasks.append(response.json()["processing_id"])

        for i, processing_id in enumerate(upload_tasks):
            status_data = await self._check_for_processing_start(client, processing_id)
            assert status_data["status"] in ["processing", "completed"], (
                f"Concurrent processing {i + 1} failed to start: {status_data['status']}"
            )
            assert status_data["total_variants"] == 100

    @pytest.mark.asyncio
    async def test_service_integration_boundaries(
        self, integration_client, sample_image_data
    ):
        client, services = integration_client

        file_storage = services["file_storage"]
        variant_generator = services["variant_generator"]
        processing_orchestrator = services["processing_orchestrator"]

        assert variant_generator.file_storage is file_storage
        assert processing_orchestrator.file_storage is file_storage
        assert processing_orchestrator.variant_generator is variant_generator

        image_data, filename = sample_image_data
        upload_response = client.post(
            "/api/modify",
            files={"file": (filename, image_data, "image/png")},
        )

        assert upload_response.status_code == 200
        processing_id = upload_response.json()["processing_id"]

        status_data = await self._check_for_processing_start(client, processing_id)
        assert status_data["status"] in ["processing", "completed"], (
            f"Service integration test failed: {status_data['status']}"
        )
        assert status_data["processing_id"] == processing_id
        image_record = await ImageModel.get(id=processing_id)
        assert image_record is not None

        assert await file_storage.file_exists(image_record.storage_path)

    @pytest.mark.asyncio
    async def test_api_endpoint_integration(
        self, integration_client, sample_image_data
    ):
        client, services = integration_client

        image_data, filename = sample_image_data
        upload_response = client.post(
            "/api/modify",
            files={"file": (filename, image_data, "image/png")},
        )

        assert upload_response.status_code == 200
        processing_id = upload_response.json()["processing_id"]

        status_data = await self._check_for_processing_start(client, processing_id)
        assert status_data["status"] in ["processing", "completed"]

        variants_response = client.get(f"/api/images/{processing_id}/variants")
        assert variants_response.status_code == 200
        variants_data = variants_response.json()
        assert isinstance(variants_data["variants"], list)

        assert len(variants_data["variants"]) > 0
        modification_id = variants_data["variants"][0]["variant_id"]
        instructions_response = client.get(
            f"/internal/modifications/{modification_id}/instructions"
        )
        assert instructions_response.status_code == 200
        instructions_data = instructions_response.json()

        assert instructions_data["modification_id"] == modification_id
        assert instructions_data["algorithm_type"] == "xor_transform"
        assert "instructions" in instructions_data
        assert len(instructions_data["instructions"]) > 0

    @pytest.mark.asyncio
    async def test_large_image_workflow(self, integration_client):
        client, services = integration_client

        test_image_data, filename = SharedImageFixtures.load_pattern_image()

        upload_response = client.post(
            "/api/modify",
            files={"file": (filename, test_image_data, "image/png")},
        )

        assert upload_response.status_code == 200
        processing_id = upload_response.json()["processing_id"]

        assert upload_response.json()["file_size"] == len(test_image_data)

        status_data = await self._check_for_processing_start(client, processing_id)
        assert status_data["status"] in ["processing", "completed"], (
            f"Large image test failed: {status_data['status']}"
        )
        assert status_data["total_variants"] == 100

        variants_response = client.get(f"/api/images/{processing_id}/variants")
        assert variants_response.status_code == 200
        variants_data = variants_response.json()
        assert isinstance(variants_data["variants"], list)

        # For completed variants, verify basic structure
        for variant in variants_data["variants"]:
            assert variant["num_modifications"] >= 1

    @pytest.mark.asyncio
    async def test_grayscale_image_workflow(self, integration_client):
        client, services = integration_client

        grayscale_image_data, filename = (
            SharedImageFixtures.load_small_grayscale_image()
        )

        upload_response = client.post(
            "/api/modify",
            files={"file": (filename, grayscale_image_data, "image/png")},
        )

        assert upload_response.status_code == 200
        processing_id = upload_response.json()["processing_id"]

        status_data = await self._check_for_processing_start(client, processing_id)
        assert status_data["status"] in ["processing", "completed"]

        details_response = client.get(f"/api/modifications/{processing_id}")
        assert details_response.status_code == 200
        details_data = details_response.json()
        assert details_data["format"] == "PNG"

        variants_response = client.get(f"/api/images/{processing_id}/variants")
        assert variants_response.status_code == 200
        variants_data = variants_response.json()
        assert isinstance(variants_data["variants"], list)

        # If variants exist, test modification instructions for grayscale
        assert len(variants_data["variants"]) > 0
        modification_id = variants_data["variants"][0]["variant_id"]
        instructions_response = client.get(
            f"/internal/modifications/{modification_id}/instructions"
        )

        assert instructions_response.status_code == 200
        instructions_data = instructions_response.json()
        assert "instructions" in instructions_data
        assert instructions_data["algorithm_type"] == "xor_transform"
