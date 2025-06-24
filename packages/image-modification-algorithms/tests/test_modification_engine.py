import numpy as np
import pytest
from image_modification_algorithms import (
    Modification,
    ModificationEngine,
    ModificationResult,
    PixelOperation,
)
from PIL import Image


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
