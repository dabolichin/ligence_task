from PIL import Image

from .types import (
    Modification,
    ModificationAlgorithm,
    ModificationResult,
)
from .xor_transform import XORTransformAlgorithm


class ModificationEngine:
    def __init__(self):
        self._algorithms: dict[str, ModificationAlgorithm] = {
            "xor_transform": XORTransformAlgorithm(),
        }

    def get_available_algorithms(self) -> list[str]:
        return list(self._algorithms.keys())

    def parse_instruction_data(self, instruction_data) -> Modification:
        algorithm_name = getattr(instruction_data, "algorithm_type", None)
        if not algorithm_name:
            raise ValueError("instruction_data must have 'algorithm_type' attribute")

        if algorithm_name not in self._algorithms:
            raise ValueError(f"Unknown algorithm: {algorithm_name}")

        algorithm = self._algorithms[algorithm_name]
        operation_class = algorithm.get_operation_class()

        instructions = getattr(instruction_data, "instructions", {})
        if not isinstance(instructions, dict):
            raise ValueError("instruction_data.instructions must be a dictionary")

        # TODO: Remove these defaults
        operations_data = instructions.get("operations", [])
        image_mode = instructions.get("image_mode", "RGB")

        parsed_operations = []
        for op_data in operations_data:
            parsed_operations.append(operation_class.from_dict(op_data))

        return Modification(
            algorithm_type=algorithm_name,
            image_mode=image_mode,
            operations=parsed_operations,
        )

    def apply_modifications(
        self,
        image: Image.Image,
        algorithm_name: str,
        num_modifications: int,
        seed: int | None = None,
    ) -> ModificationResult:
        if algorithm_name not in self._algorithms:
            raise ValueError(f"Unknown algorithm: {algorithm_name}")

        # Create algorithm instance with seed if provided
        if seed is not None and algorithm_name == "xor_transform":
            algorithm = XORTransformAlgorithm(seed=seed)
        else:
            algorithm = self._algorithms[algorithm_name]

        return algorithm.apply_modifications(image, num_modifications)

    def reverse_modifications(
        self,
        modified_image: Image.Image,
        instructions: Modification,
    ) -> Image.Image:
        algorithm_type = instructions.algorithm_type

        if algorithm_type not in self._algorithms:
            raise ValueError(f"Unknown algorithm type: {algorithm_type}")

        # Use the algorithm class for reverse operations (static method)
        if algorithm_type == "xor_transform":
            return XORTransformAlgorithm.reverse_modifications(
                modified_image, instructions
            )

        raise ValueError(f"Reverse operation not implemented for: {algorithm_type}")


# Create a singleton instance for the service to use
modification_engine = ModificationEngine()
