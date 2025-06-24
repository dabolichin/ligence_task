from typing import Optional

from ..core.config import get_settings
from ..services.algorithms.xor_transform import XORTransformAlgorithm
from ..services.file_storage import FileStorageService
from ..services.processing_orchestrator import ProcessingOrchestrator
from ..services.variant_generation import VariantGenerationService


class ServiceContainer:
    def __init__(self):
        self._settings = get_settings()
        self._file_storage: Optional[FileStorageService] = None
        self._xor_algorithm: Optional[XORTransformAlgorithm] = None
        self._variant_generator: Optional[VariantGenerationService] = None
        self._processing_orchestrator: Optional[ProcessingOrchestrator] = None

    @property
    def settings(self):
        return self._settings

    @property
    def file_storage(self) -> FileStorageService:
        if self._file_storage is None:
            self._file_storage = FileStorageService(self._settings)
        return self._file_storage

    @property
    def xor_algorithm(self) -> XORTransformAlgorithm:
        if self._xor_algorithm is None:
            self._xor_algorithm = XORTransformAlgorithm()
        return self._xor_algorithm

    @property
    def variant_generator(self) -> VariantGenerationService:
        if self._variant_generator is None:
            self._variant_generator = VariantGenerationService(
                file_storage=self.file_storage,
                xor_algorithm=self.xor_algorithm,
                settings=self._settings,
            )
        return self._variant_generator

    @property
    def processing_orchestrator(self) -> ProcessingOrchestrator:
        if self._processing_orchestrator is None:
            self._processing_orchestrator = ProcessingOrchestrator(
                file_storage=self.file_storage,
                variant_generator=self.variant_generator,
                settings=self._settings,
            )
        return self._processing_orchestrator

    def set_file_storage(self, file_storage: FileStorageService) -> None:
        self._file_storage = file_storage
        # Clear dependent services so they get recreated with new dependency
        self._variant_generator = None
        self._processing_orchestrator = None

    def set_xor_algorithm(self, xor_algorithm: XORTransformAlgorithm) -> None:
        self._xor_algorithm = xor_algorithm
        # Clear dependent services so they get recreated with new dependency
        self._variant_generator = None
        self._processing_orchestrator = None

    def set_variant_generator(
        self, variant_generator: VariantGenerationService
    ) -> None:
        self._variant_generator = variant_generator
        # Clear dependent services so they get recreated with new dependency
        self._processing_orchestrator = None

    def set_processing_orchestrator(
        self, processing_orchestrator: ProcessingOrchestrator
    ) -> None:
        self._processing_orchestrator = processing_orchestrator

    def reset(self):
        self._file_storage = None
        self._xor_algorithm = None
        self._variant_generator = None
        self._processing_orchestrator = None


# Global container instance
_container = ServiceContainer()


def get_settings_dependency():
    return get_settings()


def get_file_storage() -> FileStorageService:
    return _container.file_storage


def get_variant_generator() -> VariantGenerationService:
    return _container.variant_generator


def get_processing_orchestrator() -> ProcessingOrchestrator:
    return _container.processing_orchestrator


def get_test_container() -> ServiceContainer:
    return ServiceContainer()


def override_container_for_testing(test_container: ServiceContainer) -> None:
    global _container
    _container = test_container


def restore_container() -> None:
    global _container
    _container = ServiceContainer()
