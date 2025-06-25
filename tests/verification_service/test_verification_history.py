import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.verification_service.app.models.verification_result import (
    VerificationStatus,
)
from src.verification_service.app.services.verification_history import (
    VerificationHistoryService,
)


@pytest.fixture
def service():
    return VerificationHistoryService()


class TestVerificationStatusMethods:
    @patch(
        "src.verification_service.app.services.verification_history.VerificationResult.filter"
    )
    async def test_get_verification_status_found(self, mock_filter, service):
        verification_id = str(uuid.uuid4())

        mock_result = type("MockResult", (), {})()
        mock_result.status = VerificationStatus.COMPLETED
        mock_result.is_reversible = True
        mock_result.verified_with_hash = True
        mock_result.verified_with_pixels = True
        mock_result.created_at = datetime.fromisoformat("2024-01-01T12:00:00+00:00")
        mock_result.updated_at = datetime.fromisoformat("2024-01-01T12:01:00+00:00")

        mock_filter.return_value.first = AsyncMock(return_value=mock_result)

        result = await service.get_verification_status(verification_id)

        assert result.verification_id == verification_id
        assert result.status == "completed"
        assert result.is_reversible is True
        assert result.verified_with_hash is True
        assert result.verified_with_pixels is True

    @patch(
        "src.verification_service.app.services.verification_history.VerificationResult.filter"
    )
    async def test_get_verification_status_not_found(self, mock_filter, service):
        verification_id = str(uuid.uuid4())

        mock_filter.return_value.first = AsyncMock(return_value=None)

        result = await service.get_verification_status(verification_id)

        assert result.verification_id == verification_id
        assert result.status == "not_found"
        assert "No verification found" in result.message

    async def test_get_verification_status_invalid_uuid(self, service):
        invalid_id = "not-a-uuid"

        result = await service.get_verification_status(invalid_id)

        assert result.verification_id == invalid_id
        assert result.status == "invalid"
        assert "Invalid verification ID format" in result.message


class TestVerificationStatisticsMethods:
    @patch(
        "src.verification_service.app.services.verification_history.VerificationResult.filter"
    )
    @patch(
        "src.verification_service.app.services.verification_history.VerificationResult.all"
    )
    async def test_get_verification_statistics_success(
        self, mock_all, mock_filter, service
    ):
        """Test getting statistics successfully."""
        mock_all.return_value.count = AsyncMock(return_value=10)
        mock_filter.return_value.count = AsyncMock(
            side_effect=[7, 2, 1]
        )  # success, failed, pending

        result = await service.get_verification_statistics()

        assert result.total_verifications == 10
        assert result.successful_verifications == 7
        assert result.failed_verifications == 2
        assert result.pending_verifications == 1
        assert result.success_rate == 70.0

    @patch(
        "src.verification_service.app.services.verification_history.VerificationResult.all"
    )
    async def test_get_verification_statistics_empty(self, mock_all, service):
        mock_all.return_value.count = AsyncMock(return_value=0)

        result = await service.get_verification_statistics()

        assert result.total_verifications == 0
        assert result.success_rate == 0.0


