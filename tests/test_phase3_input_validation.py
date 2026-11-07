"""Phase 3 input-validation contract coverage (TEST-02).

Pins documented input-validation contracts that the Phase 1/2 suite did not
cover: rejected argument types and values, malformed inputs, missing columns,
boundary values, exception types and messages, and class/accessor parity.

Two documented target contracts are not implemented by production yet. They are
pinned with a strict ``xfail`` that names the Phase 1 audit finding, so the gap
stays visible and the test fails the moment the production fix lands (an
unexpected pass fails the suite under ``strict=True``):

* ``PD-01`` -- variadic shared functions and accessor methods silently absorb
  ``inplace`` instead of rejecting it (``S-4`` / ``ML-2``).
* ``PD-02`` -- ``handle_outliers`` / ``drop_outliers`` do not validate
  ``min_samples`` (``MS-3a``).
"""

import json
import logging

import pandas as pd
import pytest

from bynat.cleaning import BaseData, columns, io, stats, text

INPLACE_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="PD-01: variadic shared/accessor methods absorb `inplace` instead of "
    "rejecting it; see docs/temb/TEST-02-phase1-audit.md (S-4/ML-2)",
)

MIN_SAMPLES_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="PD-02: handle_outliers/drop_outliers do not validate min_samples; "
    "see docs/temb/TEST-02-phase1-audit.md (MS-3a)",
)

INVALID_MIN_SAMPLES = [
    pytest.param(True, id="bool-true"),
    pytest.param(False, id="bool-false"),
    pytest.param(0, id="zero"),
    pytest.param(-1, id="negative"),
    pytest.param(2.5, id="float"),
    pytest.param("5", id="string"),
]


def _variadic_frame():
    return pd.DataFrame(
        {
            "id": [1, 2],
            "text": ["alpha-beta", "gamma"],
            "items": [["a", "b"], ["c"]],
            "left": ["x", "y"],
            "right": ["p", "q"],
        }
    )


# ---------------------------------------------------------------------------
# PD-01 -- `inplace` rejection on shared functions and the accessor
# ---------------------------------------------------------------------------


@INPLACE_XFAIL
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(
            lambda frame: frame.bynat.extract_keywords("text", found=["alpha"], inplace=True),
            id="extract_keywords",
        ),
        pytest.param(
            lambda frame: frame.bynat.truncate_after_substring(text="-", inplace=True),
            id="truncate_after_substring",
        ),
        pytest.param(
            lambda frame: frame.bynat.split_list_objects("items", first=0, inplace=True),
            id="split_list_objects",
        ),
        pytest.param(
            lambda frame: frame.bynat.melt_transform_pivot(
                id_vars="id", value_vars=["left", "right"], inplace=True
            ),
            id="melt_transform_pivot",
        ),
    ],
)
def test_accessor_rejects_inplace_for_variadic_methods(call):
    with pytest.raises(TypeError):
        call(_variadic_frame())


@INPLACE_XFAIL
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(
            lambda frame: text.extract_keywords(frame, "text", found=["alpha"], inplace=True),
            id="extract_keywords",
        ),
        pytest.param(
            lambda frame: text.truncate_after_substring(frame, text="-", inplace=True),
            id="truncate_after_substring",
        ),
        pytest.param(
            lambda frame: columns.split_list_objects(frame, "items", first=0, inplace=True),
            id="split_list_objects",
        ),
        pytest.param(
            lambda frame: columns.melt_transform_pivot(
                frame, id_vars="id", value_vars=["left", "right"], inplace=True
            ),
            id="melt_transform_pivot",
        ),
    ],
)
def test_shared_functions_reject_inplace_for_variadic_methods(call):
    with pytest.raises(TypeError):
        call(_variadic_frame())


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda frame: frame.bynat.rename_all_DOTS(inplace=True), id="rename_all_DOTS"),
        pytest.param(lambda frame: frame.bynat.fill_missing("id", inplace=True), id="fill_missing"),
        pytest.param(
            lambda frame: frame.bynat.handle_outliers("id", hierarchy_cols=[], inplace=True),
            id="handle_outliers",
        ),
        pytest.param(
            lambda frame: frame.bynat.get_hierarchical_stats("id", hierarchy_cols=[], inplace=True),
            id="get_hierarchical_stats",
        ),
        pytest.param(lambda frame: frame.bynat.profile(inplace=True), id="profile"),
    ],
)
def test_accessor_rejects_inplace_for_non_variadic_methods(call):
    with pytest.raises(TypeError):
        call(pd.DataFrame({"id": [1, 2]}))


