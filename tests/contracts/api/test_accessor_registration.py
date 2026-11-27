import warnings

import pandas as pd
import pytest

from bynat._accessors import BynatAccessor
from bynat.cleaning import BaseData, CsvFile, JsonFile

pytestmark = pytest.mark.integration


def test_importing_bynat_registers_the_accessor():
    frame = pd.DataFrame({"a": [1]})

    assert isinstance(frame.bynat, BynatAccessor)


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(lambda path: BaseData({"a": [1]}, cache_dir=path), id="BaseData"),
        pytest.param(lambda path: JsonFile({"a": [1]}, cache_dir=path), id="JsonFile"),
        pytest.param(lambda path: CsvFile({"a": [1]}, cache_dir=path), id="CsvFile"),
    ],
)
def test_supported_classes_construct_without_warning(tmp_path, factory):
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        frame = factory(tmp_path)

    assert isinstance(frame, BaseData)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        frame.copy()
        frame[frame["a"] > 0].rename(columns={"a": "b"})
        pd.concat([frame, frame]).merge(frame, on="a")
        frame.assign(g="x").get_hierarchical_stats("a", hierarchy_cols="g")
