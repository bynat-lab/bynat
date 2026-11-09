import pytest

from bynat.cleaning import BaseData
from tests.shared.constants import OUTPUT_COLUMNS


@pytest.mark.parametrize(
    "method_name",
    ["handle_outliers", "drop_outliers", "fill_missing"],
)
def test_hierarchy_methods_keep_existing_return_contract_when_stats_disabled(
    tmp_path, method_name
):
    frame = BaseData(
        {"group": ["a"] * 6, "value": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]},
        cache_dir=tmp_path,
    )
    hierarchy_cols = "group" if method_name == "fill_missing" else ["group"]
    kwargs = {"hierarchy_cols": hierarchy_cols, "get_hierarchical_stats": False}
    if method_name == "fill_missing":
        frame.loc[1, "value"] = None

    result = getattr(frame, method_name)("value", **kwargs)

    assert isinstance(result, BaseData)
    assert not isinstance(result, tuple)


@pytest.mark.parametrize(
    "method_name",
    ["handle_outliers", "drop_outliers", "fill_missing"],
)
@pytest.mark.parametrize(
    "stats_kwargs", [{}, {"get_hierarchical_stats": False}],
    ids=["omitted", "explicit_false"],
)
def test_hierarchy_methods_skip_stats_calculation_when_disabled(
    monkeypatch, tmp_path, method_name, stats_kwargs
):
    frame = BaseData(
        {"group": ["a"] * 6, "value": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]},
        cache_dir=tmp_path,
    )
    hierarchy_cols = "group" if method_name == "fill_missing" else ["group"]
    if method_name == "fill_missing":
        frame.loc[1, "value"] = None

    def unexpected_stats_call(*args, **kwargs):
        pytest.fail("get_hierarchical_stats must not run when disabled")

    monkeypatch.setattr(frame, "get_hierarchical_stats", unexpected_stats_call)

    result = getattr(frame, method_name)(
        "value", hierarchy_cols=hierarchy_cols, **stats_kwargs
    )

    assert isinstance(result, BaseData)
    assert not isinstance(result, tuple)


@pytest.mark.parametrize(
    "method_name",
    ["handle_outliers", "drop_outliers", "fill_missing"],
)
def test_hierarchy_methods_return_stats_for_copy_and_inplace_modes(tmp_path, method_name):
    source = BaseData(
        {"group": ["a"] * 6, "value": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]},
        cache_dir=tmp_path,
    )
    if method_name == "fill_missing":
        source.loc[1, "value"] = None
    hierarchy_cols = "group" if method_name == "fill_missing" else ["group"]
    kwargs = {"hierarchy_cols": hierarchy_cols, "get_hierarchical_stats": True}

    result, stats = getattr(source, method_name)("value", **kwargs)

    assert isinstance(result, BaseData)
    assert isinstance(stats, BaseData)
    assert list(stats.columns) == OUTPUT_COLUMNS
    assert stats["target_column"].tolist() == ["value"]

    inplace_source = source.copy()
    inplace_stats = getattr(inplace_source, method_name)(
        "value", inplace=True, **kwargs
    )

    assert isinstance(inplace_stats, BaseData)
    assert list(inplace_stats.columns) == OUTPUT_COLUMNS
    assert not isinstance(inplace_stats, tuple)
    if method_name == "handle_outliers":
        assert inplace_source["value"].isna().tolist() == [False] * 5 + [True]
    elif method_name == "drop_outliers":
        assert len(inplace_source) == 5
    else:
        assert inplace_source["value"].isna().sum() == 0


def test_hierarchy_stats_are_extracted_before_drop_outliers(tmp_path):
    frame = BaseData(
        {"group": ["a"] * 7, "value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 100.0]},
        cache_dir=tmp_path,
    )

    result, stats = frame.drop_outliers(
        "value",
        hierarchy_cols=["group"],
        get_hierarchical_stats=True,
    )

    assert result["value"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert stats["hierarchy_level"].tolist() == [1]
    assert stats["statistic"].tolist() == [4.0]


def test_hierarchy_stats_are_extracted_before_progressive_fill(tmp_path):
    frame = BaseData(
        {
            "region": ["east", "east", "east", "east"],
            "department": ["a", "a", "b", "b"],
            "value": [1.0, None, 9.0, 11.0],
        },
        cache_dir=tmp_path,
    )

    result, stats = frame.fill_missing(
        "value",
        strategy="mean",
        hierarchy_cols=["region", "department"],
        get_hierarchical_stats=True,
    )

    assert result["value"].tolist() == [1.0, 1.0, 9.0, 11.0]
    region_stat = stats.loc[
        (stats["hierarchy_level"] == 1) & (stats["hierarchy_columns"] == ("region",)),
        "statistic",
    ]
    assert region_stat.tolist() == [7.0]
