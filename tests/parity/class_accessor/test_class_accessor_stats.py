import pandas as pd
import pytest

from bynat.cleaning import BaseData

pytestmark = pytest.mark.unit


def test_accessor_inplace_stats_matches_the_class_api_copy_result(tmp_path):
    data = {"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, None]}
    legacy = BaseData(data, cache_dir=tmp_path)
    plain = pd.DataFrame(data)
    legacy_id = id(legacy)
    plain_id = id(plain)

    legacy_returned = legacy.fill_missing("v", hierarchy_cols=["g"], inplace=True)
    plain_returned = plain.bynat.fill_missing("v", hierarchy_cols=["g"], inplace=True)

    assert legacy_returned is None
    assert plain_returned is None
    assert id(legacy) == legacy_id
    assert id(plain) == plain_id
    pd.testing.assert_frame_equal(pd.DataFrame(plain), pd.DataFrame(legacy))
