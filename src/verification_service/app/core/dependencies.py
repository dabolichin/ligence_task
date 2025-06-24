from src.verification_service.app.core.config import Settings, get_settings
from src.verification_service.app.services.instruction_parser import InstructionParser


class ServiceContainer:
    def __init__(self):
        self._settings = None
        self._instruction_parser = None

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

    def set_settings(self, settings: Settings) -> None:
        """For testing purposes."""
        self._settings = settings

    def set_instruction_parser(self, parser: InstructionParser) -> None:
        """For testing purposes."""
        self._instruction_parser = parser

    def reset(self):
        """Reset all cached dependencies."""
        self._settings = None
        self._instruction_parser = None


# Global container instance
_container = ServiceContainer()


def get_settings_dependency() -> Settings:
    """Get settings from the service container."""
    return _container.settings


def get_service_container() -> ServiceContainer:
    """Get the global service container."""
    return _container


def get_instruction_parser_dependency() -> InstructionParser:
    """Get instruction parser from the service container."""
    return _container.instruction_parser


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
