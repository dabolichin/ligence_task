from image_modification_algorithms import ModificationEngine

from src.verification_service.app.core.config import Settings, get_settings
from src.verification_service.app.services.instruction_parser import InstructionParser
from src.verification_service.app.services.instruction_retrieval import (
    InstructionRetrievalService,
)
from src.verification_service.app.services.verification_orchestrator import (
    VerificationOrchestrator,
)


class ServiceContainer:
    def __init__(self):
        self._settings = None
        self._instruction_parser = None
        self._modification_engine = None
        self._instruction_retrieval_service = None
        self._verification_orchestrator = None

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def instruction_parser(self) -> InstructionParser:
        if self._instruction_parser is None:
            self._instruction_parser = InstructionParser()
        return self._instruction_parser

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
    def verification_orchestrator(self) -> VerificationOrchestrator:
        if self._verification_orchestrator is None:
            self._verification_orchestrator = VerificationOrchestrator(
                instruction_retrieval_service=self.instruction_retrieval_service,
                instruction_parser=self.instruction_parser,
                modification_engine=self.modification_engine,
            )
        return self._verification_orchestrator

    def set_settings(self, settings: Settings) -> None:
        """For testing purposes."""
        self._settings = settings

    def set_instruction_parser(self, parser: InstructionParser) -> None:
        """For testing purposes."""
        self._instruction_parser = parser

    def set_modification_engine(self, engine: ModificationEngine) -> None:
        """For testing purposes."""
        self._modification_engine = engine

    def set_instruction_retrieval_service(
        self, service: InstructionRetrievalService
    ) -> None:
        """For testing purposes."""
        self._instruction_retrieval_service = service

    def set_verification_orchestrator(
        self, orchestrator: VerificationOrchestrator
    ) -> None:
        """For testing purposes."""
        self._verification_orchestrator = orchestrator

    def reset(self):
        """Reset all cached dependencies."""
        self._settings = None
        self._instruction_parser = None
        self._modification_engine = None
        self._instruction_retrieval_service = None
        self._verification_orchestrator = None


# Global container instance
_container = ServiceContainer()


def get_settings_dependency() -> Settings:
    """Get settings from the service container."""
    return _container.settings


def get_service_container() -> ServiceContainer:
    """Get the global service container."""
    return _container


def get_instruction_parser_dependency() -> InstructionParser:
    return _container.instruction_parser


def get_modification_engine_dependency() -> ModificationEngine:
    return _container.modification_engine


def get_instruction_retrieval_service_dependency() -> InstructionRetrievalService:
    return _container.instruction_retrieval_service


def get_verification_orchestrator_dependency() -> VerificationOrchestrator:
    return _container.verification_orchestrator


# Testing support functions
def get_test_container() -> ServiceContainer:
    """Create a fresh service container for testing."""
    return ServiceContainer()


def override_container_for_testing(test_container: ServiceContainer) -> None:
    """Override the global container with a test container."""
    global _container
    _container = test_container


def restore_container() -> None:
    """Restore the global container to a fresh instance."""
    global _container
    _container = ServiceContainer()


def reset_service_container() -> None:
    """Reset all dependencies in the global container."""
    _container.reset()
