import json

import numpy as np
import pandas as pd
import pytest

from bynat.profiling import profile
from tests.unit.profiling.helpers import EXPECTED_STATS_KEYS_BY_KIND


def test_clean_scalar_bool_before_int():
    df = pd.DataFrame({"obj": [True, "x", True]})
    rep = profile(df)
    col = rep.columns["obj"]
    assert col.kind == "other"
    assert col.stats["top"] is True
    assert type(col.stats["top"]) is bool
    assert col.stats["top_frequency"] == 2

    from bynat.profiling._internal.processing import clean_scalar

    assert clean_scalar(True) is True
    assert type(clean_scalar(True)) is bool
    assert clean_scalar(False) is False
    assert type(clean_scalar(False)) is bool
    assert clean_scalar(np.bool_(True)) is True
    assert type(clean_scalar(np.bool_(True))) is bool
    assert clean_scalar(1) == 1
    assert type(clean_scalar(1)) is int


def test_timedelta_columns_and_clean_scalar():
    td_series = pd.Series([pd.Timedelta(days=1), pd.Timedelta(days=2), pd.Timedelta(days=1)])
    df = pd.DataFrame({"td": td_series})
    rep = profile(df)
    col = rep.columns["td"]
    assert col.kind == "other"
    assert col.stats["top"] == "P1DT0H0M0S"
    assert col.stats["top_frequency"] == 2
    assert col.stats["top_proportion"] == pytest.approx(2 / 3)

    dumped = json.dumps(rep.to_dict())
    assert "P1DT0H0M0S" in dumped

    import datetime

    from bynat.profiling._internal.processing import clean_scalar

    assert clean_scalar(pd.Timedelta(days=1)) == "P1DT0H0M0S"
    assert clean_scalar(np.timedelta64(10, "s")) == "P0DT0H0M10S"
    assert clean_scalar(datetime.timedelta(days=2)) == "P2DT0H0M0S"


def test_categorical_pd_categorical():
    cat_series = pd.Series(pd.Categorical(["apple", "banana", "apple", None]))
    df = pd.DataFrame({"cat": cat_series})
    rep = profile(df)
    col = rep.columns["cat"]
    assert col.kind == "categorical"
    assert set(col.stats.keys()) == EXPECTED_STATS_KEYS_BY_KIND["categorical"]
    assert col.stats["top"] == "apple"
    assert col.stats["top_frequency"] == 2
    assert col.stats["top_proportion"] == pytest.approx(2 / 3)


def test_tz_aware_datetime():
    tz_series = pd.Series(pd.date_range("2024-01-01", periods=3, tz="UTC"))
    df = pd.DataFrame({"dt_tz": tz_series})
    rep = profile(df)
    col = rep.columns["dt_tz"]
    assert col.kind == "datetime"
    assert set(col.stats.keys()) == EXPECTED_STATS_KEYS_BY_KIND["datetime"]
    assert col.stats["min"] == "2024-01-01T00:00:00+00:00"
    assert col.stats["max"] == "2024-01-03T00:00:00+00:00"
    assert col.stats["range_days"] == pytest.approx(2.0)
