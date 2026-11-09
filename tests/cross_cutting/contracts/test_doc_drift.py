"""Verify that literal docstrings and the accessor stub match implementations."""

import inspect
from pathlib import Path

import pandas as pd

from bynat.cleaning import BaseData
from bynat.cleaning.accessor import BynatAccessor
from tools.sync_docs import check

ROOT = Path(__file__).resolve().parents[3]


def test_docstrings_and_stubs_are_in_sync():
    """Fail with actionable instructions if BaseData docstrings or accessor.pyi drift."""
    problems = check()
    assert not problems, (
        "Docstrings or accessor.pyi are out of sync with shared implementation functions:\n"
        + "\n".join(f"  - {p}" for p in problems)
        + "\n\nFix by running:\n  python tools/sync_docs.py"
    )


def test_package_typing_artifacts_exist():
    """Ensure py.typed marker and accessor stub exist for PEP 561 compliance."""
    assert (ROOT / "bynat" / "py.typed").is_file(), "bynat/py.typed marker missing"
    assert (ROOT / "bynat" / "cleaning" / "accessor.pyi").is_file(), "bynat/cleaning/accessor.pyi missing"


def test_runtime_inspect_signature_and_help_preserved():
    """Runtime inspect.signature and __doc__ must continue to reflect wrapped functions."""
    from bynat.cleaning import stats
    from bynat.cleaning.enrich import currency

    df = pd.DataFrame({"a": [1.0, None], "country": ["US", "US"], "year": [2020, 2020]})

    base_sig = inspect.signature(BaseData.fill_missing)
    assert "strategy" in base_sig.parameters
    assert "hierarchy_cols" in base_sig.parameters
    assert "min_samples" in base_sig.parameters
    assert "fallback_global" in base_sig.parameters
    assert BaseData.fill_missing.__doc__ is not None
    assert "Impute missing values by progressively relaxing" in BaseData.fill_missing.__doc__

    class_sig = inspect.signature(BynatAccessor.fill_missing)
    assert list(class_sig.parameters.keys()) == [
        "self", "target_cols", "strategy", "hierarchy_cols", "min_samples", "fallback_global", "get_hierarchical_stats"
    ]

    bound_sig = inspect.signature(df.bynat.fill_missing)
    assert list(bound_sig.parameters.keys()) == [
        "target_cols", "strategy", "hierarchy_cols", "min_samples", "fallback_global", "get_hierarchical_stats"
    ]
    assert "cache_manager" not in inspect.signature(df.bynat.convert_to_usd).parameters
    assert df.bynat.convert_to_usd.__doc__ == currency.convert_to_usd.__doc__
    assert df.bynat.fill_missing.__doc__ == stats.fill_missing.__doc__

    base_from_sig = inspect.signature(BaseData.fill_missing_from)
    assert "dataset" in base_from_sig.parameters
    assert "match_cols" in base_from_sig.parameters
    assert "targets" in base_from_sig.parameters
    assert "strategy" in base_from_sig.parameters
    assert "hierarchy_cols" in base_from_sig.parameters
    assert "min_samples" in base_from_sig.parameters
    assert "fallback_global" in base_from_sig.parameters
    assert "inplace" in base_from_sig.parameters
    assert "get_hierarchical_stats" in base_from_sig.parameters
    assert BaseData.fill_missing_from.__doc__ is not None
    assert "Impute missing values using statistics calculated from a reference dataset" in BaseData.fill_missing_from.__doc__

    class_from_sig = inspect.signature(BynatAccessor.fill_missing_from)
    assert list(class_from_sig.parameters.keys()) == [
        "self", "dataset", "target_cols", "match_cols", "targets", "strategy",
        "hierarchy_cols", "min_samples", "fallback_global", "get_hierarchical_stats"
    ]

    bound_from_sig = inspect.signature(df.bynat.fill_missing_from)
    assert list(bound_from_sig.parameters.keys()) == [
        "dataset", "target_cols", "match_cols", "targets", "strategy",
        "hierarchy_cols", "min_samples", "fallback_global", "get_hierarchical_stats"
    ]
    assert df.bynat.fill_missing_from.__doc__ == stats.fill_missing_from.__doc__


def test_documented_caching_exports_and_cleaning_namespace_boundary():
    """Verify caching package exports and strict cleaning namespace boundaries."""
    import bynat.cleaning
    from bynat.caching import (
        CACHE_DIR_ENV_VAR,
        DEFAULT_CACHE_DIR,
        CacheManager,
        shared_cache_manager,
    )

    assert CACHE_DIR_ENV_VAR == "BYNAT_CACHE_DIR"
    assert isinstance(DEFAULT_CACHE_DIR, (Path, str))
    assert DEFAULT_CACHE_DIR == "Settings/Cache Data/Automated"
    mgr = shared_cache_manager()
    assert isinstance(mgr, CacheManager)
    assert sorted(bynat.cleaning.__all__) == ["BaseData", "CsvFile", "JsonFile"]

