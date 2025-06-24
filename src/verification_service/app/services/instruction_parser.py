from typing import Any

from image_modification_algorithms.types import (
    Modification,
    ModificationAlgorithm,
    SerializableOperation,
)


class InstructionParseError(Exception):
    pass


class InstructionParser:
    def __init__(self):
        pass

    def parse_modification_instructions(
        self,
        algorithm: ModificationAlgorithm,
        image_mode: str,
        operations_data: list[dict[str, Any]],
    ) -> Modification:
        if not operations_data:
            return Modification(
                algorithm_type=algorithm.get_name(),
                image_mode=image_mode,
                operations=[],
            )

        parsed_operations: list[SerializableOperation] = []

        for i, op_data in enumerate(operations_data):
            try:
                operation = self._parse_single_operation(algorithm, op_data)
                parsed_operations.append(operation)
            except Exception as e:
                raise InstructionParseError(
                    f"Failed to parse operation {i}: {e}"
                ) from e

        return Modification(
            algorithm_type=algorithm.get_name(),
            image_mode=image_mode,
            operations=parsed_operations,
        )

    def _parse_single_operation(
        self, algorithm: ModificationAlgorithm, op_data: dict[str, Any]
    ) -> SerializableOperation:
        if not isinstance(op_data, dict):
            raise InstructionParseError(
                f"Operation data must be dict, got {type(op_data)}"
            )

        operation_class = algorithm.get_operation_class()

        try:
            return operation_class.from_dict(op_data)
        except Exception as e:
            raise InstructionParseError(
                f"Failed to deserialize {algorithm.get_name()} operation: {e}"
            ) from e

    def validate_operations_data(
        self, algorithm: ModificationAlgorithm, operations_data: list[dict[str, Any]]
    ) -> bool:
        if not isinstance(operations_data, list):
            return False

        for op_data in operations_data:
            if not isinstance(op_data, dict):
                return False

        return True
