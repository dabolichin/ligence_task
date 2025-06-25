from pathlib import Path

import pytest
from PIL import Image

from src.verification_service.app.services.image_comparison import (
    ComparisonMethod,
    ComparisonResult,
)

# All fixtures are now defined in conftest.py to avoid duplication


class TestCompareImagesWithMethods:
    def test_compare_identical_images_default_both(
        self, comparison_service, temp_image_paths
    ):
        result = comparison_service.compare_images(
            temp_image_paths["original"], temp_image_paths["identical"]
        )

        assert isinstance(result, ComparisonResult)
        assert result.hash_match is True
        assert result.pixel_match is True
        assert result.original_hash is not None
        assert result.reversed_hash is not None
        assert result.original_hash == result.reversed_hash
        assert result.method_used == "both"

    def test_compare_identical_images_hash_only(
        self, comparison_service, temp_image_paths
    ):
        result = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["identical"],
            ComparisonMethod.HASH_ONLY,
        )

        assert result.hash_match is True
        assert result.pixel_match is None  # Not performed
        assert result.original_hash is not None
        assert result.reversed_hash is not None
        assert result.original_hash == result.reversed_hash
        assert result.method_used == "hash_only"

    def test_compare_identical_images_pixel_only(
        self, comparison_service, temp_image_paths
    ):
        result = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["identical"],
            ComparisonMethod.PIXEL_ONLY,
        )

        assert result.hash_match is None  # Not performed
        assert result.pixel_match is True
        assert result.original_hash is None
        assert result.reversed_hash is None
        assert result.method_used == "pixel_only"

    def test_compare_different_images_hash_only(
        self, comparison_service, temp_image_paths
    ):
        result = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["different"],
            ComparisonMethod.HASH_ONLY,
        )

        assert result.hash_match is False
        assert result.pixel_match is None  # Not performed
        assert result.original_hash is not None
        assert result.reversed_hash is not None
        assert result.original_hash != result.reversed_hash
        assert result.method_used == "hash_only"

    def test_compare_different_images_pixel_only(
        self, comparison_service, temp_image_paths
    ):
        result = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["different"],
            ComparisonMethod.PIXEL_ONLY,
        )

        assert result.hash_match is None  # Not performed
        assert result.pixel_match is False
        assert result.original_hash is None
        assert result.reversed_hash is None
        assert result.method_used == "pixel_only"

    def test_compare_different_images_both(self, comparison_service, temp_image_paths):
        result = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["different"],
            ComparisonMethod.BOTH,
        )

        assert result.hash_match is False
        assert result.pixel_match is False
        assert result.original_hash is not None
        assert result.reversed_hash is not None
        assert result.original_hash != result.reversed_hash
        assert result.method_used == "both"

    def test_compare_partially_different_images_both(
        self, comparison_service, sample_image_rgb, tmp_path
    ):
        modified_image = sample_image_rgb.copy()
        modified_image.putpixel((0, 0), (0, 255, 0))  # Change one pixel to green

        original_path = tmp_path / "original.png"
        modified_path = tmp_path / "modified.png"
        sample_image_rgb.save(original_path)
        modified_image.save(modified_path)

        result = comparison_service.compare_images(
            original_path, modified_path, ComparisonMethod.BOTH
        )

        assert result.hash_match is False
        assert result.pixel_match is False
        assert result.method_used == "both"

    def test_compare_grayscale_images(
        self, comparison_service, sample_image_grayscale, tmp_path
    ):
        identical_grayscale = sample_image_grayscale.copy()

        original_path = tmp_path / "original_gray.png"
        identical_path = tmp_path / "identical_gray.png"
        sample_image_grayscale.save(original_path)
        identical_grayscale.save(identical_path)

        result = comparison_service.compare_images(
            original_path, identical_path, ComparisonMethod.BOTH
        )

        assert result.hash_match is True
        assert result.pixel_match is True
        assert result.method_used == "both"


