from app.core.config import get_settings


class ServiceContainer:
    def __init__(self):
        self._settings = get_settings()

    @property
    def settings(self):
        return self._settings

    def reset(self):
        pass


# Global container instance
_container = ServiceContainer()


def get_settings_dependency():
    return get_settings()


def get_service_container() -> ServiceContainer:
    return _container


# Testing support functions
def get_test_container() -> ServiceContainer:
    return ServiceContainer()


def override_container_for_testing(test_container: ServiceContainer) -> None:
    global _container
    _container = test_container


def restore_container() -> None:
    global _container
    _container = ServiceContainer()


def reset_service_container():
    _container.reset()
