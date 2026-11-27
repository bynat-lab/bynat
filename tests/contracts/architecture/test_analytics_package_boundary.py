import importlib

import pytest

pytestmark = pytest.mark.unit


def test_analytics_contract_invalid_import() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bynat.analytics.Analytics")