def test_inplace_is_accepted_by_the_class_api_and_rejected_by_the_accessor(tmp_path):
    data = {"g": ["a", "a"], "v": [1.0, None]}
    frame = BaseData(data, cache_dir=tmp_path)

    assert frame.fill_missing("v", hierarchy_cols="g", inplace=True) is None
    assert frame["v"].tolist() == [1.0, 1.0]

    with pytest.raises(TypeError):
        pd.DataFrame(data).bynat.fill_missing("v", hierarchy_cols="g", inplace=True)


# ---------------------------------------------------------------------------
# PD-02 -- `min_samples` validation on the outlier methods
# ---------------------------------------------------------------------------


@MIN_SAMPLES_XFAIL
@pytest.mark.parametrize("value", INVALID_MIN_SAMPLES)
def test_handle_outliers_rejects_invalid_min_samples(value):
    frame = pd.DataFrame({"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})

    with pytest.raises(ValueError, match="min_samples"):
        stats.handle_outliers(frame, "v", hierarchy_cols=["g"], min_samples=value)


@MIN_SAMPLES_XFAIL
@pytest.mark.parametrize("value", INVALID_MIN_SAMPLES)
def test_drop_outliers_rejects_invalid_min_samples(value):
    frame = pd.DataFrame({"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})

    with pytest.raises(ValueError, match="min_samples"):
        stats.drop_outliers(frame, "v", hierarchy_cols=["g"], min_samples=value)


@pytest.mark.parametrize("value", INVALID_MIN_SAMPLES)
def test_fill_missing_and_fill_missing_from_reject_invalid_min_samples(value):
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, None]})
    reference = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})

    with pytest.raises(ValueError, match="min_samples must be an integer"):
        stats.fill_missing(frame, "v", hierarchy_cols="g", min_samples=value)

    with pytest.raises(ValueError, match="min_samples must be an integer"):
        stats.fill_missing_from(frame, reference, "v", hierarchy_cols="g", min_samples=value)


@pytest.mark.parametrize(
    ("min_samples", "evaluated"),
    [
        pytest.param(6, True, id="exactly-min_samples"),
        pytest.param(7, False, id="above-min_samples"),
    ],
)
def test_handle_outliers_min_samples_boundary(min_samples, evaluated):
    frame = pd.DataFrame({"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})

    result = stats.handle_outliers(frame, "v", hierarchy_cols=["g"], min_samples=min_samples)

    assert bool(result["v"].isna().iloc[-1]) is evaluated


def test_min_samples_counts_only_non_null_observations():
    frame = pd.DataFrame(
        {
            "g": ["a", "a", "a", "b", "b"],
            "v": [1.0, 3.0, None, 10.0, None],
        }
    )

    result = stats.fill_missing(frame, "v", hierarchy_cols=["g"], min_samples=2)

    # Group 'a' has two non-null observations, so it supplies the median 2.0.
    assert result.loc[2, "v"] == 2.0
    # Group 'b' has one non-null observation, below the threshold, so it stays NaN.
    assert pd.isna(result.loc[4, "v"])


# ---------------------------------------------------------------------------
# HO-7 / DO-6 -- hierarchy validation on the outlier methods
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method_name", ["handle_outliers", "drop_outliers"])
@pytest.mark.parametrize("hierarchy_cols", [[], None], ids=["empty-list", "none"])
def test_outlier_methods_warn_and_return_an_unchanged_copy_without_hierarchy(
    caplog, method_name, hierarchy_cols
):
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})
    original = frame.copy(deep=True)

    with caplog.at_level(logging.WARNING, logger="bynat.cleaning.Cleaning"):
        result = getattr(stats, method_name)(frame, "v", hierarchy_cols=hierarchy_cols)

    assert result is not frame
    pd.testing.assert_frame_equal(result, original)
    assert "No hierarchy columns provided." in caplog.text


