import numpy as np
import pytest
from image_modification_algorithms import (
    Modification,
    ModificationEngine,
    ModificationResult,
    PixelOperation,
)
from PIL import Image


class MockInstructionData:
    def __init__(self, algorithm_type, instructions):
        self.algorithm_type = algorithm_type
        self.instructions = instructions


class TestModificationEngine:
    def test_apply_modifications_xor_transform_rgb(self):
        engine = ModificationEngine()
        rgb_image = Image.fromarray(
            np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8), mode="RGB"
        )

        result = engine.apply_modifications(rgb_image, "xor_transform", 5)

        assert isinstance(result, ModificationResult)
        assert isinstance(result.modified_image, Image.Image)
        assert isinstance(result.instructions, Modification)
        assert result.instructions.algorithm_type == "xor_transform"
        assert len(result.instructions.operations) == 5

    def test_apply_modifications_with_seed(self):
        engine = ModificationEngine()
        rgb_image = Image.fromarray(
            np.array([[[100, 150, 200]]], dtype=np.uint8), mode="RGB"
        )
        seed = 42

        result1 = engine.apply_modifications(rgb_image, "xor_transform", 1, seed=seed)
        result2 = engine.apply_modifications(rgb_image, "xor_transform", 1, seed=seed)

        # Results should be identical with same seed
        assert np.array_equal(
            np.array(result1.modified_image), np.array(result2.modified_image)
        )
        assert result1.instructions.operations == result2.instructions.operations

    def test_apply_modifications_invalid_algorithm(self):
        engine = ModificationEngine()
        rgb_image = Image.fromarray(
            np.random.randint(0, 256, (5, 5, 3), dtype=np.uint8), mode="RGB"
        )

        with pytest.raises(ValueError, match="Unknown algorithm: invalid_algo"):
            engine.apply_modifications(rgb_image, "invalid_algo", 5)

    def test_reverse_modifications_xor_transform(self):
        engine = ModificationEngine()
        original_image = Image.fromarray(
            np.array([[[100, 150, 200], [50, 75, 125]]], dtype=np.uint8), mode="RGB"
        )

        result = engine.apply_modifications(original_image, "xor_transform", 2)

        restored_image = engine.reverse_modifications(
            result.modified_image, result.instructions
        )

        assert np.array_equal(np.array(original_image), np.array(restored_image))
        assert restored_image.mode == original_image.mode
        assert restored_image.size == original_image.size

    def test_reverse_modifications_invalid_algorithm_type(self):
        engine = ModificationEngine()
        rgb_image = Image.fromarray(
            np.random.randint(0, 256, (5, 5, 3), dtype=np.uint8), mode="RGB"
        )

        invalid_instructions = Modification(
            algorithm_type="invalid_algo",
            image_mode="RGB",
            operations=[PixelOperation(row=0, col=0, channel=0, parameter=128)],
        )

        with pytest.raises(ValueError, match="Unknown algorithm type: invalid_algo"):
            engine.reverse_modifications(rgb_image, invalid_instructions)

    def test_end_to_end_modification_cycle(self):
        engine = ModificationEngine()
        test_cases = [
            Image.fromarray(
                np.array([[[255, 0, 128], [64, 192, 32]]], dtype=np.uint8), mode="RGB"
            ),
            Image.fromarray(
                np.array([[100, 200], [50, 150]], dtype=np.uint8), mode="L"
            ),
        ]

        for original_image in test_cases:
            result = engine.apply_modifications(original_image, "xor_transform", 3)

            assert not np.array_equal(
                np.array(original_image), np.array(result.modified_image)
            )

            restored_image = engine.reverse_modifications(
                result.modified_image, result.instructions
            )

            assert np.array_equal(np.array(original_image), np.array(restored_image))
            assert restored_image.mode == original_image.mode
            assert restored_image.size == original_image.size

    def test_parse_instruction_data_xor_transform(self):
        engine = ModificationEngine()

        operations_data = [
            {"row": 0, "col": 0, "channel": 0, "parameter": 123},
            {"row": 1, "col": 1, "channel": 1, "parameter": 45},
            {"row": 2, "col": 2, "parameter": 78},  # Grayscale operation
        ]

        instruction_data = MockInstructionData(
            algorithm_type="xor_transform",
            instructions={"operations": operations_data, "image_mode": "RGB"},
        )

        result = engine.parse_instruction_data(instruction_data)

        assert isinstance(result, Modification)
        assert result.algorithm_type == "xor_transform"
        assert result.image_mode == "RGB"
        assert len(result.operations) == 3

        op1 = result.operations[0]
        assert isinstance(op1, PixelOperation)
        assert op1.row == 0
        assert op1.col == 0
        assert op1.channel == 0
        assert op1.parameter == 123

        op3 = result.operations[2]
        assert op3.row == 2
        assert op3.col == 2
        assert op3.channel is None
        assert op3.parameter == 78

    def test_parse_instruction_data_empty_list(self):
        engine = ModificationEngine()

        instruction_data = MockInstructionData(
            algorithm_type="xor_transform",
            instructions={"operations": [], "image_mode": "L"},
        )

        result = engine.parse_instruction_data(instruction_data)

        assert isinstance(result, Modification)
        assert result.algorithm_type == "xor_transform"
        assert result.image_mode == "L"
        assert len(result.operations) == 0

    def test_parse_instruction_data_default_image_mode(self):
        engine = ModificationEngine()

        operations_data = [{"row": 5, "col": 10, "channel": 2, "parameter": 200}]

        instruction_data = MockInstructionData(
            algorithm_type="xor_transform",
            instructions={
                "operations": operations_data
            },  # No image_mode - should default to "RGB"
        )

        result = engine.parse_instruction_data(instruction_data)

        assert result.image_mode == "RGB"
        assert len(result.operations) == 1
        assert result.operations[0].parameter == 200

    def test_parse_instruction_data_unknown_algorithm(self):
        engine = ModificationEngine()

        instruction_data = MockInstructionData(
            algorithm_type="unknown_algo",
            instructions={"operations": [], "image_mode": "RGB"},
        )

        with pytest.raises(ValueError, match="Unknown algorithm: unknown_algo"):
            engine.parse_instruction_data(instruction_data)

    def test_parse_instruction_data_invalid_operation_data(self):
        engine = ModificationEngine()

        invalid_operations_data = [{"col": 0, "channel": 0, "parameter": 123}]

        instruction_data = MockInstructionData(
            algorithm_type="xor_transform",
            instructions={"operations": invalid_operations_data, "image_mode": "RGB"},
        )

        with pytest.raises(KeyError):
            engine.parse_instruction_data(instruction_data)

    def test_parse_instruction_data_preserves_order(self):
        engine = ModificationEngine()

        operations_data = [
            {"row": 5, "col": 5, "channel": 0, "parameter": 100},
            {"row": 1, "col": 1, "channel": 1, "parameter": 200},
            {"row": 3, "col": 3, "channel": 2, "parameter": 150},
        ]

        instruction_data = MockInstructionData(
            algorithm_type="xor_transform",
            instructions={"operations": operations_data, "image_mode": "RGB"},
        )

        result = engine.parse_instruction_data(instruction_data)

        assert len(result.operations) == 3

        assert result.operations[0].row == 5 and result.operations[0].parameter == 100
        assert result.operations[1].row == 1 and result.operations[1].parameter == 200
        assert result.operations[2].row == 3 and result.operations[2].parameter == 150

    def test_parse_instruction_data_missing_algorithm_type(self):
        engine = ModificationEngine()

        instruction_data = MockInstructionData(
            algorithm_type=None,
            instructions={"operations": [], "image_mode": "RGB"},
        )
        instruction_data.algorithm_type = None

        with pytest.raises(
            ValueError, match="instruction_data must have 'algorithm_type' attribute"
        ):
            engine.parse_instruction_data(instruction_data)

    def test_parse_instruction_data_invalid_instructions_type(self):
        engine = ModificationEngine()

        instruction_data = MockInstructionData(
            algorithm_type="xor_transform",
            instructions="not_a_dict",
        )

        with pytest.raises(
            ValueError, match="instruction_data.instructions must be a dictionary"
        ):
            engine.parse_instruction_data(instruction_data)
