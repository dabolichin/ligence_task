from unittest.mock import AsyncMock, patch

import pytest


class TestInstructionStorage:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "image_fixture,expected_mode,expected_channels",
        [
            ("small_sample_image", "RGB", 3),
            ("grayscale_image", "L", 1),
        ],
    )
    async def test_complete_instruction_storage(
        self,
        test_container,
        mock_file_storage,
        mock_modification_engine,
        request,
        mock_image_record,
        image_fixture,
        expected_mode,
        expected_channels,
    ):
        test_image = request.getfixturevalue(image_fixture)

        stored_instructions = []

        def capture_instructions(**kwargs):
            stored_instructions.append(kwargs.get("instructions"))
            mock_modification = AsyncMock()
            mock_modification.id = f"mod-{len(stored_instructions)}"
            return mock_modification

        mock_file_storage.save_variant_image.return_value = "/path/to/variant.jpg"

        test_container.set_file_storage(mock_file_storage)
        test_container.set_modification_engine(mock_modification_engine)
        variant_service = test_container.variant_generator

        with patch(
            "src.image_processing_service.app.services.variant_generation.Modification.create",
            side_effect=capture_instructions,
        ):
            variants = await variant_service.generate_variants(
                test_image, mock_image_record
            )

            assert len(variants) == 100
            assert len(stored_instructions) == 100

            instructions = stored_instructions[0]

            assert instructions["algorithm_type"] == "xor_transform"
            assert instructions["image_mode"] == expected_mode
            assert isinstance(instructions["operations"], list)
            assert len(instructions["operations"]) >= 1

            first_op = instructions["operations"][0]
            assert "row" in first_op
            assert "col" in first_op
            assert "parameter" in first_op

            for op in instructions["operations"]:
                assert isinstance(op["row"], int)
                assert isinstance(op["col"], int)
                assert isinstance(op["parameter"], int)
                assert 0 <= op["row"] < test_image.height
                assert 0 <= op["col"] < test_image.width
                assert 1 <= op["parameter"] <= 255

                if expected_mode == "RGB":
                    assert "channel" in op
                    assert 0 <= op["channel"] < expected_channels
                else:
                    assert "channel" not in op or op["channel"] is None