@pytest.mark.parametrize("method_name", ["handle_outliers", "drop_outliers"])
def test_outlier_methods_raise_keyerror_for_a_missing_named_hierarchy(method_name):
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})

    with pytest.raises(KeyError, match="missing_hierarchy"):
        getattr(stats, method_name)(frame, "v", hierarchy_cols=["missing_hierarchy"])


# ---------------------------------------------------------------------------
# FM-23 / FF-19 -- non-numeric targets with numeric strategies
# ---------------------------------------------------------------------------


def test_fill_missing_non_numeric_target_with_hierarchy_raises_typeerror():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", None, "y"]})

    with pytest.raises(TypeError):
        stats.fill_missing(frame, "label", strategy="median", hierarchy_cols=["g"])


def test_fill_missing_non_numeric_target_with_fallback_global_raises_typeerror():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", None, "y"]})

    with pytest.raises(TypeError):
        stats.fill_missing(frame, "label", strategy="median", fallback_global=True)


def test_fill_missing_non_numeric_target_without_hierarchy_is_unchanged():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", None, "y"]})
    original = frame.copy(deep=True)

    result = stats.fill_missing(frame, "label", strategy="median")

    pd.testing.assert_frame_equal(result, original)


def test_fill_missing_non_numeric_all_nan_target_does_not_raise():
    frame = pd.DataFrame({"g": ["a", "a"], "label": [None, None]})

    result = stats.fill_missing(frame, "label", strategy="median", hierarchy_cols=["g"])

    assert result["label"].isna().all()


def test_fill_missing_from_non_numeric_all_nan_target_is_exempt():
    reference = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "b"], "v": pd.Series([None, None], dtype=object)})

    result = stats.fill_missing_from(
        target, reference, "v", strategy="median", hierarchy_cols=["g"]
    )

    assert result["v"].tolist() == [1.0, 2.0]


@pytest.mark.parametrize("strategy", ["median", "mean"])
def test_get_hierarchical_stats_non_numeric_target_raises_typeerror(strategy):
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", "y", "z"]})

    with pytest.raises(TypeError):
        stats.get_hierarchical_stats(frame, "label", strategy=strategy, hierarchy_cols=["g"])


def test_get_hierarchical_stats_non_numeric_target_mode_is_allowed():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", "y", "z"]})

    result = stats.get_hierarchical_stats(frame, "label", strategy="mode", hierarchy_cols=["g"])

    assert result["statistic"].tolist() == ["x", "z"]


# ---------------------------------------------------------------------------
# FM-11a / FF-13a -- some target columns missing, others valid
# ---------------------------------------------------------------------------


def test_fill_missing_skips_missing_targets_and_fills_valid_ones():
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, None], "w": [None, None]})
    original = frame.copy(deep=True)

    result = stats.fill_missing(frame, "v", "missing", hierarchy_cols=["g"])

    assert result["v"].tolist() == [1.0, 1.0]
    assert "missing" not in result.columns
    pd.testing.assert_frame_equal(frame, original)


def test_fill_missing_from_skips_missing_targets_and_fills_valid_ones():
    reference = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "b"], "v": [None, None]})

    result = stats.fill_missing_from(target, reference, "v", "missing", hierarchy_cols=["g"])

    assert result["v"].tolist() == [1.0, 2.0]
    assert "missing" not in result.columns


def test_get_hierarchical_stats_skips_missing_targets():
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 3.0]})

    result = stats.get_hierarchical_stats(frame, "v", "missing", hierarchy_cols=["g"])

    assert result["target_column"].unique().tolist() == ["v"]


