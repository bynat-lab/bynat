import json

import numpy as np
import pandas as pd

from bynat.profiling import profile


def test_contract_json_dumps_mixed_dataframe():
    df = pd.DataFrame(
        {
            "num_standard": [1.5, 2.5, np.nan, 4.5],
            "num_nullable_int": pd.Series([10, None, 30, 40], dtype="Int64"),
            "num_nullable_float": pd.Series([1.1, 2.2, None, 4.4], dtype="Float64"),
            "cat_str": ["apple", "banana", None, "apple"],
            "cat_categorical": pd.Series(pd.Categorical(["cat", "dog", None, "cat"])),
            "cat_nullable_str": pd.Series(["x", None, "z", "x"], dtype="string"),
            "bool_standard": [True, False, None, True],
            "bool_nullable": pd.Series([True, None, False, False], dtype="boolean"),
            "dt_naive": pd.to_datetime(["2024-01-01", "2024-01-02", None, "2024-01-04"]),
            "dt_tz": pd.Series(pd.date_range("2024-01-01", periods=4, tz="UTC")),
            "timedelta_col": [pd.Timedelta(days=1), pd.Timedelta(hours=2), None, pd.Timedelta(days=1)],
            "unhashable_list": [["a", "b"], ["c"], None, ["a", "b"]],
            "unhashable_dict": [{"a": 1}, {"b": 2}, None, {"a": 1}],
        }
    )

    report = profile(df)
    raw_dict = report.to_dict()

    dumped = json.dumps(raw_dict)
    assert isinstance(dumped, str)

    parsed = json.loads(dumped)
    assert set(parsed.keys()) == {"dataset", "columns"}
    assert parsed["dataset"]["row_count"] == 4
    assert parsed["dataset"]["column_count"] == 13
    assert "timedelta_col" in parsed["columns"]
    assert "unhashable_dict" in parsed["columns"]
