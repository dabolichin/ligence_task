import random

import numpy as np
from PIL import Image

from .types import (
    Modification,
    ModificationAlgorithm,
    ModificationResult,
    PixelOperation,
)


class XORTransformAlgorithm(ModificationAlgorithm):
    def __init__(self, seed: int | None = None):
        if seed is not None:
            self.rng = random.Random(seed)
        else:
            self.rng = random

    def apply_modifications(
        self, image: Image.Image, num_modifications: int
    ) -> ModificationResult:
        # Input validation
        if not isinstance(image, Image.Image):
            raise ValueError("Input must be a PIL Image")

        num_modifications = max(0, num_modifications)

        img_array = np.array(image)
        height, width = img_array.shape[:2]
        channels = img_array.shape[2] if len(img_array.shape) == 3 else 1

        max_pixels = height * width * channels
        num_modifications = min(num_modifications, max_pixels)

        operations = self._generate_random_operations(
            height, width, channels, num_modifications
        )

        modified_array = XORTransformAlgorithm._apply_xor_modifications(
            img_array, operations
        )

        modified_image = Image.fromarray(
            modified_array.astype(np.uint8), mode=image.mode
        )

        instructions = Modification(
            algorithm_type="xor_transform",
            image_mode=image.mode,
            operations=operations,
        )

        return ModificationResult(
            modified_image=modified_image, instructions=instructions
        )

    @staticmethod
    def reverse_modifications(
        modified_image: Image.Image, instructions: Modification
    ) -> Image.Image:
        if not isinstance(modified_image, Image.Image):
            raise ValueError("Input must be a PIL Image")

        if not hasattr(instructions, "operations") or instructions.operations is None:
            raise ValueError("Modification data must contain operations")

        img_array = np.array(modified_image)
        operations = instructions.operations
        restored_array = XORTransformAlgorithm._apply_xor_modifications(
            img_array, operations
        )

        restored_image = Image.fromarray(
            restored_array.astype(np.uint8), mode=modified_image.mode
        )

        return restored_image

    def get_name(self) -> str:
        return "xor_transform"

    def get_operation_class(self) -> type[PixelOperation]:
        return PixelOperation

    def _generate_random_operations(
        self, height: int, width: int, channels: int, num_modifications: int
    ) -> list[PixelOperation]:
        operations = []

        for _ in range(num_modifications):
            row = self.rng.randint(0, height - 1)
            col = self.rng.randint(0, width - 1)
            parameter = self.rng.randint(1, 255)

            if channels > 1:
                channel = self.rng.randint(0, channels - 1)
                operations.append(PixelOperation(row, col, channel, parameter))
            else:
                operations.append(PixelOperation(row, col, parameter=parameter))

        return operations

    @staticmethod
    def _apply_xor_modifications(
        image: np.ndarray, operations: list[PixelOperation]
    ) -> np.ndarray:
        result = image.copy()

        for operation in operations:
            pos_tuple = operation.to_tuple()
            if len(pos_tuple) == 3:  # RGB
                result[pos_tuple[0], pos_tuple[1], pos_tuple[2]] ^= operation.parameter
            else:  # Grayscale
                result[pos_tuple[0], pos_tuple[1]] ^= operation.parameter

        return result
