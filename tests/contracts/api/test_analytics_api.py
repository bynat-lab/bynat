import pytest

import bynat.analytics

pytestmark = pytest.mark.unit


def test_analytics_contract_exports() -> None:
    assert bynat.analytics.__all__ == ["Analyzer"]
    import bynat.analytics.analyzer as analyzer_mod
    assert analyzer_mod.__all__ == ["Analyzer"]
