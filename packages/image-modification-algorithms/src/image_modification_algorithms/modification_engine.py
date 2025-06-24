from typing import Optional

from PIL import Image

from .xor_transform import (
    Modification,
    ModificationResult,
    XORTransformAlgorithm,
)


class ModificationEngine:
    def __init__(self):
        self._xor_algorithm = XORTransformAlgorithm()

    def get_available_algorithms(self) -> list[str]:
        return ["xor_transform"]

    def apply_modifications(
        self,
        image: Image.Image,
        algorithm_name: str,
        num_modifications: int,
        seed: Optional[int] = None,
    ) -> ModificationResult:
        if algorithm_name not in self.get_available_algorithms():
            raise ValueError(f"Unknown algorithm: {algorithm_name}")

        if algorithm_name == "xor_transform":
            if seed is not None:
                algorithm = XORTransformAlgorithm(seed=seed)
            else:
                algorithm = self._xor_algorithm
            return algorithm.apply_modifications(image, num_modifications)

        raise ValueError(f"Algorithm not implemented: {algorithm_name}")

    def reverse_modifications(
        self,
        modified_image: Image.Image,
        instructions: Modification,
    ) -> Image.Image:
        algorithm_type = instructions.algorithm_type

        if algorithm_type == "xor_transform":
            return XORTransformAlgorithm.reverse_modifications(
                modified_image, instructions
            )

        raise ValueError(f"Unknown algorithm type: {algorithm_type}")


# Create a singleton instance for the service to use
modification_engine = ModificationEngine()
