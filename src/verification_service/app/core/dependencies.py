from image_modification_algorithms import ModificationEngine

from src.verification_service.app.core.config import Settings, get_settings
from src.verification_service.app.services.image_comparison import (
    ImageComparisonService,
)
from src.verification_service.app.services.image_reversal import (
    ImageReversalService,
)
from src.verification_service.app.services.instruction_retrieval import (
    InstructionRetrievalService,
)
from src.verification_service.app.services.verification_history import (
    VerificationHistoryService,
)
from src.verification_service.app.services.verification_orchestrator import (
    VerificationOrchestrator,
)
from src.verification_service.app.services.verification_persistence import (
    VerificationPersistence,
)


class ServiceContainer:
    def __init__(self):
        self._settings = None

        self._modification_engine = None
        self._instruction_retrieval_service = None
        self._image_comparison_service = None
        self._image_reversal_service = None
        self._verification_persistence = None
        self._verification_orchestrator = None
        self._verification_history_service = None

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def modification_engine(self) -> ModificationEngine:
        if self._modification_engine is None:
            self._modification_engine = ModificationEngine()
        return self._modification_engine

    @property
    def instruction_retrieval_service(self) -> InstructionRetrievalService:
        if self._instruction_retrieval_service is None:
            self._instruction_retrieval_service = InstructionRetrievalService(
                settings=self.settings
            )
        return self._instruction_retrieval_service

    @property
    def image_comparison_service(self) -> ImageComparisonService:
        if self._image_comparison_service is None:
            self._image_comparison_service = ImageComparisonService()
        return self._image_comparison_service

    @property
    def image_reversal_service(self) -> ImageReversalService:
        if self._image_reversal_service is None:
            self._image_reversal_service = ImageReversalService(
                image_comparison_service=self.image_comparison_service
            )
        return self._image_reversal_service

    @property
    def verification_persistence(self) -> VerificationPersistence:
        if self._verification_persistence is None:
            self._verification_persistence = VerificationPersistence()
        return self._verification_persistence

    @property
    def verification_orchestrator(self) -> VerificationOrchestrator:
        if self._verification_orchestrator is None:
            self._verification_orchestrator = VerificationOrchestrator(
                instruction_retrieval_service=self.instruction_retrieval_service,
                modification_engine=self.modification_engine,
                image_reversal_service=self.image_reversal_service,
                verification_persistence=self.verification_persistence,
            )
        return self._verification_orchestrator

    @property
    def verification_history_service(self) -> VerificationHistoryService:
        if self._verification_history_service is None:
            self._verification_history_service = VerificationHistoryService()
        return self._verification_history_service

    def set_settings(self, settings: Settings) -> None:
        """For testing purposes."""
        self._settings = settings

    def set_modification_engine(self, engine: ModificationEngine) -> None:
        """For testing purposes."""
        self._modification_engine = engine

    def set_instruction_retrieval_service(
        self, service: InstructionRetrievalService
    ) -> None:
        """For testing purposes."""
        self._instruction_retrieval_service = service

    def set_image_comparison_service(self, service: ImageComparisonService) -> None:
        """For testing purposes."""
        self._image_comparison_service = service

    def set_image_reversal_service(self, service: ImageReversalService) -> None:
        """For testing purposes."""
        self._image_reversal_service = service

    def set_verification_persistence(
        self, persistence: VerificationPersistence
    ) -> None:
        """For testing purposes."""
        self._verification_persistence = persistence

    def set_verification_orchestrator(
        self, orchestrator: VerificationOrchestrator
    ) -> None:
        """For testing purposes."""
        self._verification_orchestrator = orchestrator

    def set_verification_history_service(
        self, service: VerificationHistoryService
    ) -> None:
        """For testing purposes."""
        self._verification_history_service = service

    def reset(self):
        """Reset all cached dependencies."""
        self._settings = None

        self._modification_engine = None
        self._instruction_retrieval_service = None
        self._image_comparison_service = None
        self._image_reversal_service = None
        self._verification_persistence = None
        self._verification_orchestrator = None
        self._verification_history_service = None


# Global container instance
_container = ServiceContainer()


def get_service_container() -> ServiceContainer:
    """Get the global service container."""
    return _container


def get_verification_orchestrator_dependency() -> VerificationOrchestrator:
    """Get verification orchestrator for FastAPI dependency injection."""
    return _container.verification_orchestrator


def get_verification_history_service_dependency() -> VerificationHistoryService:
    """Get verification history service for FastAPI dependency injection."""
    return _container.verification_history_service


def reset_service_container() -> None:
    """Reset all dependencies in the global container."""
    _container.reset()
