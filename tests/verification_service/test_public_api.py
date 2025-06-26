import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.verification_service.app.api import internal, public
from src.verification_service.app.core.dependencies import (
    get_verification_history_service,
)
from src.verification_service.app.schemas.verification import (
    VerificationHistoryItem,
    VerificationHistoryResponse,
    VerificationStatisticsResponse,
    VerificationStatusResponse,
)


@pytest.fixture
def client(mock_verification_history_service):
    app = FastAPI()

    # Override FastAPI dependencies with test mocks
    app.dependency_overrides[get_verification_history_service] = (
        lambda: mock_verification_history_service
    )

    app.include_router(public.router, prefix="/api", tags=["public"])
    app.include_router(internal.router, prefix="/internal", tags=["internal"])

    return TestClient(app)


class TestVerificationStatusEndpoint:
    def test_get_verification_status_success(
        self, client, mock_verification_history_service
    ):
        modification_id = uuid.uuid4()

        mock_response = VerificationStatusResponse(
            verification_id=str(modification_id),
            status="completed",
            is_reversible=True,
            verified_with_hash=True,
            verified_with_pixels=True,
            created_at="2024-01-01T12:00:00+00:00",
            completed_at="2024-01-01T12:01:00+00:00",
        )
        mock_verification_history_service.get_verification_status.return_value = (
            mock_response
        )

        response = client.get(f"/api/verification/{modification_id}/status")

        assert response.status_code == 200
        data = response.json()

        assert data["verification_id"] == str(modification_id)
        assert data["status"] == "completed"
        assert data["is_reversible"] is True
        assert data["verified_with_hash"] is True
        assert data["verified_with_pixels"] is True
        assert data["created_at"] is not None
        assert data["completed_at"] is not None

        mock_verification_history_service.get_verification_status.assert_called_once_with(
            str(modification_id)
        )

    def test_get_verification_status_not_found(
        self, client, mock_verification_history_service
    ):
        modification_id = uuid.uuid4()

        mock_response = VerificationStatusResponse(
            verification_id=str(modification_id),
            status="not_found",
            message=f"No verification found for ID {modification_id}",
        )
        mock_verification_history_service.get_verification_status.return_value = (
            mock_response
        )

        response = client.get(f"/api/verification/{modification_id}/status")

        assert response.status_code == 200
        data = response.json()

        assert data["verification_id"] == str(modification_id)
        assert data["status"] == "not_found"
        assert data["message"] == f"No verification found for ID {modification_id}"

        mock_verification_history_service.get_verification_status.assert_called_once_with(
            str(modification_id)
        )

    def test_get_verification_status_invalid_uuid(
        self, client, mock_verification_history_service
    ):
        invalid_id = "invalid-uuid-format"

        mock_response = VerificationStatusResponse(
            verification_id=invalid_id,
            status="invalid",
            message="Invalid verification ID format",
        )
        mock_verification_history_service.get_verification_status.return_value = (
            mock_response
        )

        response = client.get(f"/api/verification/{invalid_id}/status")

        assert response.status_code == 200
        data = response.json()

        assert data["verification_id"] == invalid_id
        assert data["status"] == "invalid"
        assert data["message"] == "Invalid verification ID format"

        mock_verification_history_service.get_verification_status.assert_called_once_with(
            invalid_id
        )

    def test_get_verification_status_pending(
        self, client, mock_verification_history_service
    ):
        modification_id = uuid.uuid4()

        mock_response = VerificationStatusResponse(
            verification_id=str(modification_id),
            status="pending",
            is_reversible=None,
            verified_with_hash=False,
            verified_with_pixels=False,
            created_at="2024-01-01T12:00:00+00:00",
            completed_at=None,
        )
        mock_verification_history_service.get_verification_status.return_value = (
            mock_response
        )

        response = client.get(f"/api/verification/{modification_id}/status")

        assert response.status_code == 200
        data = response.json()

        assert data["verification_id"] == str(modification_id)
        assert data["status"] == "pending"
        assert data["is_reversible"] is None
        assert data["verified_with_hash"] is False
        assert data["verified_with_pixels"] is False
        assert data["created_at"] is not None
        assert data["completed_at"] is None

        mock_verification_history_service.get_verification_status.assert_called_once_with(
            str(modification_id)
        )

    def test_get_verification_status_failed_verification(
        self, client, mock_verification_history_service
    ):
        modification_id = uuid.uuid4()

        mock_response = VerificationStatusResponse(
            verification_id=str(modification_id),
            status="completed",
            is_reversible=False,
            verified_with_hash=False,
            verified_with_pixels=False,
            created_at="2024-01-01T12:00:00+00:00",
            completed_at="2024-01-01T12:01:00+00:00",
        )
        mock_verification_history_service.get_verification_status.return_value = (
            mock_response
        )

        response = client.get(f"/api/verification/{modification_id}/status")

        assert response.status_code == 200
        data = response.json()

        assert data["verification_id"] == str(modification_id)
        assert data["status"] == "completed"
        assert data["is_reversible"] is False
        assert data["verified_with_hash"] is False
        assert data["verified_with_pixels"] is False

        mock_verification_history_service.get_verification_status.assert_called_once_with(
            str(modification_id)
        )

    def test_get_verification_status_database_error(
        self, client, mock_verification_history_service
    ):
        modification_id = uuid.uuid4()

        mock_response = VerificationStatusResponse(
            verification_id=str(modification_id),
            status="error",
            message="Internal server error",
        )
        mock_verification_history_service.get_verification_status.return_value = (
            mock_response
        )

        response = client.get(f"/api/verification/{modification_id}/status")

        assert response.status_code == 200
        data = response.json()

        assert data["verification_id"] == str(modification_id)
        assert data["status"] == "error"
        assert data["message"] == "Internal server error"

        mock_verification_history_service.get_verification_status.assert_called_once_with(
            str(modification_id)
        )