# ---------------------------------------------------------------------------
# FF-8 -- duplicate targets are deduplicated
# ---------------------------------------------------------------------------


def test_fill_missing_from_duplicate_targets_are_deduplicated():
    reference = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "b"], "v": [None, None]})

    unique = stats.fill_missing_from(target, reference, "v", hierarchy_cols=["g"])
    duplicated = stats.fill_missing_from(target, reference, "v", "v", hierarchy_cols=["g"])

    pd.testing.assert_frame_equal(duplicated, unique)


# ---------------------------------------------------------------------------
# get_hierarchical_stats -- strategy validation
# ---------------------------------------------------------------------------


def test_get_hierarchical_stats_rejects_non_iterable_strategy():
    frame = pd.DataFrame({"g": ["a"], "v": [1.0]})

    with pytest.raises(TypeError, match="strategy must be a string or an iterable"):
        stats.get_hierarchical_stats(frame, "v", strategy=5, hierarchy_cols=["g"])


def test_get_hierarchical_stats_rejects_empty_strategy_iterable():
    frame = pd.DataFrame({"g": ["a"], "v": [1.0]})

    with pytest.raises(ValueError, match="at least one strategy"):
        stats.get_hierarchical_stats(frame, "v", strategy=[], hierarchy_cols=["g"])


def test_get_hierarchical_stats_rejects_unknown_strategy():
    frame = pd.DataFrame({"g": ["a"], "v": [1.0]})

    with pytest.raises(ValueError, match="Invalid strategy 'bogus'"):
        stats.get_hierarchical_stats(frame, "v", strategy="bogus", hierarchy_cols=["g"])


# ---------------------------------------------------------------------------
# fill_missing_from -- match_cols validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "match_cols",
    [
        pytest.param({"": "v"}, id="empty-key"),
        pytest.param({"v": ""}, id="empty-value"),
    ],
)
def test_fill_missing_from_rejects_empty_match_cols_strings(match_cols):
    reference = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "b"], "v": [None, None]})

    with pytest.raises(ValueError, match="cannot be empty strings"):
        stats.fill_missing_from(target, reference, "v", match_cols=match_cols)


# ---------------------------------------------------------------------------
# melt_transform_pivot -- documented argument validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "exception", "message"),
    [
        pytest.param(
            {"id_vars": None}, ValueError, "id_vars must contain at least one", id="id-vars-none"
        ),
        pytest.param(
            {"id_vars": []}, ValueError, "id_vars must contain at least one", id="id-vars-empty"
        ),
        pytest.param(
            {"id_vars": 5},
            TypeError,
            "id_vars must be a column name or an iterable",
            id="id-vars-non-iterable",
        ),
        pytest.param(
            {"id_vars": ["missing"]}, ValueError, "id_vars not found", id="id-vars-missing"
        ),
        pytest.param(
            {"id_vars": ["id", "id"]},
            ValueError,
            "id_vars contains duplicate",
            id="id-vars-duplicate",
        ),
        pytest.param(
            {"id_vars": "id", "value_vars": ["missing"]},
            ValueError,
            "value_vars not found",
            id="value-vars-missing",
        ),
        pytest.param(
            {"id_vars": "id", "value_vars": ["left", "left"]},
            ValueError,
            "value_vars contains duplicate",
            id="value-vars-duplicate",
        ),
        pytest.param(
            {"id_vars": "id", "value_vars": ["id", "left"]},
            ValueError,
            "value_vars cannot include id_vars",
            id="value-vars-overlap",
        ),
        pytest.param(
            {"id_vars": "id", "var_name": "  "},
            ValueError,
            "var_name must be a non-empty string",
            id="var-name-empty",
        ),
        pytest.param(
            {"id_vars": "id", "value_name": ""},
            ValueError,
            "value_name must be a non-empty string",
            id="value-name-empty",
        ),
        pytest.param(
            {"id_vars": "id", "var_name": "same", "value_name": "same"},
            ValueError,
            "must be different",
            id="var-name-equals-value-name",
        ),
        pytest.param(
            {"id_vars": "id", "value_name": "left"},
            ValueError,
            "cannot match an existing dataframe column",
            id="value-name-existing",
        ),
        pytest.param(
            {"id_vars": "id", "aggfunc": 5},
            TypeError,
            "aggfunc must be a string or callable",
            id="aggfunc-invalid",
        ),
        pytest.param(
            {"id_vars": "id", "transform_func": "not-callable"},
            TypeError,
            "transform_func must be callable",
            id="transform-func-non-callable",
        ),
        pytest.param(
            {"id_vars": "id", "transform_func": lambda values: [1, 2, 3]},
            ValueError,
            "same number of values",
            id="transform-func-length-mismatch",
        ),
        pytest.param(
            {"id_vars": "id", "transform_func": lambda values: 1 / 0},
            RuntimeError,
            "transform_func failed",
            id="transform-func-raises",
        ),
    ],
)
def test_melt_transform_pivot_rejects_invalid_arguments(kwargs, exception, message):
    frame = pd.DataFrame({"id": [1, 2], "left": ["a", "b"], "right": ["c", "d"]})

    with pytest.raises(exception, match=message):
        columns.melt_transform_pivot(frame, **kwargs)


