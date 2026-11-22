"""Root package API contract: exports, forbidden aliases, and accessor registration."""

import importlib
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

import bynat

pytestmark = pytest.mark.unit

PACKAGE_ROOT = Path(bynat.__file__).resolve().parent
EXPECTED_ALL = ["cleaning", "caching", "analytics", "profiling", "read_csv", "read_json"]
PACKAGE_EXPORTS = {
    "cleaning": "bynat.cleaning",
    "caching": "bynat.caching",
    "analytics": "bynat.analytics",
    "profiling": "bynat.profiling",
}
FORBIDDEN_ATTRIBUTES = (
    "BaseData",
    "CsvFile",
    "JsonFile",
    "ProfileReport",
    "profile",
    "BynatAccessor",
)


def test_root_all_is_exactly_the_six_names_in_order():
    assert bynat.__all__ == EXPECTED_ALL
    assert set(bynat.__all__) == set(EXPECTED_ALL)


def test_root_exposes_the_four_package_objects():
    for name, module_name in PACKAGE_EXPORTS.items():
        attribute = getattr(bynat, name)
        assert attribute is importlib.import_module(module_name)
        assert attribute.__name__ == module_name


def test_root_readers_are_canonical_references_from_cleaning_io():
    from bynat.cleaning import io

    assert bynat.read_csv is io.read_csv
    assert bynat.read_json is io.read_json
    assert bynat.read_csv.__module__ == "bynat.cleaning.io"
    assert bynat.read_json.__module__ == "bynat.cleaning.io"


def test_root_does_not_expose_implementation_objects():
    for name in FORBIDDEN_ATTRIBUTES:
        assert not hasattr(bynat, name), name

    assert "_accessors" not in bynat.__all__
    assert "_accessor_registration" not in bynat.__all__


def test_package_level_public_imports_remain_available():
    from bynat.analytics import Analyzer
    from bynat.caching import (
        CACHE_DIR_ENV_VAR,
        DEFAULT_CACHE_DIR,
        CacheManager,
        shared_cache_manager,
    )
    from bynat.cleaning import BaseData, CsvFile, JsonFile
    from bynat.profiling import ProfileReport, profile

    assert BaseData.__module__ == "bynat.cleaning.base"
    assert CsvFile.__module__ == "bynat.cleaning.base"
    assert JsonFile.__module__ == "bynat.cleaning.base"
    assert profile.__module__ == "bynat.profiling.profile"
    assert ProfileReport.__module__ == "bynat.profiling.report"
    assert Analyzer.__module__ == "bynat.analytics.analyzer"
    assert CacheManager.__module__ == "bynat.caching.manager"
    assert shared_cache_manager.__module__ == "bynat.caching.manager"
    assert CACHE_DIR_ENV_VAR == "BYNAT_CACHE_DIR"
    assert DEFAULT_CACHE_DIR == "Settings/Cache Data/Automated"


def test_importing_bynat_registers_the_dataframe_accessor():
    from bynat._accessors import BynatAccessor

    frame = pd.DataFrame({"a": [1]})

    assert isinstance(frame.bynat, BynatAccessor)


def test_root_reader_signatures_match_cleaning_io():
    from bynat.cleaning import io

    assert inspect.signature(bynat.read_csv) == inspect.signature(io.read_csv)
    assert inspect.signature(bynat.read_json) == inspect.signature(io.read_json)


def test_root_readers_load_csv_and_json(tmp_path):
    csv_path = tmp_path / "people.csv"
    csv_path.write_text("name;age\nGrace;28\n", encoding="utf-8")
    json_path = tmp_path / "jobs.json"
    json_path.write_text(
        json.dumps({"items": [{"name": "Ada", "info": {"age": 36}}]}),
        encoding="utf-8",
    )

    csv_frame = bynat.read_csv(csv_path, sep=";")
    json_frame = bynat.read_json(json_path, key="items")

    assert type(csv_frame) is pd.DataFrame
    assert csv_frame.to_dict("records") == [{"name": "Grace", "age": 28}]
    assert type(json_frame) is pd.DataFrame
    assert list(json_frame.columns) == ["name", "info.age"]
    assert json_frame.iloc[0].to_dict() == {"name": "Ada", "info.age": 36}


@pytest.mark.parametrize(
    "first_import",
    [
        "bynat.cleaning",
        "bynat.caching",
        "bynat.analytics",
        "bynat.profiling",
        "bynat.cleaning.io",
        "bynat._accessors",
    ],
)
def test_fresh_import_order_registers_and_exports_the_root_api(first_import):
    script = (
        f"import {first_import}\n"
        "import bynat\n"
        "import pandas as pd\n"
        "from bynat._accessors import BynatAccessor\n"
        "from bynat.cleaning import io\n"
        f"assert bynat.__all__ == {EXPECTED_ALL!r}\n"
        "assert bynat.read_csv is io.read_csv\n"
        "assert bynat.read_json is io.read_json\n"
        "assert isinstance(pd.DataFrame({'a': [1]}).bynat, BynatAccessor)\n"
        "for forbidden in ('BaseData', 'CsvFile', 'JsonFile', 'ProfileReport', 'BynatAccessor', 'profile'):\n"
        "    assert not hasattr(bynat, forbidden), forbidden\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(PACKAGE_ROOT.parent),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
