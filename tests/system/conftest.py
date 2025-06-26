import pytest


def pytest_configure(config):
    """Add custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")


def pytest_collection_modifyitems(config, items):
    """Auto-mark slow tests."""
    for item in items:
        if "larger" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.slow)
