import random
from dataclasses import asdict
from typing import Dict, List, Optional

from image_modification_algorithms import ModificationEngine
from loguru import logger
from PIL import Image

from ..core.config import Settings
from ..models import Image as ImageModel
from ..models import Modification
from ..models.modification import AlgorithmType
from .file_storage import FileStorageService


class VariantGenerationService:
    def __init__(
        self,
        file_storage: Optional[FileStorageService] = None,
        modification_engine: Optional[ModificationEngine] = None,
        settings: Settings = None,
    ):
        from ..core.config import get_settings

        self.settings = settings or get_settings()
        self.file_storage = file_storage or FileStorageService()
        self.modification_engine = modification_engine or ModificationEngine()

    async def generate_variants(
        self, original_image: Image.Image, image_record: ImageModel
    ) -> List[Dict]:
        if original_image is None:
            raise ValueError("Original image cannot be None")

        if image_record is None:
            raise ValueError("Image record cannot be None")

        logger.info(f"Starting variant generation for image {image_record.id}")

        variants = []
        total_pixels = original_image.width * original_image.height

        if total_pixels < 100:
            min_modifications = max(1, total_pixels // 2)
            max_modifications = total_pixels
        else:
            min_modifications = 100
            max_modifications = max(total_pixels, min_modifications)

        try:
            for variant_number in range(1, 101):
                variant_info = await self._generate_single_variant(
                    original_image=original_image,
                    image_record=image_record,
                    variant_number=variant_number,
                    min_modifications=min_modifications,
                    max_modifications=max_modifications,
                )
                variants.append(variant_info)

            logger.info(
                f"Generated {len(variants)} variants for image {image_record.id}"
            )
            return variants

        except Exception as e:
            logger.error(
                f"Failed to generate variants for image {image_record.id}: {e}"
            )
            raise IOError(f"Failed to generate variants: {str(e)}")

    async def _generate_single_variant(
        self,
        original_image: Image.Image,
        image_record: ImageModel,
        variant_number: int,
        min_modifications: int,
        max_modifications: int,
    ) -> Dict:
        num_modifications = random.randint(min_modifications, max_modifications)

        result = self.modification_engine.apply_modifications(
            original_image, "xor_transform", num_modifications
        )

        extension = self.file_storage.extension_from_format(image_record.format)

        storage_path = await self.file_storage.save_variant_image(
            image=result.modified_image,
            image_id=str(image_record.id),
            variant_number=variant_number,
            extension=extension,
        )

        modification_record = await Modification.create(
            image_id=image_record.id,
            algorithm_type=AlgorithmType.XOR_TRANSFORM,
            variant_number=variant_number,
            instructions=asdict(result.instructions),
            storage_path=storage_path,
        )

        return {
            "variant_number": variant_number,
            "storage_path": storage_path,
            "modification_id": str(modification_record.id),
            "num_modifications": num_modifications,
            "algorithm_type": AlgorithmType.XOR_TRANSFORM.value,
        }

    async def get_variant_count(self, image_id: str) -> int:
        count = await Modification.filter(image_id=image_id).count()
        return count

    async def get_modification_by_id(
        self, modification_id: str
    ) -> Optional[Modification]:
        try:
            modification = await Modification.get(id=modification_id)
            return modification
        except Exception:
            return None

    async def get_all_variants_for_image(self, image_id: str) -> List[Modification]:
        modifications = await Modification.filter(image_id=image_id).order_by(
            "variant_number"
        )
        return modifications

    async def get_variant_by_number(
        self, image_id: str, variant_number: int
    ) -> Optional[Modification]:
        modification = await Modification.filter(
            image_id=image_id, variant_number=variant_number
        ).first()
        return modification
