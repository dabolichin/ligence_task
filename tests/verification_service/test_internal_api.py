import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from src.verification_service.app.api.internal import (
    VerificationRequest,
    process_verification,
    receive_verification_request,
)
from src.verification_service.app.models.verification_result import (
    VerificationResult,
    VerificationStatus,
)


class TestProcessVerificationBackgroundTask:
    @pytest.mark.asyncio
    async def test_process_verification_new_record(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_result = AsyncMock()
        mock_result.status = VerificationStatus.PENDING
        mock_result.save = AsyncMock()

        mock_filter_calls = [
            AsyncMock(first=AsyncMock(return_value=None)),  # First call - no existing
            AsyncMock(
                first=AsyncMock(return_value=mock_result)
            ),  # Second call - found result
        ]

        with patch.object(VerificationResult, "filter", side_effect=mock_filter_calls):
            with patch.object(
                VerificationResult, "create", return_value=mock_result
            ) as mock_create:
                await process_verification(image_id, modification_id)

                mock_create.assert_called_once_with(
                    modification_id=modification_id,
                    status=VerificationStatus.PENDING,
                )

                assert mock_result.status == VerificationStatus.COMPLETED
                assert mock_result.is_reversible is True
                assert mock_result.verified_with_hash is True
                assert mock_result.verified_with_pixels is True
                mock_result.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_verification_existing_record(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        existing_result = AsyncMock()
        existing_result.modification_id = modification_id

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first.return_value = existing_result

            with patch.object(VerificationResult, "create") as mock_create:
                await process_verification(image_id, modification_id)

                mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_verification_database_error(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.side_effect = Exception("Database connection failed")

            # Should not raise exception, handle gracefully
            await process_verification(image_id, modification_id)

    @pytest.mark.asyncio
    async def test_process_verification_create_error(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first.return_value = None

            with patch.object(VerificationResult, "create") as mock_create:
                mock_create.side_effect = Exception("Failed to create record")

                # Should not raise exception, handle gracefully
                await process_verification(image_id, modification_id)

    @pytest.mark.asyncio
    async def test_process_verification_save_error(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first.return_value = None

            with patch.object(VerificationResult, "create") as mock_create:
                mock_result = AsyncMock()
                mock_result.save.side_effect = Exception("Failed to save")
                mock_create.return_value = mock_result

                with patch.object(VerificationResult, "filter") as mock_filter2:
                    mock_filter2.return_value.first.return_value = mock_result

                    # Should not raise exception, handle gracefully
                    await process_verification(image_id, modification_id)


class TestReceiveVerificationRequestEndpoint:
    @pytest.mark.asyncio
    async def test_receive_verification_request_success(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        request = VerificationRequest(
            image_id=image_id, modification_id=modification_id
        )

        background_tasks = BackgroundTasks()

        with patch.object(background_tasks, "add_task") as mock_add_task:
            response = await receive_verification_request(request, background_tasks)

            assert response["status"] == "accepted"
            assert response["modification_id"] == str(modification_id)
            assert "successfully" in response["message"]

            mock_add_task.assert_called_once_with(
                process_verification, image_id, modification_id
            )

    @pytest.mark.asyncio
    async def test_receive_verification_request_background_task_error(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        request = VerificationRequest(
            image_id=image_id, modification_id=modification_id
        )

        background_tasks = BackgroundTasks()

        with patch.object(background_tasks, "add_task") as mock_add_task:
            mock_add_task.side_effect = Exception("Background task failed")

            with pytest.raises(Exception):
                await receive_verification_request(request, background_tasks)


class TestInternalAPIIntegration:
    @pytest.fixture
    def client(self):
        import os
        import sys

        # Add the verification service directory to Python path
        verification_service_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "src", "verification_service"
        )
        if verification_service_path not in sys.path:
            sys.path.insert(0, verification_service_path)

        from main import create_app

        app = create_app()
        return TestClient(app)

    def test_internal_verify_endpoint_valid_request(self, client):
        image_id = str(uuid.uuid4())
        modification_id = str(uuid.uuid4())

        request_data = {"image_id": image_id, "modification_id": modification_id}

        with patch("src.verification_service.app.api.internal.process_verification"):
            response = client.post("/internal/verify", json=request_data)

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "accepted"
            assert response_data["modification_id"] == modification_id

    def test_internal_verify_endpoint_invalid_request(self, client):
        request_data = {"image_id": "invalid-uuid", "modification_id": "invalid-uuid"}

        response = client.post("/internal/verify", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_internal_verify_endpoint_missing_fields(self, client):
        request_data = {"image_id": str(uuid.uuid4())}  # Missing modification_id

        response = client.post("/internal/verify", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_internal_verify_endpoint_empty_request(self, client):
        response = client.post("/internal/verify", json={})

        assert response.status_code == 422  # Validation error


class TestBackgroundTaskExecution:
    @pytest.mark.asyncio
    async def test_background_task_queuing(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        request = VerificationRequest(
            image_id=image_id, modification_id=modification_id
        )

        background_tasks = BackgroundTasks()

        # Response should be immediate
        response = await receive_verification_request(request, background_tasks)
        assert response["status"] == "accepted"
        assert response["modification_id"] == str(modification_id)

        # Background task should be queued
        assert len(background_tasks.tasks) == 1
        task = background_tasks.tasks[0]
        assert task.func.__name__ == "process_verification"

    @pytest.mark.asyncio
    async def test_multiple_concurrent_verification_requests(self):
        requests = []
        for _ in range(5):
            requests.append(
                VerificationRequest(image_id=uuid.uuid4(), modification_id=uuid.uuid4())
            )

        background_tasks = BackgroundTasks()

        with patch("src.verification_service.app.api.internal.process_verification"):
            responses = []
            for request in requests:
                response = await receive_verification_request(request, background_tasks)
                responses.append(response)

            # All responses should be successful
            for response in responses:
                assert response["status"] == "accepted"

            # Should have 5 background tasks queued
            assert len(background_tasks.tasks) == 5

    @pytest.mark.asyncio
    async def test_verification_request_idempotency(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        existing_result = AsyncMock()
        existing_result.modification_id = modification_id

        with patch.object(VerificationResult, "filter") as mock_filter:
            mock_filter.return_value.first.return_value = existing_result

            # Process the same request twice
            await process_verification(image_id, modification_id)
            await process_verification(image_id, modification_id)

            # Should only check for existing record, not create new ones
            assert mock_filter.call_count >= 2

            with patch.object(VerificationResult, "create") as mock_create:
                await process_verification(image_id, modification_id)
                mock_create.assert_not_called()
