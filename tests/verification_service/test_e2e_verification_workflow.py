import io
import uuid
from datetime import datetime
from unittest.mock import AsyncMock

from PIL import Image

from src.verification_service.app.models.verification_result import (
    VerificationResult,
    VerificationStatus,
)
from src.verification_service.app.schemas.verification import (
    ModificationInstructionData,
)
from tests.shared_fixtures import SharedImageFixtures


class TestVerificationWorkflowIntegration:
    async def test_complete_end_to_end_verification_cycle(
        self, test_client, test_container, tmp_path
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        image_data, filename = SharedImageFixtures.load_small_rgb_image()

        SharedImageFixtures.create_temp_image_file(
            tmp_path / "original", image_data, f"{image_id}_original.png"
        )

        image = Image.open(io.BytesIO(image_data))
        modified_image = image.copy()
        original_pixel = modified_image.getpixel((0, 0))
        new_pixel = (original_pixel[0] ^ 123, original_pixel[1], original_pixel[2])
        modified_image.putpixel((0, 0), new_pixel)

        variant_buffer = io.BytesIO()
        modified_image.save(variant_buffer, format="PNG")
        variant_file = SharedImageFixtures.create_temp_image_file(
            tmp_path / "variant", variant_buffer.getvalue(), f"{image_id}_variant_1.png"
        )

        modification_instructions = {
            "operations": [{"row": 0, "col": 0, "channel": 0, "parameter": 123}]
        }

        mock_instruction_data = ModificationInstructionData(
            modification_id=modification_id,
            image_id=image_id,
            original_filename=filename,
            variant_number=1,
            algorithm_type="xor_transform",
            instructions=modification_instructions,
            storage_path=str(variant_file),
            created_at=datetime.now(),
        )

        mock_retrieval_service = AsyncMock()
        mock_retrieval_service.get_modification_instructions.return_value = (
            mock_instruction_data
        )
        test_container.set_instruction_retrieval_service(mock_retrieval_service)

        request_payload = {
            "image_id": str(image_id),
            "modification_id": str(modification_id),
        }

        response = test_client.post("/internal/verify", json=request_payload)
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

        verification_record = await VerificationResult.filter(
            modification_id=modification_id
        ).first()
        assert verification_record is not None
        assert verification_record.status == VerificationStatus.COMPLETED

        status_response = test_client.get(f"/api/verification/{modification_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "completed"

        stats_response = test_client.get("/api/verification/statistics")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert "total_verifications" in stats_data
        assert "success_rate" in stats_data

        history_response = test_client.get("/api/verification/history")
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert "verifications" in history_data
        assert "total_count" in history_data

        mod_response = test_client.get(
            f"/api/verification/modifications/{modification_id}"
        )
        assert mod_response.status_code == 200
        mod_data = mod_response.json()
        assert mod_data["modification_id"] == str(modification_id)

        health_response = test_client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"

    async def test_verification_error_handling(self, test_client, test_container):
        invalid_payload = {"invalid": "data"}
        response = test_client.post("/internal/verify", json=invalid_payload)
        assert response.status_code == 422

        non_existent_id = uuid.uuid4()
        mock_retrieval_service = AsyncMock()
        mock_retrieval_service.get_modification_instructions.side_effect = Exception(
            "Modification not found"
        )
        test_container.set_instruction_retrieval_service(mock_retrieval_service)

        request_payload = {
            "image_id": str(uuid.uuid4()),
            "modification_id": str(non_existent_id),
        }

        response = test_client.post("/internal/verify", json=request_payload)
        assert (
            response.status_code == 200
        )  # Request accepted, error handled in background

        verification_record = await VerificationResult.filter(
            modification_id=non_existent_id
        ).first()
        assert verification_record is not None
        assert verification_record.status == VerificationStatus.COMPLETED
        assert verification_record.is_reversible is False  # Error results in False

    async def test_idempotent_verification_requests(
        self, test_client, test_container, tmp_path
    ):
        image_id = uuid.uuid4()
        modification_id = uuid.uuid4()

        image_data, _ = SharedImageFixtures.load_tiny_image()
        variant_file = tmp_path / "test_variant.jpg"
        variant_file.write_bytes(image_data)

        mock_instruction_data = ModificationInstructionData(
            modification_id=modification_id,
            image_id=image_id,
            original_filename="test_image.jpg",
            variant_number=1,
            algorithm_type="xor_transform",
            instructions={"operations": []},
            storage_path=str(variant_file),
            created_at=datetime.now(),
        )

        mock_retrieval_service = AsyncMock()
        mock_retrieval_service.get_modification_instructions.return_value = (
            mock_instruction_data
        )
        test_container.set_instruction_retrieval_service(mock_retrieval_service)

        request_payload = {
            "image_id": str(image_id),
            "modification_id": str(modification_id),
        }

        response1 = test_client.post("/internal/verify", json=request_payload)
        assert response1.status_code == 200

        response2 = test_client.post("/internal/verify", json=request_payload)
        assert response2.status_code == 200

        verification_records = await VerificationResult.filter(
            modification_id=modification_id
        ).all()
        assert len(verification_records) == 1

    async def test_concurrent_verification_handling(
        self, test_client, test_container, tmp_path
    ):
        def mock_get_instructions(image_id, modification_id):
            image_data, _ = SharedImageFixtures.load_tiny_image()
            variant_file = tmp_path / f"concurrent_variant_{modification_id}.jpg"
            variant_file.write_bytes(image_data)

            return ModificationInstructionData(
                modification_id=modification_id,
                image_id=image_id,
                original_filename="concurrent_test.jpg",
                variant_number=1,
                algorithm_type="xor_transform",
                instructions={"operations": []},
                storage_path=str(variant_file),
                created_at=datetime.now(),
            )

        mock_retrieval_service = AsyncMock()
        mock_retrieval_service.get_modification_instructions.side_effect = (
            mock_get_instructions
        )
        test_container.set_instruction_retrieval_service(mock_retrieval_service)

        image_id = uuid.uuid4()
        modification_ids = [uuid.uuid4() for _ in range(3)]

        responses = []
        for mod_id in modification_ids:
            request_payload = {
                "image_id": str(image_id),
                "modification_id": str(mod_id),
            }
            response = test_client.post("/internal/verify", json=request_payload)
            responses.append((mod_id, response))

        for mod_id, response in responses:
            assert response.status_code == 200
            assert response.json()["modification_id"] == str(mod_id)

        for mod_id, _ in responses:
            verification_record = await VerificationResult.filter(
                modification_id=mod_id
            ).first()
            assert verification_record is not None
            assert verification_record.status == VerificationStatus.COMPLETED
