import random
from dataclasses import asdict
from typing import Dict, List

from PIL import Image

from ..core.config import get_settings
from ..models import Image as ImageModel
from ..models import Modification
from ..models.modification import AlgorithmType
from .algorithms.xor_transform import XORTransformAlgorithm
from .file_storage import FileStorageService


class VariantGenerationService:
    def __init__(self):
        self.settings = get_settings()
        self.file_storage = FileStorageService()
        self.xor_algorithm = XORTransformAlgorithm()

    async def generate_variants(
        self, original_image: Image.Image, image_record: ImageModel
    ) -> List[Dict]:
        if original_image is None:
            raise ValueError("Original image cannot be None")

        if image_record is None:
            raise ValueError("Image record cannot be None")

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

            return variants

        except Exception as e:
            await self._cleanup_variants(image_record.id, len(variants))
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

        modification_result = self.xor_algorithm.apply_modifications(
            original_image, num_modifications
        )

        extension = self.file_storage.extension_from_format(image_record.format)

        storage_path = await self.file_storage.save_variant_image(
            image=modification_result.modified_image,
            image_id=str(image_record.id),
            variant_number=variant_number,
            extension=extension,
        )

        modification_record = await Modification.create(
            image_id=image_record.id,
            algorithm_type=AlgorithmType.XOR_TRANSFORM,
            variant_number=variant_number,
            instructions=asdict(modification_result.instructions),
            storage_path=storage_path,
        )

        return {
            "variant_number": variant_number,
            "storage_path": storage_path,
            "modification_id": str(modification_record.id),
            "num_modifications": num_modifications,
            "algorithm_type": AlgorithmType.XOR_TRANSFORM.value,
        }

    async def _cleanup_variants(self, image_id: str, num_variants_created: int) -> None:
        try:
            # Delete any files that were created
            await self.file_storage.delete_image_and_variants(image_id)

            # Delete any database records that were created
            await Modification.filter(image_id=image_id).delete()

        except Exception as cleanup_error:
            # Log cleanup error but don't raise to avoid masking original error
            print(
                f"Warning: Failed to cleanup variants for image {image_id}: {cleanup_error}"
            )

    async def get_variant_count(self, image_id: str) -> int:
        count = await Modification.filter(image_id=image_id).count()
        return count
