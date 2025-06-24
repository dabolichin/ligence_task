import numpy as np
import pytest
from image_modification_algorithms import (
    Modification,
    ModificationResult,
    PixelOperation,
    XORTransformAlgorithm,
)
from PIL import Image


class TestXORTransformAlgorithm:
    def test_apply_modifications_rgb(self):
        algorithm = XORTransformAlgorithm(seed=42)
        rgb_image = Image.fromarray(
            np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8), mode="RGB"
        )

        result = algorithm.apply_modifications(rgb_image, 5)
        modified_image, instructions = result.modified_image, result.instructions

        assert isinstance(modified_image, Image.Image)
        assert isinstance(instructions, Modification)
        assert isinstance(result, ModificationResult)

        assert modified_image.mode == rgb_image.mode
        assert modified_image.size == rgb_image.size

        assert instructions.algorithm_type == "xor_transform"
        assert instructions.image_mode == "RGB"
        assert len(instructions.operations) == 5

        for pixel in instructions.operations:
            assert isinstance(pixel, PixelOperation)
            assert 0 <= pixel.row < 10
            assert 0 <= pixel.col < 10
            assert 1 <= pixel.parameter <= 255
            assert pixel.channel is not None
            assert 0 <= pixel.channel < 3

    def test_apply_modifications_grayscale(self):
        algorithm = XORTransformAlgorithm(seed=42)
        grayscale_image = Image.fromarray(
            np.random.randint(0, 256, (10, 10), dtype=np.uint8), mode="L"
        )

        result = algorithm.apply_modifications(grayscale_image, 3)
        modified_image, instructions = result.modified_image, result.instructions

        assert isinstance(modified_image, Image.Image)
        assert isinstance(instructions, Modification)
        assert isinstance(result, ModificationResult)

        assert modified_image.mode == grayscale_image.mode
        assert modified_image.size == grayscale_image.size

        assert instructions.algorithm_type == "xor_transform"
        assert instructions.image_mode == "L"
        assert len(instructions.operations) == 3

        for pixel in instructions.operations:
            assert isinstance(pixel, PixelOperation)
            assert 0 <= pixel.row < 10
            assert 0 <= pixel.col < 10
            assert 1 <= pixel.parameter <= 255
            assert pixel.channel is None

    def test_apply_modifications_input_validation(self):
        algorithm = XORTransformAlgorithm()
        rgb_image = Image.fromarray(
            np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8), mode="RGB"
        )

        result = algorithm.apply_modifications(rgb_image, 0)
        assert len(result.instructions.operations) == 0

        result = algorithm.apply_modifications(rgb_image, -5)
        assert len(result.instructions.operations) == 0

    def test_modifications_actually_change_image(self):
        algorithm = XORTransformAlgorithm(seed=42)
        small_rgb = Image.fromarray(
            np.array(
                [[[100, 150, 200], [50, 75, 125]], [[25, 35, 45], [200, 175, 150]]],
                dtype=np.uint8,
            ),
            mode="RGB",
        )

        original_array = np.array(small_rgb)
        result = algorithm.apply_modifications(small_rgb, 2)
        modified_array = np.array(result.modified_image)

        assert not np.array_equal(original_array, modified_array)

    def test_reverse_modifications(self):
        algorithm = XORTransformAlgorithm(seed=42)
        small_rgb = Image.fromarray(
            np.array(
                [[[100, 150, 200], [50, 75, 125]], [[25, 35, 45], [200, 175, 150]]],
                dtype=np.uint8,
            ),
            mode="RGB",
        )

        result = algorithm.apply_modifications(small_rgb, 3)

        restored_image = algorithm.reverse_modifications(
            result.modified_image, result.instructions
        )

        assert restored_image.mode == small_rgb.mode
        assert restored_image.size == small_rgb.size

        original_array = np.array(small_rgb)
        restored_array = np.array(restored_image)
        assert np.array_equal(original_array, restored_array)

    def test_reverse_modifications_input_validation(self):
        rgb_image = Image.fromarray(
            np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8), mode="RGB"
        )
        invalid_instructions = Modification(
            algorithm_type="test",
            image_mode="RGB",
            operations=None,
        )
        with pytest.raises(
            ValueError, match="Modification data must contain operations"
        ):
            XORTransformAlgorithm.reverse_modifications(rgb_image, invalid_instructions)

    def test_max_modifications_limit(self):
        algorithm = XORTransformAlgorithm(seed=42)
        small_image = Image.fromarray(
            np.random.randint(0, 256, (2, 2, 3), dtype=np.uint8), mode="RGB"
        )
        total_pixels = 2 * 2 * 3

        result = algorithm.apply_modifications(
            small_image,
            total_pixels + 100,  # Request more than available
        )

        assert len(result.instructions.operations) <= total_pixels

    def test_deterministic_behavior_with_seed(self):
        seed = 123
        small_rgb = Image.fromarray(
            np.array(
                [[[100, 150, 200], [50, 75, 125]], [[25, 35, 45], [200, 175, 150]]],
                dtype=np.uint8,
            ),
            mode="RGB",
        )

        algorithm1 = XORTransformAlgorithm(seed=seed)
        algorithm2 = XORTransformAlgorithm(seed=seed)

        result1 = algorithm1.apply_modifications(small_rgb, 5)
        result2 = algorithm2.apply_modifications(small_rgb, 5)

        assert np.array_equal(
            np.array(result1.modified_image), np.array(result2.modified_image)
        )
        assert result1.instructions.operations == result2.instructions.operations
