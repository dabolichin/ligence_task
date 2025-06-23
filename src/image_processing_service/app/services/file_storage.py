import asyncio
import shutil
import uuid
from pathlib import Path
from typing import Tuple

import aiofiles
from loguru import logger
from PIL import Image

from ..core.config import get_settings


class FileStorageService:
    def __init__(self):
        self.settings = get_settings()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        directories = [
            Path(self.settings.absolute_original_images_dir),
            Path(self.settings.absolute_modified_images_dir),
            Path(self.settings.absolute_temp_dir),
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    async def _extract_metadata(self, file_path: str) -> Tuple[str, dict]:
        try:

            def _extract_format_and_metadata():
                with Image.open(file_path) as img:
                    image_format = img.format.lower() if img.format else None

                    self._validate_format(image_format)

                    # Extract metadata
                    metadata = {
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode,
                        "file_size": Path(file_path).stat().st_size,
                    }

                    return metadata

            return await asyncio.to_thread(_extract_format_and_metadata)

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid image file: {str(e)}")

    def _validate_format(self, image_format: str) -> None:
        if not image_format:
            raise ValueError("Unable to determine image format")

        if image_format not in self.settings.ALLOWED_IMAGE_FORMATS:
            raise ValueError(f"Unsupported image format: {image_format}")

    def _format_variant_name(
        self, base_name: str, variant_number: int, extension: str
    ) -> str:
        """Generate a variant name with consistent formatting."""
        return f"{base_name}_variant_{variant_number:03d}{extension}"

    def generate_variant_path(
        self, image_id: str, variant_number: int, extension: str
    ) -> str:
        variant_filename = self._format_variant_name(
            image_id, variant_number, extension
        )

        return str(Path(self.settings.absolute_modified_images_dir) / variant_filename)

    def extension_from_format(self, image_format: str) -> str:
        if image_format == "JPEG":
            return ".jpg"
        else:
            return f".{image_format.lower()}"

    async def save_original_image(
        self, file_data: bytes, filename: str, image_id: str
    ) -> Tuple[str, dict]:
        temp_path = f"{self.settings.absolute_temp_dir}/{uuid.uuid4().hex}_temp"

        logger.info(f"Saving original image: {filename} (ID: {image_id})")

        try:
            async with aiofiles.open(temp_path, "wb") as f:
                await f.write(file_data)

            metadata = await self._extract_metadata(temp_path)
            extension = self.extension_from_format(metadata["format"])

            new_filename = f"{image_id}_original{extension}"
            storage_path = str(
                Path(self.settings.absolute_original_images_dir) / new_filename
            )

            await asyncio.to_thread(shutil.move, temp_path, storage_path)

            return storage_path, metadata

        except Exception as e:
            await self._safe_delete_file(temp_path)
            if "storage_path" in locals():
                await self._safe_delete_file(storage_path)

            if isinstance(e, ValueError):
                raise
            raise IOError(f"Failed to save original image: {str(e)}")

    async def save_variant_image(
        self,
        image: Image.Image,
        image_id: str,
        variant_number: int,
        extension: str,
    ) -> str:
        storage_path = self.generate_variant_path(image_id, variant_number, extension)

        try:
            await asyncio.to_thread(image.save, storage_path)

            return storage_path

        except Exception as e:
            await self._safe_delete_file(storage_path)
            raise IOError(f"Failed to save variant image: {str(e)}")

    async def load_image(self, file_path: str) -> Image.Image:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        try:
            image = await asyncio.to_thread(Image.open, file_path)
            return image

        except Exception as e:
            raise IOError(f"Failed to load image: {str(e)}")

    async def delete_image(self, file_path: str) -> bool:
        return await self._safe_delete_file(file_path)

    async def delete_image_and_variants(self, image_id: str) -> int:
        deleted_count = 0

        original_pattern = f"{image_id}_original*"
        original_dir = Path(self.settings.absolute_original_images_dir)

        for file_path in original_dir.glob(original_pattern):
            if await self._safe_delete_file(str(file_path)):
                deleted_count += 1

        variant_pattern = f"{image_id}_variant_*"
        variant_dir = Path(self.settings.absolute_modified_images_dir)

        for file_path in variant_dir.glob(variant_pattern):
            if await self._safe_delete_file(str(file_path)):
                deleted_count += 1

        return deleted_count

    async def _safe_delete_file(self, file_path: str) -> bool:
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except (OSError, IOError, PermissionError):
            return False
        except Exception:
            return False

    async def file_exists(self, file_path: str) -> bool:
        try:
            path = Path(file_path)
            return path.exists()

        except Exception:
            return False

    def generate_variant_filename(
        self, original_filename: str, variant_number: int
    ) -> str:
        base_name = original_filename.rsplit(".", 1)[0]
        extension = (
            original_filename.rsplit(".", 1)[1] if "." in original_filename else "img"
        )
        return self._format_variant_name(base_name, variant_number, f".{extension}")