class TestVerificationHistoryMethods:
    async def test_get_verification_history_parameter_validation(self, service):
        with patch(
            "src.verification_service.app.services.verification_history.VerificationResult.all"
        ) as mock_all:
            mock_all.return_value.count = AsyncMock(return_value=0)

            mock_query = type("MockQuery", (), {})()
            mock_query.offset = lambda x: mock_query
            mock_query.limit = lambda x: mock_query
            mock_query.order_by = AsyncMock(return_value=[])

            mock_all.side_effect = [mock_all.return_value, mock_query]

            # Test limit validation - service should cap large limits
            result = await service.get_verification_history(limit=200, offset=-5)

            # Service should validate and cap the limit at 100, set offset to 0
            assert result.limit == 100
            assert result.offset == 0
            assert result.verifications == []

    @patch(
        "src.verification_service.app.services.verification_history.VerificationResult.all"
    )
    async def test_get_verification_history_database_error(self, mock_all, service):
        mock_all.return_value.count = AsyncMock(side_effect=Exception("Database error"))

        result = await service.get_verification_history()

        assert result.verifications == []
        assert result.total_count == 0
        assert result.error == "Failed to retrieve verification history"

    @patch(
        "src.verification_service.app.services.verification_history.VerificationResult.filter"
    )
    async def test_get_verifications_by_modification_id_success(
        self, mock_filter, service
    ):
        modification_id = str(uuid.uuid4())

        mock_result1 = type("MockResult", (), {})()
        mock_result1.modification_id = uuid.UUID(modification_id)
        mock_result1.status = VerificationStatus.COMPLETED
        mock_result1.is_reversible = True
        mock_result1.verified_with_hash = True
        mock_result1.verified_with_pixels = True
        mock_result1.created_at = datetime.fromisoformat("2024-01-01T12:00:00+00:00")
        mock_result1.updated_at = datetime.fromisoformat("2024-01-01T12:01:00+00:00")

        mock_result2 = type("MockResult", (), {})()
        mock_result2.modification_id = uuid.UUID(modification_id)
        mock_result2.status = VerificationStatus.PENDING
        mock_result2.is_reversible = None
        mock_result2.verified_with_hash = None
        mock_result2.verified_with_pixels = None
        mock_result2.created_at = datetime.fromisoformat("2024-01-01T13:00:00+00:00")
        mock_result2.updated_at = None

        mock_query = type("MockQuery", (), {})()
        mock_query.order_by = AsyncMock(return_value=[mock_result1, mock_result2])
        mock_filter.return_value = mock_query

        result = await service.get_verifications_by_modification_id(modification_id)

        assert result.modification_id == modification_id
        assert result.total_count == 2
        assert len(result.verifications) == 2
        assert result.error is None

        verification1 = result.verifications[0]
        assert verification1.modification_id == modification_id
        assert verification1.status == "completed"
        assert verification1.is_reversible is True
        assert verification1.verified_with_hash is True
        assert verification1.verified_with_pixels is True

        verification2 = result.verifications[1]
        assert verification2.modification_id == modification_id
        assert verification2.status == "pending"
        assert verification2.is_reversible is None
        assert verification2.completed_at is None

    @patch(
        "src.verification_service.app.services.verification_history.VerificationResult.filter"
    )
    async def test_get_verifications_by_modification_id_empty(
        self, mock_filter, service
    ):
        modification_id = str(uuid.uuid4())

        mock_query = type("MockQuery", (), {})()
        mock_query.order_by = AsyncMock(return_value=[])
        mock_filter.return_value = mock_query

        result = await service.get_verifications_by_modification_id(modification_id)

        assert result.modification_id == modification_id
        assert result.total_count == 0
        assert len(result.verifications) == 0
        assert result.error is None

    async def test_get_verifications_by_modification_id_invalid_uuid(self, service):
        """Test getting verifications with invalid UUID."""
        invalid_id = "not-a-valid-uuid"

        result = await service.get_verifications_by_modification_id(invalid_id)

        assert result.modification_id == invalid_id
        assert result.total_count == 0
        assert len(result.verifications) == 0
        assert result.error == "Invalid modification ID format"

    @patch(
        "src.verification_service.app.services.verification_history.VerificationResult.filter"
    )
    async def test_get_verifications_by_modification_id_database_error(
        self, mock_filter, service
    ):
        modification_id = str(uuid.uuid4())

        mock_filter.side_effect = Exception("Database connection error")

        result = await service.get_verifications_by_modification_id(modification_id)

        assert result.modification_id == modification_id
        assert result.total_count == 0
        assert len(result.verifications) == 0
        assert result.error == "Failed to retrieve verifications for modification"

    @patch(
        "src.verification_service.app.services.verification_history.VerificationResult.filter"
    )
    async def test_get_verifications_by_modification_id_single_result(
        self, mock_filter, service
    ):
        modification_id = str(uuid.uuid4())

        mock_result = type("MockResult", (), {})()
        mock_result.modification_id = uuid.UUID(modification_id)
        mock_result.status = VerificationStatus.COMPLETED
        mock_result.is_reversible = False
        mock_result.verified_with_hash = True
        mock_result.verified_with_pixels = False
        mock_result.created_at = datetime.fromisoformat("2024-01-01T12:00:00+00:00")
        mock_result.updated_at = datetime.fromisoformat("2024-01-01T12:02:00+00:00")

        mock_query = type("MockQuery", (), {})()
        mock_query.order_by = AsyncMock(return_value=[mock_result])
        mock_filter.return_value = mock_query

        result = await service.get_verifications_by_modification_id(modification_id)

        assert result.modification_id == modification_id
        assert result.total_count == 1
        assert len(result.verifications) == 1
        assert result.error is None

        verification = result.verifications[0]
        assert verification.modification_id == modification_id
        assert verification.status == "completed"
        assert verification.is_reversible is False
        assert verification.verified_with_hash is True
        assert verification.verified_with_pixels is False
