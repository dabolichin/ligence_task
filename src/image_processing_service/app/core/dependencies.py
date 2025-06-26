from functools import lru_cache

from image_modification_algorithms import ModificationEngine

from ..core.config import Settings, get_settings
from ..services.file_storage import FileStorageService
from ..services.processing_orchestrator import ProcessingOrchestrator
from ..services.variant_generation import VariantGenerationService


@lru_cache()
def get_settings_dependency() -> Settings:
    return get_settings()


@lru_cache()
def get_file_storage() -> FileStorageService:
    settings = get_settings()
    return FileStorageService(settings)


@lru_cache()
def get_modification_engine() -> ModificationEngine:
    return ModificationEngine()


def get_variant_generator() -> VariantGenerationService:
    return VariantGenerationService(
        file_storage=get_file_storage(),
        modification_engine=get_modification_engine(),
        settings=get_settings(),
    )


def get_processing_orchestrator() -> ProcessingOrchestrator:
    return ProcessingOrchestrator(
        file_storage=get_file_storage(),
        variant_generator=get_variant_generator(),
        settings=get_settings(),
    )
