import os
import tempfile
from pathlib import Path

from loguru import logger
from PIL import Image

from ..core.config import get_settings
from .domain import ComparisonMethod, ComparisonResult
from .image_comparison import ImageComparisonService


class ImageReversalService:
    def __init__(self, image_comparison_service: ImageComparisonService):
        self.image_comparison_service = image_comparison_service
        self.settings = get_settings()

    async def reverse_image_modifications(
        self, instruction_data, modification_instructions, modification_engine
    ) -> Image.Image:
        try:
            logger.info(
                f"Applying reverse modifications for modification {instruction_data.modification_id}"
            )
            modified_image = Image.open(instruction_data.storage_path)
            reversed_image = modification_engine.reverse_modifications(
                modified_image, modification_instructions
            )
            logger.info(
                f"Successfully applied reverse modifications for modification {instruction_data.modification_id}"
            )
            return reversed_image

        except Exception as e:
            logger.error(
                f"Error applying reverse modifications for modification {instruction_data.modification_id}: {e}",
                exc_info=True,
            )
            raise

    async def verify_reversibility(
        self, reversed_image: Image.Image, instruction_data
    ) -> ComparisonResult:
        original_image_path = self._get_original_image_path(instruction_data)
        logger.info(f"Starting reversibility verification for {original_image_path}")

        temp_reversed_path = None
        try:
            temp_reversed_path = self._save_temporary_image(reversed_image)
            comparison_result = self.image_comparison_service.compare_images(
                original_path=original_image_path,
                reversed_path=temp_reversed_path,
                method=ComparisonMethod.BOTH,
            )

            logger.info(
                f"Reversibility verification complete: "
                f"hash_match={comparison_result.hash_match}, "
                f"pixel_match={comparison_result.pixel_match}"
            )
            return comparison_result

        except Exception as e:
            logger.error(f"Error during reversibility verification: {e}", exc_info=True)
            return ComparisonResult(
                hash_match=False,
                pixel_match=False,
                original_hash=None,
                reversed_hash=None,
                method_used=ComparisonMethod.BOTH.value,
            )
        finally:
            if temp_reversed_path:
                self._cleanup_temporary_file(temp_reversed_path)

    def _get_original_image_path(self, instruction_data) -> str:
        original_image_path = instruction_data.instructions.get("original_image_path")

        if original_image_path:
            return original_image_path

        original_filename = instruction_data.original_filename
        if "." in original_filename:
            extension = "." + original_filename.rsplit(".", 1)[1]
        else:
            extension = ".jpg"  # Default fallback

        # Construct path using the same pattern as image processing service
        # Pattern: {image_id}_original{extension}
        filename = f"{instruction_data.image_id}_original{extension}"
        fallback_path = str(Path(self.settings.absolute_original_images_dir) / filename)

        logger.warning(
            f"Original image path not found in instructions, using fallback: {fallback_path}"
        )

        return fallback_path

    def _save_temporary_image(self, image: Image.Image) -> str:
        try:
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".png", delete=False, prefix="reversed_image_"
            )
            temp_path = temp_file.name
            temp_file.close()

            image.save(temp_path)
            logger.debug(f"Saved temporary image to {temp_path}")

            return temp_path

        except Exception as e:
            logger.error(f"Error saving temporary image: {e}")
            raise

    def _cleanup_temporary_file(self, file_path: str) -> None:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except OSError as e:
            logger.warning(f"Failed to delete temporary file {file_path}: {e}")

    async def verify_modification_completely(
        self,
        instruction_data,
        modification_instructions,
        modification_engine,
    ) -> ComparisonResult:
        try:
            reversed_image = await self.reverse_image_modifications(
                instruction_data, modification_instructions, modification_engine
            )
            comparison_result = await self.verify_reversibility(
                reversed_image, instruction_data
            )
            return comparison_result

        except Exception as e:
            logger.error(
                f"Error in complete modification verification for {instruction_data.modification_id}: {e}",
                exc_info=True,
            )
            return ComparisonResult(
                hash_match=False,
                pixel_match=False,
                original_hash=None,
                reversed_hash=None,
                method_used=ComparisonMethod.BOTH.value,
            )
