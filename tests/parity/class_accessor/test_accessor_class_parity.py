import pandas as pd
import pytest

from bynat.cleaning import BaseData
from bynat.profiling import ProfileReport
from bynat.profiling import profile as profiling_profile
from tests.shared.constants import PARITY_DATA

pytestmark = pytest.mark.integration


@pytest.fixture()
def frame():
    return pd.DataFrame({
        "region": ["north", "south", "north", "east"],
        "revenue": [10.0, 20.5, 30.25, 40.0],
        "order_date": pd.to_datetime([
            "2026-01-05", "2026-01-20", "2026-02-11", "2026-02-28",
        ]),
    })


TRANSFORM_PARITY_CASES = [
    pytest.param(lambda obj, data: obj.drop_by_substring("user"), id="drop_by_substring"),
    pytest.param(lambda obj, data: obj.drop_CLASS_columns(), id="drop_CLASS_columns"),
    pytest.param(lambda obj, data: obj.rename_by_substring("name", "n"), id="rename_by_substring"),
    pytest.param(lambda obj, data: obj.rename_all_DOTS(), id="rename_all_DOTS"),
    pytest.param(lambda obj, data: obj.reorder_columns("A", "B"), id="reorder_columns"),
    pytest.param(
        lambda obj, data: obj.move_column("value", "id", position="before"), id="move_column"
    ),
    pytest.param(lambda obj, data: obj.align_lat_lng(), id="align_lat_lng"),
    pytest.param(
        lambda obj, data: obj.melt_transform_pivot(id_vars="id", value_vars=["C", "A"]),
        id="melt_transform_pivot",
    ),
    pytest.param(
        lambda obj, data: obj.split_list_objects("items", first=0), id="split_list_objects"
    ),
    pytest.param(
        lambda obj, data: obj.extract_keywords("description", colors=["blue", "red"]),
        id="extract_keywords",
    ),
    pytest.param(
        lambda obj, data: obj.truncate_after_substring(regex=False, title="-"),
        id="truncate_after_substring",
    ),
    pytest.param(
        lambda obj, data: obj.fill_missing("score", hierarchy_cols="g"), id="fill_missing"
    ),
    pytest.param(
        lambda obj, data: obj.fill_missing_from(data, "score", hierarchy_cols="g"),
        id="fill_missing_from",
    ),
    pytest.param(
        lambda obj, data: obj.handle_outliers("value", hierarchy_cols=["g"], min_samples=2),
        id="handle_outliers",
    ),
    pytest.param(
        lambda obj, data: obj.drop_outliers("value", hierarchy_cols=["g"], min_samples=2),
        id="drop_outliers",
    ),
]


def test_accessor_methods_return_new_plain_frames_and_leave_the_source_alone():
    frame = pd.DataFrame({
        "user.name": ["Ada", "Grace"], "description": ["Blue shoes", "red shirt"],
        "group": ["x", "x"], "score": [1.0, None],
    })
    original = frame.copy()

    renamed = frame.bynat.rename_all_DOTS()
    keywords = frame.bynat.extract_keywords("description", colors=["blue", "red"])
    filled = frame.bynat.fill_missing("score", hierarchy_cols="group")
    unchanged = frame.bynat.drop_by_substring("missing")

    assert type(renamed) is pd.DataFrame
    assert list(renamed.columns) == ["user_name", "description", "group", "score"]
    assert keywords["colors"].tolist() == ["Blue", "Red"]
    assert filled["score"].tolist() == [1.0, 1.0]
    assert unchanged is not frame
    pd.testing.assert_frame_equal(unchanged, frame)
    pd.testing.assert_frame_equal(frame, original)


def test_accessor_matches_basedata_results(tmp_path):
    data = {"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]}
    legacy = BaseData(data, cache_dir=tmp_path)

    plain = pd.DataFrame(data)

    pd.testing.assert_frame_equal(
        plain.bynat.drop_outliers("v", hierarchy_cols=["g"]),
        pd.DataFrame(legacy.drop_outliers("v", hierarchy_cols=["g"])),
    )
    result, stats = plain.bynat.handle_outliers("v", hierarchy_cols=["g"], get_hierarchical_stats=True)
    assert type(stats) is pd.DataFrame
    assert result["v"].isna().tolist() == [False] * 5 + [True]


def test_accessor_profile_output_type_dispatch_matches_profiling():
    frame = pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "a"]})
    expected = profiling_profile(frame)

    assert frame.bynat.profile().to_dict() == expected.to_dict()
    assert frame.bynat.profile(output_type=ProfileReport).to_dict() == expected.to_dict()
    assert frame.bynat.profile(output_type=dict) == expected.to_dict()
    pd.testing.assert_frame_equal(
        frame.bynat.profile(output_type=pd.DataFrame), expected.to_dataframe()
    )

    with pytest.raises(TypeError, match="Unsupported output_type"):
        frame.bynat.profile(output_type=int)


def test_accessor_profile_matches_basedata_and_profiling_results(tmp_path):
    frame = pd.DataFrame({"g": ["a", "a", "b"], "v": [1.0, 2.0, 3.0]})
    legacy = BaseData(frame, cache_dir=tmp_path)

    assert frame.bynat.profile().to_dict() == legacy.profile().to_dict()
    pd.testing.assert_frame_equal(
        frame.bynat.profile(output_type=pd.DataFrame),
        legacy.profile(output_type=pd.DataFrame),
    )


@pytest.mark.parametrize("transform", TRANSFORM_PARITY_CASES)
def test_accessor_and_basedata_produce_equal_results(tmp_path, transform):
    base = BaseData(PARITY_DATA, cache_dir=tmp_path)
    plain = pd.DataFrame(PARITY_DATA)

    base_result = transform(base, base)
    accessor_result = transform(plain.bynat, plain)

    assert isinstance(base_result, BaseData)
    assert type(accessor_result) is pd.DataFrame
    pd.testing.assert_frame_equal(pd.DataFrame(base_result), accessor_result)