class TestErrorHandling:
    def test_compare_pixels_different_dimensions(
        self, comparison_service, sample_image_rgb, different_size_image, tmp_path
    ):
        path1 = tmp_path / "image1.png"
        path2 = tmp_path / "image2.png"
        sample_image_rgb.save(path1)
        different_size_image.save(path2)

        with pytest.raises(ValueError, match="Image dimensions don't match"):
            comparison_service._compare_pixels(path1, path2)

    def test_compare_pixels_different_modes(
        self, comparison_service, sample_image_rgb, different_mode_image, tmp_path
    ):
        rgb_path = tmp_path / "rgb.png"
        gray_path = tmp_path / "gray.png"
        sample_image_rgb.save(rgb_path)
        different_mode_image.save(gray_path)

        with pytest.raises(ValueError, match="Image modes don't match"):
            comparison_service._compare_pixels(rgb_path, gray_path)

    def test_compare_from_paths_nonexistent_file(
        self, comparison_service, temp_image_paths
    ):
        nonexistent_path = Path("/nonexistent/path.png")

        with pytest.raises(FileNotFoundError):
            comparison_service.compare_images(
                temp_image_paths["original"], nonexistent_path
            )

    def test_get_file_hash_nonexistent_file(self, comparison_service):
        nonexistent_path = Path("/nonexistent/path.png")

        with pytest.raises(FileNotFoundError):
            comparison_service._get_file_hash(nonexistent_path)


class TestEdgeCases:
    def test_compare_single_pixel_images(self, comparison_service, tmp_path):
        image1 = Image.new("RGB", (1, 1), color=(255, 0, 0))
        image2 = Image.new("RGB", (1, 1), color=(255, 0, 0))

        path1 = tmp_path / "single1.png"
        path2 = tmp_path / "single2.png"
        image1.save(path1)
        image2.save(path2)

        result = comparison_service.compare_images(path1, path2, ComparisonMethod.BOTH)

        assert result.hash_match is True
        assert result.pixel_match is True
        assert result.method_used == "both"

    def test_compare_single_pixel_different_images(self, comparison_service, tmp_path):
        image1 = Image.new("RGB", (1, 1), color=(255, 0, 0))
        image2 = Image.new("RGB", (1, 1), color=(0, 255, 0))

        path1 = tmp_path / "single1.png"
        path2 = tmp_path / "single2.png"
        image1.save(path1)
        image2.save(path2)

        result = comparison_service.compare_images(path1, path2, ComparisonMethod.BOTH)

        assert result.hash_match is False
        assert result.pixel_match is False
        assert result.method_used == "both"


class TestIntegration:
    def test_full_comparison_workflow_identical(
        self, comparison_service, temp_image_paths
    ):
        result = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["identical"],
            ComparisonMethod.BOTH,
        )

        assert result.hash_match is True
        assert result.pixel_match is True
        assert result.original_hash is not None
        assert result.reversed_hash is not None
        assert result.original_hash == result.reversed_hash
        assert result.method_used == "both"

    def test_full_comparison_workflow_different(
        self, comparison_service, temp_image_paths
    ):
        result = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["different"],
            ComparisonMethod.BOTH,
        )

        assert result.hash_match is False
        assert result.pixel_match is False
        assert result.original_hash is not None
        assert result.reversed_hash is not None
        assert result.original_hash != result.reversed_hash
        assert result.method_used == "both"

    def test_all_comparison_methods_consistency(
        self, comparison_service, temp_image_paths
    ):
        result_hash = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["identical"],
            ComparisonMethod.HASH_ONLY,
        )

        result_pixel = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["identical"],
            ComparisonMethod.PIXEL_ONLY,
        )

        result_both = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["identical"],
            ComparisonMethod.BOTH,
        )

        assert result_hash.hash_match is True
        assert result_both.hash_match is True
        assert result_hash.original_hash == result_both.original_hash

        assert result_pixel.pixel_match is True
        assert result_both.pixel_match is True

        assert result_hash.method_used == "hash_only"
        assert result_pixel.method_used == "pixel_only"
        assert result_both.method_used == "both"

    def test_both_method_performs_both_comparisons(
        self, comparison_service, temp_image_paths
    ):
        result_identical = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["identical"],
            ComparisonMethod.BOTH,
        )

        assert result_identical.hash_match is not None
        assert result_identical.pixel_match is not None
        assert result_identical.hash_match is True
        assert result_identical.pixel_match is True

        result_different = comparison_service.compare_images(
            temp_image_paths["original"],
            temp_image_paths["different"],
            ComparisonMethod.BOTH,
        )

        assert result_different.hash_match is not None
        assert result_different.pixel_match is not None
        assert result_different.hash_match is False
        assert result_different.pixel_match is False
