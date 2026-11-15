"""Module-local fixtures for the caching test suite.

Every caching test must run against an isolated cache directory so a failure
cannot leak state into another test or into the user's default cache location
(§8.8). The autouse fixture below redirects the process-wide default for the
duration of each test; tests that pass an explicit ``cache_dir`` are unaffected.
"""

import pytest


@pytest.fixture
def cache_dir(tmp_path):
    """Return an isolated cache directory under the test's ``tmp_path``."""
    return tmp_path / "cache"


@pytest.fixture(autouse=True)
def _isolated_default_cache_dir(cache_dir, monkeypatch):
    """Redirect the default cache directory to an isolated per-test path."""
    monkeypatch.setenv("BYNAT_CACHE_DIR", str(cache_dir))
