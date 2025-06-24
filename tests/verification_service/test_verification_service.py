import os
import sys

import pytest
from fastapi.testclient import TestClient

verification_service_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "verification_service"
)
if verification_service_path not in sys.path:
    sys.path.insert(0, verification_service_path)

from main import create_app  # noqa: E402


class TestVerificationServiceLifecycle:
    @pytest.fixture
    def client(self, test_container):
        from unittest.mock import AsyncMock

        from fastapi import FastAPI

        from src.verification_service.app.api import internal, public
        from src.verification_service.app.core.dependencies import (
            get_verification_orchestrator_dependency,
        )

        mock_orchestrator = AsyncMock()
        test_container.set_verification_orchestrator(mock_orchestrator)

        app = FastAPI()
        app.dependency_overrides[get_verification_orchestrator_dependency] = (
            lambda: test_container.verification_orchestrator
        )

        app.include_router(public.router, prefix="/api", tags=["public"])
        app.include_router(internal.router, prefix="/internal", tags=["internal"])

        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "verification"}

        return TestClient(app)

    def test_health_endpoint(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "verification"

    def test_api_routes_mounted(self, client):
        response = client.get("/api/verification/statistics")
        assert response.status_code == 200

        response = client.post(
            "/internal/verify",
            json={
                "image_id": "550e8400-e29b-41d4-a716-446655440000",
                "modification_id": "550e8400-e29b-41d4-a716-446655440001",
            },
        )
        assert response.status_code == 200


class TestVerificationServiceConfiguration:
    """Test verification service configuration."""

    def test_service_settings(self):
        """Test that service settings are properly configured."""
        from app.core.config import get_settings

        settings = get_settings()

        assert settings.APP_NAME == "Verification Service"
        assert settings.PORT == 8002
        assert settings.CONCURRENT_VERIFICATION_LIMIT >= 1
        assert settings.POLLING_INTERVAL >= 1
        assert settings.MAX_RETRY_ATTEMPTS >= 1

    def test_database_configuration(self):
        """Test database configuration."""
        from app.core.config import get_settings

        settings = get_settings()

        assert "verification.db" in settings.DATABASE_URL
        assert settings.absolute_database_url.startswith("sqlite:///")

    def test_inter_service_communication_config(self):
        """Test inter-service communication configuration."""
        from app.core.config import get_settings

        settings = get_settings()

        assert settings.IMAGE_PROCESSING_SERVICE_URL
        assert "8001" in settings.IMAGE_PROCESSING_SERVICE_URL  # Default IPS port


class TestDatabaseIntegration:
    @pytest.mark.asyncio
    async def test_database_initialization(self):
        from src.verification_service.app.db.database import close_db, init_db

        # Should not raise exception
        await init_db()
        await close_db()


class TestServiceIntegration:
    @pytest.fixture
    def client(self):
        app = create_app()
        return TestClient(app)

    def test_internal_api_integration(self, client):
        import uuid

        request_data = {
            "image_id": str(uuid.uuid4()),
            "modification_id": str(uuid.uuid4()),
        }

        response = client.post("/internal/verify", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "modification_id" in data

    def test_public_api_integration(self, client):
        response = client.get("/api/verification/statistics")
        assert response.status_code == 200

        response = client.get("/api/verification/history")
        assert response.status_code == 200

        verification_id = "550e8400-e29b-41d4-a716-446655440000"
        response = client.get(f"/api/verification/{verification_id}/status")
        assert response.status_code == 200

    def test_dependency_injection_integration(self):
        from app.core.dependencies import get_service_container

        container = get_service_container()

        settings = container.settings
        assert settings is not None

        instruction_parser = container.instruction_parser
        assert instruction_parser is not None


class TestErrorHandling:
    @pytest.fixture
    def client(self):
        app = create_app()
        return TestClient(app)

    def test_invalid_endpoint_404(self, client):
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404

    def test_invalid_json_request(self, client):
        response = client.post(
            "/internal/verify",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_request_data(self, client):
        response = client.post("/internal/verify", json={})
        assert response.status_code == 422
