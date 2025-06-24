import asyncio
import io
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from src.image_processing_service.app.api.internal import router as internal_router
from src.image_processing_service.app.api.public import router as public_router
from src.image_processing_service.app.core.dependencies import (
    ServiceContainer,
    get_file_storage,
    get_processing_orchestrator,
    get_variant_generator,
)
from src.image_processing_service.app.models import Image as ImageModel
from src.image_processing_service.app.models import Modification
from src.image_processing_service.app.services.file_storage import FileStorageService


class TestSimpleServiceIntegration:
    @pytest.fixture
    def test_app(self, temp_storage_dir):
        app = FastAPI()
        app.include_router(public_router, prefix="/api")
        app.include_router(internal_router, prefix="/internal")

        mock_settings = MagicMock()
        mock_settings.absolute_original_images_dir = str(
            Path(temp_storage_dir) / "original"
        )
        mock_settings.absolute_modified_images_dir = str(
            Path(temp_storage_dir) / "modified"
        )
        mock_settings.absolute_temp_dir = str(Path(temp_storage_dir) / "temp")
        mock_settings.ALLOWED_IMAGE_FORMATS = ["jpeg", "png", "bmp"]

        for dir_path in [
            mock_settings.absolute_original_images_dir,
            mock_settings.absolute_modified_images_dir,
            mock_settings.absolute_temp_dir,
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

        container = ServiceContainer()

        file_storage = FileStorageService(settings=mock_settings)
        container.set_file_storage(file_storage)

        app.dependency_overrides[get_file_storage] = lambda: container.file_storage
        app.dependency_overrides[get_variant_generator] = (
            lambda: container.variant_generator
        )
        app.dependency_overrides[get_processing_orchestrator] = (
            lambda: container.processing_orchestrator
        )

        return TestClient(app), container

    @pytest.fixture
    def sample_image_data(self):
        image = Image.new("RGB", (50, 50), color="red")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="JPEG")
        return img_bytes.getvalue()

    def test_service_container_integration(self, test_app):
        client, container = test_app

        file_storage = container.file_storage
        variant_generator = container.variant_generator
        processing_orchestrator = container.processing_orchestrator

        assert variant_generator.file_storage is file_storage
        assert processing_orchestrator.file_storage is file_storage
        assert processing_orchestrator.variant_generator is variant_generator

    def test_api_routing_integration(self, test_app):
        client, container = test_app

        # Verify routes exist without testing HTTP details (that's for API tests)
        from src.image_processing_service.app.api.internal import (
            router as internal_router,
        )
        from src.image_processing_service.app.api.public import router as public_router

        # Check that routers have the expected routes
        public_routes = [route.path for route in public_router.routes]
        internal_routes = [route.path for route in internal_router.routes]

        assert "/modify" in public_routes
        assert "/processing/{processing_id}/status" in public_routes
        assert "/modifications/{modification_id}/instructions" in internal_routes

    @pytest.mark.asyncio
    async def test_file_storage_integration(self, test_app, sample_image_data):
        client, container = test_app

        file_storage = container.file_storage

        image_id = str(uuid.uuid4())
        storage_path, metadata = await file_storage.save_original_image(
            sample_image_data, "test.jpg", image_id
        )

        assert Path(storage_path).exists()
        assert metadata["width"] == 50
        assert metadata["height"] == 50
        assert metadata["format"] == "JPEG"

        loaded_image = await file_storage.load_image(storage_path)
        assert loaded_image.size == (50, 50)

        variant_path = await file_storage.save_variant_image(
            loaded_image, image_id, 1, ".jpg"
        )
        assert Path(variant_path).exists()

    @pytest.mark.asyncio
    async def test_variant_generation_service_integration(self, test_app):
        client, container = test_app

        test_image = Image.new("RGB", (10, 10), color="blue")

        mock_image_record = MagicMock()
        mock_image_record.id = str(uuid.uuid4())
        mock_image_record.format = "JPEG"

        variant_generator = container.variant_generator

        with patch(
            "src.image_processing_service.app.services.variant_generation.Modification.create"
        ) as mock_create:
            mock_modification = MagicMock()
            mock_modification.id = str(uuid.uuid4())
            mock_create.return_value = mock_modification

            variants = await variant_generator.generate_variants(
                test_image, mock_image_record
            )

            assert len(variants) == 100
            assert mock_create.call_count == 100

            for variant in variants:
                assert "variant_number" in variant
                assert "storage_path" in variant
                assert "modification_id" in variant
                assert "num_modifications" in variant

    def test_processing_orchestrator_integration(self, test_app, sample_image_data):
        client, container = test_app

        file_storage = container.file_storage
        orchestrator = container.processing_orchestrator

        assert orchestrator.file_storage is file_storage
        assert orchestrator.variant_generator is not None
        assert orchestrator.variant_generator.file_storage is file_storage

    def test_service_error_handling_integration(self, test_app):
        client, container = test_app

        file_storage = container.file_storage

        import tempfile

        with tempfile.TemporaryDirectory() as _:
            try:
                asyncio.run(file_storage.load_image("/nonexistent/path.jpg"))
                assert False, "Should have raised an exception"
            except Exception as e:
                assert isinstance(e, (FileNotFoundError, IOError))

    @pytest.mark.asyncio
    async def test_database_model_integration(self):
        from src.image_processing_service.app.models.modification import AlgorithmType

        image_record = await ImageModel.create(
            original_filename="test.jpg",
            file_size=1024,
            width=100,
            height=100,
            format="JPEG",
            storage_path="/fake/path.jpg",
        )

        modification = await Modification.create(
            image=image_record,
            algorithm_type=AlgorithmType.XOR_TRANSFORM,
            variant_number=1,
            instructions={"test": "data"},
            num_modifications=100,
            storage_path="/fake/variant/path.jpg",
        )

        assert modification.image_id == image_record.id

        found_modifications = await Modification.filter(image_id=image_record.id).all()
        assert len(found_modifications) == 1
        assert found_modifications[0].id == modification.id

        await modification.delete()
        await image_record.delete()

    def test_dependency_override_integration(self, test_app):
        client, container = test_app

        custom_file_storage = MagicMock()
        container.set_file_storage(custom_file_storage)

        assert container.file_storage is custom_file_storage

        variant_generator = container.variant_generator
        assert variant_generator.file_storage is custom_file_storage

    @pytest.mark.asyncio
    async def test_concurrent_service_operations(self, test_app, sample_image_data):
        import asyncio

        client, container = test_app
        file_storage = container.file_storage

        tasks = []
        for i in range(3):
            image_id = f"concurrent-test-{i}"
            task = file_storage.save_original_image(
                sample_image_data, f"test_{i}.jpg", image_id
            )
            tasks.append(task)

        # Wait for all operations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations succeeded
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent operation failed: {result}")
            else:
                storage_path, metadata = result
                assert Path(storage_path).exists()
                assert metadata["format"] == "JPEG"
