from dataclasses import dataclass
from typing import Any

import pytest
from image_modification_algorithms.types import (
    Modification,
    PixelOperation,
    SerializableOperation,
)

from src.verification_service.app.services.instruction_parser import (
    InstructionParseError,
)


@dataclass
class MockOperation(SerializableOperation):
    value: int

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MockOperation":
        return cls(data["value"])


class TestInstructionParser:
    def test_parse_empty_operations(self, instruction_parser, mock_xor_algorithm):
        mock_xor_algorithm.get_name.return_value = "test_algorithm"

        result = instruction_parser.parse_modification_instructions(
            algorithm=mock_xor_algorithm,
            image_mode="RGB",
            operations_data=[],
        )

        assert isinstance(result, Modification)
        assert result.algorithm_type == "test_algorithm"
        assert result.image_mode == "RGB"
        assert result.operations == []

    def test_parse_pixel_operations_success(
        self, instruction_parser, mock_xor_algorithm, sample_pixel_operations_data
    ):
        result = instruction_parser.parse_modification_instructions(
            algorithm=mock_xor_algorithm,
            image_mode="RGB",
            operations_data=sample_pixel_operations_data,
        )

        assert isinstance(result, Modification)
        assert result.algorithm_type == "xor_transform"
        assert result.image_mode == "RGB"
        assert len(result.operations) == 3

        op1 = result.operations[0]
        assert isinstance(op1, PixelOperation)
        assert op1.row == 10
        assert op1.col == 20
        assert op1.channel == 1
        assert op1.parameter == 255

        op2 = result.operations[1]
        assert isinstance(op2, PixelOperation)
        assert op2.row == 5
        assert op2.col == 8
        assert op2.channel == 0
        assert op2.parameter == 128

        op3 = result.operations[2]
        assert isinstance(op3, PixelOperation)
        assert op3.row == 15
        assert op3.col == 25
        assert op3.channel is None
        assert op3.parameter == 0

    def test_parse_grayscale_operations(
        self, instruction_parser, mock_xor_algorithm, sample_grayscale_operations_data
    ):
        result = instruction_parser.parse_modification_instructions(
            algorithm=mock_xor_algorithm,
            image_mode="L",
            operations_data=sample_grayscale_operations_data,
        )

        assert result.image_mode == "L"
        assert len(result.operations) == 2

        for op in result.operations:
            assert isinstance(op, PixelOperation)
            assert op.channel is None  # Grayscale operations

    def test_parse_with_custom_operation_class(
        self, instruction_parser, sample_custom_operations_data
    ):
        from unittest.mock import Mock

        mock_custom_algorithm = Mock()
        mock_custom_algorithm.get_name.return_value = "custom_algorithm"
        mock_custom_algorithm.get_operation_class.return_value = MockOperation

        result = instruction_parser.parse_modification_instructions(
            algorithm=mock_custom_algorithm,
            image_mode="RGB",
            operations_data=sample_custom_operations_data,
        )

        assert result.algorithm_type == "custom_algorithm"
        assert len(result.operations) == 2

        op1 = result.operations[0]
        assert isinstance(op1, MockOperation)
        assert op1.value == 42

        op2 = result.operations[1]
        assert isinstance(op2, MockOperation)
        assert op2.value == 100

    def test_parse_invalid_operation_data_type(
        self, instruction_parser, mock_xor_algorithm
    ):
        mock_xor_algorithm.get_name.return_value = "test_algorithm"

        operations_data = [
            {"row": 10, "col": 20},
            "invalid_data",  # Not a dict
        ]

        with pytest.raises(InstructionParseError, match="Operation data must be dict"):
            instruction_parser.parse_modification_instructions(
                algorithm=mock_xor_algorithm,
                image_mode="RGB",
                operations_data=operations_data,
            )

    def test_parse_operation_deserialization_error(
        self, instruction_parser, mock_xor_algorithm
    ):
        mock_xor_algorithm.get_name.return_value = "test_algorithm"

        operations_data = [
            {"invalid_field": "value"},  # Missing required fields
        ]

        with pytest.raises(InstructionParseError, match="Failed to parse operation 0"):
            instruction_parser.parse_modification_instructions(
                algorithm=mock_xor_algorithm,
                image_mode="RGB",
                operations_data=operations_data,
            )

    def test_parse_multiple_operation_errors(
        self, instruction_parser, mock_xor_algorithm
    ):
        mock_xor_algorithm.get_name.return_value = "test_algorithm"

        operations_data = [
            {"row": 10, "col": 20},  # Valid
            {"invalid": "data"},  # Invalid - should fail here
            {"also_invalid": "data"},  # This won't be reached
        ]

        with pytest.raises(InstructionParseError, match="Failed to parse operation 1"):
            instruction_parser.parse_modification_instructions(
                algorithm=mock_xor_algorithm,
                image_mode="RGB",
                operations_data=operations_data,
            )

    def test_validate_operations_data_success(
        self, instruction_parser, mock_xor_algorithm
    ):
        operations_data = [
            {"row": 10, "col": 20, "channel": 1, "parameter": 255},
            {"row": 5, "col": 8},
        ]

        result = instruction_parser.validate_operations_data(
            algorithm=mock_xor_algorithm,
            operations_data=operations_data,
        )

        assert result is True

    def test_validate_operations_data_not_list(
        self, instruction_parser, mock_xor_algorithm
    ):
        result = instruction_parser.validate_operations_data(
            algorithm=mock_xor_algorithm,
            operations_data="not_a_list",
        )

        assert result is False

    def test_validate_operations_data_invalid_operation(
        self, instruction_parser, mock_xor_algorithm
    ):
        operations_data = [
            {"row": 10, "col": 20},  # Valid
            "not_a_dict",  # Invalid
        ]

        result = instruction_parser.validate_operations_data(
            algorithm=mock_xor_algorithm,
            operations_data=operations_data,
        )

        assert result is False

    def test_validate_empty_operations_data(
        self, instruction_parser, mock_xor_algorithm
    ):
        result = instruction_parser.validate_operations_data(
            algorithm=mock_xor_algorithm,
            operations_data=[],
        )

        assert result is True

    def test_error_message_includes_algorithm_name(
        self, instruction_parser, mock_xor_algorithm
    ):
        mock_xor_algorithm.get_name.return_value = "custom_test_algorithm"

        operations_data = [
            {"missing_required_fields": "value"},
        ]

        with pytest.raises(
            InstructionParseError, match="custom_test_algorithm operation"
        ):
            instruction_parser.parse_modification_instructions(
                algorithm=mock_xor_algorithm,
                image_mode="RGB",
                operations_data=operations_data,
            )

    def test_parse_preserves_operation_order(
        self, instruction_parser, mock_xor_algorithm
    ):
        operations_data = [
            {"row": 1, "col": 1, "parameter": 10},
            {"row": 2, "col": 2, "parameter": 20},
            {"row": 3, "col": 3, "parameter": 30},
            {"row": 4, "col": 4, "parameter": 40},
        ]

        result = instruction_parser.parse_modification_instructions(
            algorithm=mock_xor_algorithm,
            image_mode="RGB",
            operations_data=operations_data,
        )

        # Check that operations are in the same order
        for i, op in enumerate(result.operations):
            assert op.row == i + 1
            assert op.col == i + 1
            assert op.parameter == (i + 1) * 10

    def test_parse_large_number_of_operations(
        self, instruction_parser, mock_xor_algorithm
    ):
        operations_data = [
            {"row": i, "col": i, "parameter": i % 256} for i in range(1000)
        ]

        result = instruction_parser.parse_modification_instructions(
            algorithm=mock_xor_algorithm,
            image_mode="RGB",
            operations_data=operations_data,
        )

        assert len(result.operations) == 1000
        assert all(isinstance(op, PixelOperation) for op in result.operations)

        assert result.operations[0].row == 0
        assert result.operations[999].row == 999
        assert result.operations[500].parameter == 500 % 256