class TestVerificationStatisticsEndpoint:
    def test_get_verification_statistics_success(
        self, client, mock_verification_history_service
    ):
        mock_response = VerificationStatisticsResponse(
            total_verifications=10,
            successful_verifications=7,
            failed_verifications=2,
            pending_verifications=1,
            success_rate=70.0,
        )
        mock_verification_history_service.get_verification_statistics.return_value = (
            mock_response
        )

        response = client.get("/api/verification/statistics")

        assert response.status_code == 200
        data = response.json()

        assert data["total_verifications"] == 10
        assert data["successful_verifications"] == 7
        assert data["failed_verifications"] == 2
        assert data["pending_verifications"] == 1
        assert data["success_rate"] == 70.0
        assert "error" not in data or data["error"] is None

        mock_verification_history_service.get_verification_statistics.assert_called_once()

    def test_get_verification_statistics_empty_database(
        self, client, mock_verification_history_service
    ):
        mock_response = VerificationStatisticsResponse(
            total_verifications=0,
            successful_verifications=0,
            failed_verifications=0,
            pending_verifications=0,
            success_rate=0.0,
        )
        mock_verification_history_service.get_verification_statistics.return_value = (
            mock_response
        )

        response = client.get("/api/verification/statistics")

        assert response.status_code == 200
        data = response.json()

        assert data["total_verifications"] == 0
        assert data["successful_verifications"] == 0
        assert data["failed_verifications"] == 0
        assert data["pending_verifications"] == 0
        assert data["success_rate"] == 0.0

        mock_verification_history_service.get_verification_statistics.assert_called_once()

    def test_get_verification_statistics_error(
        self, client, mock_verification_history_service
    ):
        mock_response = VerificationStatisticsResponse(
            total_verifications=0,
            successful_verifications=0,
            failed_verifications=0,
            pending_verifications=0,
            success_rate=0.0,
            error="Failed to retrieve statistics",
        )
        mock_verification_history_service.get_verification_statistics.return_value = (
            mock_response
        )

        response = client.get("/api/verification/statistics")

        assert response.status_code == 200
        data = response.json()

        assert data["total_verifications"] == 0
        assert data["successful_verifications"] == 0
        assert data["failed_verifications"] == 0
        assert data["pending_verifications"] == 0
        assert data["success_rate"] == 0.0
        assert data["error"] == "Failed to retrieve statistics"

        mock_verification_history_service.get_verification_statistics.assert_called_once()


