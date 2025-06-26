import hashlib
from pathlib import Path

import numpy as np
from loguru import logger
from PIL import Image

from .domain import ComparisonMethod, ComparisonResult


class ImageComparisonService:
    def __init__(self):
        pass

    def compare_images(
        self,
        original_path: str | Path,
        reversed_path: str | Path,
        method: ComparisonMethod = ComparisonMethod.BOTH,
    ) -> "ComparisonResult":
        logger.info(f"Starting image comparison using method: {method.value}")

        try:
            if method == ComparisonMethod.HASH_ONLY:
                hash_match, original_hash, reversed_hash = self._compare_hashes(
                    original_path, reversed_path
                )
                result = ComparisonResult(
                    hash_match=hash_match,
                    pixel_match=None,  # Not performed
                    original_hash=original_hash,
                    reversed_hash=reversed_hash,
                    method_used=ComparisonMethod.HASH_ONLY.value,
                )
                logger.info(f"Hash-only comparison complete: hash_match={hash_match}")
                return result

            elif method == ComparisonMethod.PIXEL_ONLY:
                pixels_match = self._compare_pixels(original_path, reversed_path)
                result = ComparisonResult(
                    hash_match=None,  # Not performed
                    pixel_match=pixels_match,
                    original_hash=None,  # Not calculated
                    reversed_hash=None,  # Not calculated
                    method_used=ComparisonMethod.PIXEL_ONLY.value,
                )
                logger.info(
                    f"Pixel-only comparison complete: pixel_match={pixels_match}"
                )
                return result

            else:
                hash_match, original_hash, reversed_hash = self._compare_hashes(
                    original_path, reversed_path
                )
                pixels_match = self._compare_pixels(original_path, reversed_path)

                result = ComparisonResult(
                    hash_match=hash_match,
                    pixel_match=pixels_match,
                    original_hash=original_hash,
                    reversed_hash=reversed_hash,
                    method_used=ComparisonMethod.BOTH.value,
                )
                logger.info(
                    f"Both methods comparison complete: hash_match={hash_match}, pixel_match={pixels_match}"
                )
                return result

        except Exception as e:
            logger.error(f"Error during image comparison: {e}", exc_info=True)
            raise

    def _compare_hashes(
        self, original_path: str | Path, reversed_path: str | Path
    ) -> tuple[bool, str, str]:
        try:
            original_hash = self._get_pixel_hash(original_path)
            reversed_hash = self._get_pixel_hash(reversed_path)

            hash_match = original_hash == reversed_hash

            logger.debug(
                f"Pixel hash comparison: match={hash_match}, "
                f"original={original_hash[:16]}..., reversed={reversed_hash[:16]}..."
            )

            return hash_match, original_hash, reversed_hash

        except Exception as e:
            logger.error(f"Error in pixel hash comparison: {e}")
            raise

    def _compare_pixels(
        self, original_path: str | Path, reversed_path: str | Path
    ) -> bool:
        try:
            with Image.open(original_path) as img1, Image.open(reversed_path) as img2:
                if img1.size != img2.size:
                    raise ValueError(
                        f"Image dimensions don't match: "
                        f"original={img1.size}, reversed={img2.size}"
                    )

                if img1.mode != img2.mode:
                    raise ValueError(
                        f"Image modes don't match: "
                        f"original={img1.mode}, reversed={img2.mode}"
                    )

                arr1 = np.array(img1)
                arr2 = np.array(img2)

                if arr1.shape != arr2.shape:
                    raise ValueError(
                        f"Array shapes don't match: "
                        f"original={arr1.shape}, reversed={arr2.shape}"
                    )

                pixels_match = np.array_equal(arr1, arr2)

                logger.debug(f"Pixel comparison: pixels_match={pixels_match}")

                return pixels_match

        except Exception as e:
            logger.error(f"Error in pixel comparison: {e}")
            raise

    def _get_file_hash(self, file_path: str | Path) -> str:
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            raise

    def _get_pixel_hash(self, file_path: str | Path) -> str:
        try:
            with Image.open(file_path) as img:
                # Convert to numpy array to get raw pixel data
                pixel_array = np.array(img)

                # Convert to bytes and hash
                pixel_bytes = pixel_array.tobytes()
                pixel_hash = hashlib.sha256(pixel_bytes).hexdigest()

                logger.debug(
                    f"Calculated pixel hash for {file_path}: {pixel_hash[:16]}..."
                )
                return pixel_hash

        except Exception as e:
            logger.error(f"Error calculating pixel hash for {file_path}: {e}")
            raise
