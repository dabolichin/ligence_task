import gc
import random
from dataclasses import asdict

import httpx
from image_modification_algorithms import ModificationEngine
from loguru import logger
from PIL import Image

from ..core.config import Settings
from ..models import Image as ImageModel
from ..models import Modification
from ..models.modification import AlgorithmType
from ..schemas import VerificationRequest
from .file_storage import FileStorageService


class VariantGenerationService:
    def __init__(
        self,
        file_storage: FileStorageService | None = None,
        modification_engine: ModificationEngine | None = None,
        settings: Settings = None,
    ):
        from ..core.config import get_settings

        self.settings = settings or get_settings()

        if file_storage is None:
            raise ValueError(
                "FileStorageService must be provided via dependency injection"
            )
        if modification_engine is None:
            raise ValueError(
                "ModificationEngine must be provided via dependency injection"
            )

        self.file_storage = file_storage
        self.modification_engine = modification_engine
        self.http_client = httpx.AsyncClient(
            timeout=10.0, 
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2)
        )
        self.verification_failures = 0

    async def generate_variants(
        self,
        original_image: Image.Image,
        image_record: ImageModel,
    ) -> list[dict]:
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

                # Force garbage collection every few variants to prevent memory buildup
                if variant_number % 5 == 0:
                    gc.collect()

                # Notify verification service with circuit breaker for failures
                if self.verification_failures < 5:
                    try:
                        await self._notify_verification_service(
                            str(image_record.id), variant_info["modification_id"]
                        )
                    except Exception as e:
                        self.verification_failures += 1
                        logger.warning(f"Verification service notification failed for variant {variant_number}: {e}")

            logger.info(
                f"Generated {len(variants)} variants for image {image_record.id}"
            )
            return variants

        except MemoryError as e:
            logger.error(
                f"Memory exhaustion during variant generation for image {image_record.id} at variant {len(variants)}: {e}"
            )
            # Force cleanup and try to save partial progress
            gc.collect()
            raise MemoryError(f"Memory exhaustion during variant generation at variant {len(variants)}")
        except Exception as e:
            logger.error(
                f"Failed to generate variants for image {image_record.id} at variant {len(variants)}: {e}"
            )
            # Ensure cleanup
            gc.collect()
            raise IOError(f"Failed to generate variants at variant {len(variants)}: {str(e)}")

    async def _generate_single_variant(
        self,
        original_image: Image.Image,
        image_record: ImageModel,
        variant_number: int,
        min_modifications: int,
        max_modifications: int,
    ) -> dict:
        num_modifications = random.randint(min_modifications, max_modifications)

        # Apply modifications and immediately save to reduce memory pressure
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
        
        # Extract instructions before clearing result to allow garbage collection
        # of the modified_image contained within the frozen ModificationResult
        instructions = result.instructions
        result = None  # Allow the entire ModificationResult (including image) to be garbage collected

        modification_record = await Modification.create(
            image_id=image_record.id,
            algorithm_type=AlgorithmType.XOR_TRANSFORM,
            variant_number=variant_number,
            instructions=asdict(instructions),
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

    async def get_modification_by_id(self, modification_id: str) -> Modification | None:
        try:
            modification = await Modification.get(id=modification_id)
            return modification
        except Exception:
            return None

    async def get_all_variants_for_image(self, image_id: str) -> list[Modification]:
        modifications = await Modification.filter(image_id=image_id).order_by(
            "variant_number"
        )
        return modifications

    async def get_variant_by_number(
        self, image_id: str, variant_number: int
    ) -> Modification | None:
        modification = await Modification.filter(
            image_id=image_id, variant_number=variant_number
        ).first()
        return modification

    async def _notify_verification_service(
        self, image_id: str, modification_id: str
    ) -> None:
        try:
            verification_request = VerificationRequest(
                image_id=image_id,
                modification_id=modification_id,
            )

            response = await self.http_client.post(
                f"{self.settings.VERIFICATION_SERVICE_URL}/internal/verify",
                json=verification_request.model_dump(mode="json"),
            )

            if response.status_code == 200:
                logger.info(
                    f"Successfully notified verification service for modification {modification_id}"
                )
                # Reset failure counter on success
                self.verification_failures = max(0, self.verification_failures - 1)
            else:
                logger.error(
                    f"Failed to notify verification service for modification {modification_id}: "
                    f"HTTP {response.status_code} - {response.text}"
                )
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}", 
                    request=response.request, 
                    response=response
                )

        except httpx.TimeoutException as e:
            logger.warning(f"Timeout notifying verification service for modification {modification_id}: {e}")
            raise
        except httpx.ConnectError as e:
            logger.warning(f"Connection error notifying verification service for modification {modification_id}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Error notifying verification service for modification {modification_id}: {e}",
                exc_info=True,
            )
            raise

    async def cleanup(self):
        """Cleanup resources when service is shutting down"""
        if hasattr(self, 'http_client'):
            await self.http_client.aclose()