class TestVerificationHistoryEndpoint:
    """Test GET /verification/history endpoint."""

    def test_get_verification_history_success(
        self, client, mock_verification_history_service
    ):
        modification_id = uuid.uuid4()

        mock_response = VerificationHistoryResponse(
            verifications=[
                VerificationHistoryItem(
                    modification_id=str(modification_id),
                    status="completed",
                    is_reversible=True,
                    verified_with_hash=True,
                    verified_with_pixels=True,
                    created_at="2024-01-01T12:00:00+00:00",
                    completed_at="2024-01-01T12:01:00+00:00",
                )
            ],
            total_count=1,
            limit=50,
            offset=0,
        )
        mock_verification_history_service.get_verification_history.return_value = (
            mock_response
        )

        response = client.get("/api/verification/history")

        assert response.status_code == 200
        data = response.json()

        assert "verifications" in data
        assert "total_count" in data
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert data["total_count"] == 1
        assert isinstance(data["verifications"], list)
        assert len(data["verifications"]) == 1

        verification = data["verifications"][0]
        assert verification["modification_id"] == str(modification_id)
        assert verification["status"] == "completed"
        assert verification["is_reversible"] is True
        assert verification["verified_with_hash"] is True
        assert verification["verified_with_pixels"] is True

        mock_verification_history_service.get_verification_history.assert_called_once_with(
            limit=50, offset=0
        )

    def test_get_verification_history_with_pagination(
        self, client, mock_verification_history_service
    ):
        mock_response = VerificationHistoryResponse(
            verifications=[],
            total_count=0,
            limit=10,
            offset=5,
        )
        mock_verification_history_service.get_verification_history.return_value = (
            mock_response
        )

        response = client.get("/api/verification/history?limit=10&offset=5")

        assert response.status_code == 200
        data = response.json()

        assert data["limit"] == 10
        assert data["offset"] == 5

        mock_verification_history_service.get_verification_history.assert_called_once_with(
            limit=10, offset=5
        )

    def test_get_verification_history_parameter_validation(
        self, client, mock_verification_history_service
    ):
        mock_response = VerificationHistoryResponse(
            verifications=[],
            total_count=0,
            limit=100,  # Should be capped at 100
            offset=0,  # Should be at least 0
        )
        mock_verification_history_service.get_verification_history.return_value = (
            mock_response
        )

        response = client.get("/api/verification/history?limit=200")
        assert response.status_code == 200

        response = client.get("/api/verification/history?offset=-5")
        assert response.status_code == 200

        assert (
            mock_verification_history_service.get_verification_history.call_count == 2
        )

    def test_get_verification_history_empty_results(
        self, client, mock_verification_history_service
    ):
        mock_response = VerificationHistoryResponse(
            verifications=[],
            total_count=0,
            limit=1,
            offset=999999,
        )
        mock_verification_history_service.get_verification_history.return_value = (
            mock_response
        )

        response = client.get("/api/verification/history?limit=1&offset=999999")

        assert response.status_code == 200
        data = response.json()

        assert "verifications" in data
        assert "total_count" in data
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 1
        assert data["offset"] == 999999
        assert data["total_count"] == 0
        assert isinstance(data["verifications"], list)
        assert len(data["verifications"]) == 0

        mock_verification_history_service.get_verification_history.assert_called_once_with(
            limit=1, offset=999999
        )

    def test_get_verification_history_database_error(
        self, client, mock_verification_history_service
    ):
        mock_response = VerificationHistoryResponse(
            verifications=[],
            total_count=0,
            limit=50,
            offset=0,
            error="Failed to retrieve verification history",
        )
        mock_verification_history_service.get_verification_history.return_value = (
            mock_response
        )

        response = client.get("/api/verification/history")

        assert response.status_code == 200
        data = response.json()

        assert data["verifications"] == []
        assert data["total_count"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert data["error"] == "Failed to retrieve verification history"

        mock_verification_history_service.get_verification_history.assert_called_once_with(
            limit=50, offset=0
        )


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "verification"


class TestVerificationsByModificationEndpoint:
    def test_get_verifications_by_modification_success(
        self, client, mock_verification_history_service
    ):
        from src.verification_service.app.schemas.verification import (
            VerificationHistoryItem,
            VerificationsByModificationResponse,
        )

        modification_id = "12345678-1234-5678-9abc-123456789abc"
        mock_response = VerificationsByModificationResponse(
            modification_id=modification_id,
            verifications=[
                VerificationHistoryItem(
                    modification_id=modification_id,
                    status="completed",
                    is_reversible=True,
                    verified_with_hash=True,
                    verified_with_pixels=True,
                    created_at="2023-12-01T10:00:00",
                    completed_at="2023-12-01T10:01:00",
                ),
                VerificationHistoryItem(
                    modification_id=modification_id,
                    status="completed",
                    is_reversible=True,
                    verified_with_hash=True,
                    verified_with_pixels=True,
                    created_at="2023-12-01T11:00:00",
                    completed_at="2023-12-01T11:01:00",
                ),
            ],
            total_count=2,
        )

        mock_verification_history_service.get_verifications_by_modification_id.return_value = mock_response

        response = client.get(f"/api/verification/modifications/{modification_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["modification_id"] == modification_id
        assert data["total_count"] == 2
        assert len(data["verifications"]) == 2

        # Check first verification
        verification1 = data["verifications"][0]
        assert verification1["modification_id"] == modification_id
        assert verification1["status"] == "completed"
        assert verification1["is_reversible"] is True
        assert verification1["verified_with_hash"] is True
        assert verification1["verified_with_pixels"] is True

        mock_verification_history_service.get_verifications_by_modification_id.assert_called_once_with(
            modification_id
        )

    def test_get_verifications_by_modification_not_found(
        self, client, mock_verification_history_service
    ):
        from src.verification_service.app.schemas.verification import (
            VerificationsByModificationResponse,
        )

        modification_id = "12345678-1234-5678-9abc-123456789abc"
        mock_response = VerificationsByModificationResponse(
            modification_id=modification_id,
            verifications=[],
            total_count=0,
        )

        mock_verification_history_service.get_verifications_by_modification_id.return_value = mock_response

        response = client.get(f"/api/verification/modifications/{modification_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["modification_id"] == modification_id
        assert data["total_count"] == 0
        assert len(data["verifications"]) == 0
        assert "error" not in data or data["error"] is None

    def test_get_verifications_by_modification_invalid_uuid(
        self, client, mock_verification_history_service
    ):
        from src.verification_service.app.schemas.verification import (
            VerificationsByModificationResponse,
        )

        invalid_id = "invalid-uuid"
        mock_response = VerificationsByModificationResponse(
            modification_id=invalid_id,
            verifications=[],
            total_count=0,
            error="Invalid modification ID format",
        )

        mock_verification_history_service.get_verifications_by_modification_id.return_value = mock_response

        response = client.get(f"/api/verification/modifications/{invalid_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["modification_id"] == invalid_id
        assert data["total_count"] == 0
        assert len(data["verifications"]) == 0
        assert data["error"] == "Invalid modification ID format"

    def test_get_verifications_by_modification_database_error(
        self, client, mock_verification_history_service
    ):
        from src.verification_service.app.schemas.verification import (
            VerificationsByModificationResponse,
        )

        modification_id = "12345678-1234-5678-9abc-123456789abc"
        mock_response = VerificationsByModificationResponse(
            modification_id=modification_id,
            verifications=[],
            total_count=0,
            error="Failed to retrieve verifications for modification",
        )

        mock_verification_history_service.get_verifications_by_modification_id.return_value = mock_response

        response = client.get(f"/api/verification/modifications/{modification_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["modification_id"] == modification_id
        assert data["total_count"] == 0
        assert len(data["verifications"]) == 0
        assert data["error"] == "Failed to retrieve verifications for modification"

    def test_get_verifications_by_modification_single_verification(
        self, client, mock_verification_history_service
    ):
        from src.verification_service.app.schemas.verification import (
            VerificationHistoryItem,
            VerificationsByModificationResponse,
        )

        modification_id = "12345678-1234-5678-9abc-123456789abc"
        mock_response = VerificationsByModificationResponse(
            modification_id=modification_id,
            verifications=[
                VerificationHistoryItem(
                    modification_id=modification_id,
                    status="pending",
                    is_reversible=None,
                    verified_with_hash=None,
                    verified_with_pixels=None,
                    created_at="2023-12-01T10:00:00",
                    completed_at=None,
                ),
            ],
            total_count=1,
        )

        mock_verification_history_service.get_verifications_by_modification_id.return_value = mock_response

        response = client.get(f"/api/verification/modifications/{modification_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["modification_id"] == modification_id
        assert data["total_count"] == 1
        assert len(data["verifications"]) == 1

        verification = data["verifications"][0]
        assert verification["status"] == "pending"
        assert verification["is_reversible"] is None
        assert verification["completed_at"] is None
