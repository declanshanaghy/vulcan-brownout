"""pytest configuration for Vulcan Brownout component tests."""

import pytest

# Configure pytest-asyncio for automatic event loop handling
pytest_plugins = ('pytest_asyncio',)


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
