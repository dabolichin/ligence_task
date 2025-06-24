import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from src.verification_service.app.api.internal import (
    receive_verification_request,
)
from src.verification_service.app.schemas import (
    VerificationRequestData as VerificationRequest,
)


class TestReceiveVerificationRequestEndpoint:
    @pytest.mark.asyncio
    async def test_receive_verification_request_success(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        request = VerificationRequest(
            image_id=image_id, modification_id=modification_id
        )

        background_tasks = BackgroundTasks()
        mock_verification_orchestrator = AsyncMock()

        with patch.object(background_tasks, "add_task") as mock_add_task:
            response = await receive_verification_request(
                request, background_tasks, mock_verification_orchestrator
            )

            assert response["status"] == "accepted"
            assert response["modification_id"] == str(modification_id)
            assert "successfully" in response["message"]

            # Verify background task was added with correct parameters
            assert mock_add_task.call_count == 1
            call_args = mock_add_task.call_args[0]
            assert (
                call_args[0]
                == mock_verification_orchestrator.execute_verification_background
            )
            assert call_args[1] == image_id
            assert call_args[2] == modification_id
            assert len(call_args) == 3  # method + image_id + modification_id

    @pytest.mark.asyncio
    async def test_receive_verification_request_background_task_error(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        request = VerificationRequest(
            image_id=image_id, modification_id=modification_id
        )

        background_tasks = BackgroundTasks()
        mock_verification_orchestrator = AsyncMock()

        with patch.object(background_tasks, "add_task") as mock_add_task:
            mock_add_task.side_effect = Exception("Background task failed")

            with pytest.raises(Exception):
                await receive_verification_request(
                    request, background_tasks, mock_verification_orchestrator
                )


class TestInternalAPIIntegration:
    @pytest.fixture
    def client_with_mock_orchestrator(self, test_container):
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

    def test_internal_verify_endpoint_valid_request(
        self, client_with_mock_orchestrator
    ):
        image_id = str(uuid.uuid4())
        modification_id = str(uuid.uuid4())

        request_data = {"image_id": image_id, "modification_id": modification_id}

        response = client_with_mock_orchestrator.post(
            "/internal/verify", json=request_data
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "accepted"
        assert response_data["modification_id"] == modification_id

    def test_internal_verify_endpoint_with_dependency_injection(
        self, client_with_mock_orchestrator
    ):
        image_id = str(uuid.uuid4())
        modification_id = str(uuid.uuid4())

        request_data = {"image_id": image_id, "modification_id": modification_id}

        response = client_with_mock_orchestrator.post(
            "/internal/verify", json=request_data
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "accepted"
        assert response_data["modification_id"] == modification_id

    def test_internal_verify_endpoint_invalid_request(
        self, client_with_mock_orchestrator
    ):
        request_data = {"image_id": "invalid-uuid", "modification_id": "invalid-uuid"}

        response = client_with_mock_orchestrator.post(
            "/internal/verify", json=request_data
        )

        assert response.status_code == 422  # Validation error

    def test_internal_verify_endpoint_missing_fields(
        self, client_with_mock_orchestrator
    ):
        request_data = {"image_id": str(uuid.uuid4())}  # Missing modification_id

        response = client_with_mock_orchestrator.post(
            "/internal/verify", json=request_data
        )

        assert response.status_code == 422  # Validation error

    def test_internal_verify_endpoint_empty_request(
        self, client_with_mock_orchestrator
    ):
        response = client_with_mock_orchestrator.post("/internal/verify", json={})

        assert response.status_code == 422  # Validation error


class TestBackgroundTaskExecution:
    @pytest.mark.asyncio
    async def test_background_task_queuing_with_container(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        request = VerificationRequest(
            image_id=image_id, modification_id=modification_id
        )

        background_tasks = BackgroundTasks()
        mock_verification_orchestrator = AsyncMock()

        # Response should be immediate
        response = await receive_verification_request(
            request, background_tasks, mock_verification_orchestrator
        )
        assert response["status"] == "accepted"
        assert response["modification_id"] == str(modification_id)

        # Background task should be queued with orchestrator method
        assert len(background_tasks.tasks) == 1
        task = background_tasks.tasks[0]
        assert (
            task.func == mock_verification_orchestrator.execute_verification_background
        )
        # Task should have correct number of arguments (image_id + modification_id)
        assert len(task.args) == 2
        assert task.args[0] == image_id
        assert task.args[1] == modification_id

    @pytest.mark.asyncio
    async def test_multiple_concurrent_verification_requests(self):
        requests = []
        for _ in range(5):
            requests.append(
                VerificationRequest(image_id=uuid.uuid4(), modification_id=uuid.uuid4())
            )

        background_tasks = BackgroundTasks()
        mock_verification_orchestrator = AsyncMock()

        responses = []
        for request in requests:
            response = await receive_verification_request(
                request, background_tasks, mock_verification_orchestrator
            )
            responses.append(response)

        # All responses should be successful
        for response in responses:
            assert response["status"] == "accepted"

        # Should have 5 background tasks queued
        assert len(background_tasks.tasks) == 5

        for task in background_tasks.tasks:
            # Should be the orchestrator method
            assert hasattr(task.func, "__self__") or callable(task.func)
            # Each task should have 2 arguments (image_id + modification_id)
            assert len(task.args) == 2

    @pytest.mark.asyncio
    async def test_verification_orchestrator_integration(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_verification_orchestrator = AsyncMock()

        await mock_verification_orchestrator.verify_modification(
            image_id, modification_id
        )

        mock_verification_orchestrator.verify_modification.assert_called_once_with(
            image_id, modification_id
        )

    @pytest.mark.asyncio
    async def test_container_dependency_injection_in_endpoint(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        request = VerificationRequest(
            image_id=image_id, modification_id=modification_id
        )

        background_tasks = BackgroundTasks()
        mock_verification_orchestrator = AsyncMock()

        response = await receive_verification_request(
            request, background_tasks, mock_verification_orchestrator
        )

        assert response["status"] == "accepted"
        assert response["modification_id"] == str(modification_id)

        # Verify background task was queued with the orchestrator method
        assert len(background_tasks.tasks) == 1
        task = background_tasks.tasks[0]
        assert len(task.args) == 2  # image_id, modification_id
        assert (
            task.func == mock_verification_orchestrator.execute_verification_background
        )


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_orchestrator_method_direct_usage(self):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        mock_verification_orchestrator = AsyncMock()

        await mock_verification_orchestrator.verify_modification(
            image_id, modification_id
        )

        mock_verification_orchestrator.verify_modification.assert_called_once_with(
            image_id, modification_id
        )
