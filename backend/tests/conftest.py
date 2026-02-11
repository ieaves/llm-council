import pytest


# Ensure pytest-asyncio uses the modern auto mode so async tests run without explicit event loop fixtures
def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as requiring asyncio")


@pytest.fixture(scope="session", autouse=True)
def _set_asyncio_mode():
    # Newer pytest-asyncio prefers env/config; set default here to avoid warnings.
    import os

    os.environ.setdefault("PYTEST_ASYNCIO_MODE", "auto")
