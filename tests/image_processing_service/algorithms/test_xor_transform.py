import time
from contextlib import contextmanager

import numpy as np
import pytest
from PIL import Image

from src.image_processing_service.app.services.algorithms.xor_transform import (
    Modification,
    ModificationResult,
    PixelOperation,
    XORTransformAlgorithm,
)


@contextmanager
def timeout_check(seconds):
    start_time = time.time()
    yield
    elapsed = time.time() - start_time
    if elapsed >= seconds:
        raise AssertionError(f"Operation took {elapsed:.2f}s, timeout was {seconds}s")


class TestXORTransformAlgorithm:
    def setup_method(self):  #
        row, col, channels = 10, 10, 3
        self.rgb_image = Image.fromarray(
            np.random.randint(0, 256, (row, col, channels), dtype=np.uint8), mode="RGB"
        )
        self.grayscale_image = Image.fromarray(
            np.random.randint(0, 256, (row, col), dtype=np.uint8), mode="L"
        )

        self.small_rgb = Image.fromarray(
            np.array(
                [[[100, 150, 200], [50, 75, 125]], [[25, 35, 45], [200, 175, 150]]],
                dtype=np.uint8,
            ),
            mode="RGB",
        )
        self.small_gray = Image.fromarray(
            np.array([[100, 150], [50, 200]], dtype=np.uint8), mode="L"
        )

    @pytest.mark.parametrize(
        "image_attr,mode,num_modifications,has_channel",
        [
            ("rgb_image", "RGB", 5, True),
            ("grayscale_image", "L", 3, False),
        ],
    )
    def test_apply_modifications(
        self, image_attr, mode, num_modifications, has_channel
    ):
        algorithm = XORTransformAlgorithm(seed=42)
        image = getattr(self, image_attr)

        result = algorithm.apply_modifications(image, num_modifications)
        modified_image, instructions = result.modified_image, result.instructions

        assert isinstance(modified_image, Image.Image)
        assert isinstance(instructions, Modification)
        assert isinstance(result, ModificationResult)

        assert modified_image.mode == image.mode
        assert modified_image.size == image.size

        assert instructions.algorithm_type == "xor_transform"
        assert instructions.image_mode == mode
        assert len(instructions.operations) == num_modifications

        for pixel in instructions.operations:
            assert isinstance(pixel, PixelOperation)
            assert 0 <= pixel.row < 10
            assert 0 <= pixel.col < 10
            assert 1 <= pixel.parameter <= 255

            if has_channel:
                assert pixel.channel is not None
                assert 0 <= pixel.channel < 3
            else:
                assert pixel.channel is None

    def test_apply_modifications_input_validation(self):
        algorithm = XORTransformAlgorithm()

        result = algorithm.apply_modifications(self.rgb_image, 0)
        assert len(result.instructions.operations) == 0

        result = algorithm.apply_modifications(self.rgb_image, -5)
        assert len(result.instructions.operations) == 0

    def test_modifications_actually_change_image(self):
        algorithm = XORTransformAlgorithm(seed=42)

        original_array = np.array(self.small_rgb)
        result = algorithm.apply_modifications(self.small_rgb, 2)
        modified_array = np.array(result.modified_image)

        assert not np.array_equal(original_array, modified_array)

    def test_xor_values_in_valid_range(self):
        algorithm = XORTransformAlgorithm(seed=42)

        result = algorithm.apply_modifications(self.rgb_image, 10)
        operations = result.instructions.operations

        for operation in operations:
            assert 1 <= operation.parameter <= 255

    @pytest.mark.parametrize(
        "image_attr,num_modifications",
        [
            ("small_rgb", 3),
            ("small_gray", 2),
        ],
    )
    def test_reverse_modifications(self, image_attr, num_modifications):
        algorithm = XORTransformAlgorithm(seed=42)
        original_image = getattr(self, image_attr)

        result = algorithm.apply_modifications(original_image, num_modifications)

        restored_image = algorithm.reverse_modifications(
            result.modified_image, result.instructions
        )

        assert restored_image.mode == original_image.mode
        assert restored_image.size == original_image.size

        original_array = np.array(original_image)
        restored_array = np.array(restored_image)
        assert np.array_equal(original_array, restored_array)

    def test_reverse_modifications_input_validation(self):
        invalid_instructions = Modification(
            algorithm_type="test",
            image_mode="RGB",
            operations=None,
        )
        with pytest.raises(
            ValueError, match="Modification data must contain operations"
        ):
            XORTransformAlgorithm.reverse_modifications(
                self.rgb_image, invalid_instructions
            )

    def test_max_modifications_limit(self):
        algorithm = XORTransformAlgorithm(seed=42)
        row, col, channels = 2, 2, 3

        small_image = Image.fromarray(
            np.random.randint(0, 256, (row, col, channels), dtype=np.uint8), mode="RGB"
        )
        total_pixels = row * col * channels

        result = algorithm.apply_modifications(
            small_image,
            total_pixels + 100,  # Request more than available
        )

        assert len(result.instructions.operations) <= total_pixels

    def test_deterministic_behavior_with_seed(self):
        seed = 123

        algorithm1 = XORTransformAlgorithm(seed=seed)
        algorithm2 = XORTransformAlgorithm(seed=seed)

        result1 = algorithm1.apply_modifications(self.small_rgb, 5)
        result2 = algorithm2.apply_modifications(self.small_rgb, 5)

        assert np.array_equal(
            np.array(result1.modified_image), np.array(result2.modified_image)
        )
        assert result1.instructions.operations == result2.instructions.operations

    def test_large_image_performance(self):
        algorithm = XORTransformAlgorithm(seed=42)

        large_image = Image.fromarray(
            np.random.randint(0, 256, (1000, 1000, 3), dtype=np.uint8), mode="RGB"
        )

        with timeout_check(5):
            start_time = time.time()
            result = algorithm.apply_modifications(large_image, 1000000)
            modification_time = time.time() - start_time

        with timeout_check(5):
            start_time = time.time()
            restored = algorithm.reverse_modifications(
                result.modified_image, result.instructions
            )
            reversal_time = time.time() - start_time

        original_array = np.array(large_image)
        restored_array = np.array(restored)
        assert np.array_equal(original_array, restored_array)

        print(
            f"\nPerformance: Modification {modification_time:.3f}s, Reversal {reversal_time:.3f}s"
        )
