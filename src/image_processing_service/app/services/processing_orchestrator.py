import uuid
from typing import Dict, List, Optional, Tuple

from loguru import logger

from ..core.config import Settings
from ..models import Image as ImageModel
from ..models import Modification
from .domain import ImageWithVariants, ProcessingResult
from .file_storage import FileStorageService
from .variant_generation import VariantGenerationService


class ProcessingOrchestrator:
    def __init__(
        self,
        file_storage: Optional[FileStorageService] = None,
        variant_generator: Optional[VariantGenerationService] = None,
        settings: Settings = None,
    ):
        from ..core.config import get_settings

        self.settings = settings or get_settings()
        self.file_storage = file_storage or FileStorageService()
        self.variant_generator = variant_generator or VariantGenerationService()

    async def start_image_processing(
        self, file_data: bytes, original_filename: str
    ) -> Tuple[str, Dict]:
        image_id = str(uuid.uuid4())

        try:
            logger.info(
                f"Starting image processing for {original_filename} (ID: {image_id})"
            )

            storage_path, metadata = await self.file_storage.save_original_image(
                file_data, original_filename, image_id
            )

            image_record = await ImageModel.create(
                id=image_id,
                original_filename=original_filename,
                file_size=metadata["file_size"],
                width=metadata["width"],
                height=metadata["height"],
                format=metadata["format"],
                storage_path=storage_path,
            )

            # Background task will be added by the API endpoint
            return image_id, {
                "processing_id": image_record.id,
                "message": "Image upload successful, processing started",
                "original_filename": image_record.original_filename,
                "file_size": image_record.file_size,
            }

        except Exception:
            await self._cleanup_image_and_records(image_id)
            raise

    async def process_variants_background(self, image_id: str):
        try:
            image_record = await ImageModel.get(id=image_id)
            await self._generate_variants_background(image_record)
        except Exception as e:
            logger.error(f"Background task failed for image {image_id}: {e}")

    async def _generate_variants_background(self, image_record: ImageModel):
        image_id = str(image_record.id)

        try:
            logger.info(f"Starting variant generation for image {image_id}")

            original_image = await self.file_storage.load_image(
                image_record.storage_path
            )

            await self.variant_generator.generate_variants(original_image, image_record)

            logger.info(f"Successfully generated variants for image {image_id}")

        except Exception as e:
            logger.error(f"Failed to process variants for image {image_id}: {e}")

            await self._cleanup_image_and_records(image_id, image_record)

    async def _cleanup_image_and_records(
        self, image_id: str, image_record: Optional[ImageModel] = None
    ):
        try:
            await self.file_storage.delete_image_and_variants(image_id)

            await Modification.filter(image_id=image_id).delete()

            if image_record:
                await image_record.delete()

        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup for image {image_id}: {cleanup_error}")

    async def get_processing_status(
        self, processing_id: str
    ) -> Optional[ProcessingResult]:
        try:
            image_record = await ImageModel.get(id=processing_id)

            variants_count = await Modification.filter(image_id=processing_id).count()

            if variants_count == 0:
                status = "processing"
                progress = 0
            elif variants_count < 100:
                status = "processing"
                progress = variants_count
            else:
                status = "completed"
                progress = 100

            return ProcessingResult(
                processing_id=processing_id,
                status=status,
                progress=progress,
                variants_completed=variants_count,
                total_variants=100,
                created_at=image_record.created_at,
                completed_at=image_record.updated_at if status == "completed" else None,
                error_message=None,
            )

        except Exception:
            return None

    async def get_modification_details(
        self, image_id: str
    ) -> Optional[ImageWithVariants]:
        try:
            image_record = await ImageModel.get(id=image_id)
            variants_count = await Modification.filter(image_id=image_id).count()

            return ImageWithVariants(image=image_record, variants_count=variants_count)

        except Exception:
            return None

    async def get_image_variants(self, image_id: str) -> Optional[List[Modification]]:
        try:
            await ImageModel.get(id=image_id)

            modifications = await Modification.filter(image_id=image_id).order_by(
                "variant_number"
            )

            return modifications

        except Exception:
            return None