# ---------------------------------------------------------------------------
# read_json -- documented loader validation
# ---------------------------------------------------------------------------


def test_read_json_missing_key_raises_keyerror(tmp_path):
    path = tmp_path / "records.json"
    path.write_text(json.dumps({"items": [{"a": 1}]}), encoding="utf-8")

    with pytest.raises(KeyError, match="missing"):
        io.read_json(path, key="missing")


def test_read_json_key_on_non_dict_payload_raises_typeerror(tmp_path):
    path = tmp_path / "records.json"
    path.write_text(json.dumps([{"a": 1}]), encoding="utf-8")

    with pytest.raises(TypeError, match="dictionary payload"):
        io.read_json(path, key="items")


# ---------------------------------------------------------------------------
# translate_conditional_column -- documented argument validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("threshold", [-0.1, 1.1], ids=["below-range", "above-range"])
def test_translate_conditional_column_rejects_out_of_range_threshold(tmp_path, threshold):
    frame = pd.DataFrame({"partition": ["a"], "detect": ["hello"], "label": ["x"]})

    with pytest.raises(ValueError, match="threshold"):
        frame.bynat.with_cache(tmp_path).translate_conditional_column(
            "partition", "detect", "label", threshold=threshold
        )


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        pytest.param("sample_size", 0, id="sample-size-zero"),
        pytest.param("sample_size", -1, id="sample-size-negative"),
        pytest.param("sample_size", 2.5, id="sample-size-float"),
        pytest.param("number_of_samples", 0, id="number-of-samples-zero"),
        pytest.param("save_every", 0, id="save-every-zero"),
    ],
)
def test_translate_conditional_column_rejects_non_positive_integer_parameters(
    tmp_path, parameter, value
):
    frame = pd.DataFrame({"partition": ["a"], "detect": ["hello"], "label": ["x"]})

    with pytest.raises(ValueError, match=parameter):
        frame.bynat.with_cache(tmp_path).translate_conditional_column(
            "partition", "detect", "label", **{parameter: value}
        )


# ---------------------------------------------------------------------------
# fill_missing_coordinates -- documented argument validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(2.5, id="float"),
        pytest.param("5", id="string"),
        pytest.param(True, id="bool"),
    ],
)
def test_fill_missing_coordinates_rejects_non_positive_integer_save_every(tmp_path, value):
    frame = pd.DataFrame({"city": ["Paris"], "lat": [None], "lng": [None]})

    with pytest.raises(ValueError, match="save_every"):
        frame.bynat.with_cache(tmp_path).fill_missing_coordinates(
            "city", lat_col="lat", long_col="lng", save_every=value
        )
