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
