import warnings

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


def _outlier_stats_frame():
    return pd.DataFrame({"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})


def _missing_stats_frame():
    return pd.DataFrame({"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, None]})


FILL_MISSING_FROM_STATS = pytest.param(
    "fill_missing_from",
    _missing_stats_frame,
    ("v",),
    {"hierarchy_cols": ["g"]},
    _outlier_stats_frame,
    id="fill_missing_from",
)


STATS_TRANSFORMS = [
    pytest.param(
        "handle_outliers",
        _outlier_stats_frame,
        ("v",),
        {"hierarchy_cols": ["g"]},
        None,
        id="handle_outliers",
    ),
    pytest.param(
        "drop_outliers",
        _outlier_stats_frame,
        ("v",),
        {"hierarchy_cols": ["g"]},
        None,
        id="drop_outliers",
    ),
    pytest.param(
        "fill_missing",
        _missing_stats_frame,
        ("v",),
        {"hierarchy_cols": ["g"]},
        None,
        id="fill_missing",
    ),
    FILL_MISSING_FROM_STATS,
]


def _stats_call_arguments(args, kwargs, reference_factory):
    call_args = (reference_factory(), *args) if reference_factory is not None else args
    return call_args, kwargs


@pytest.mark.parametrize(
    ("name", "frame_factory", "args", "kwargs", "reference_factory"), STATS_TRANSFORMS
)
def test_accessor_inplace_stats_returns_none_when_statistics_are_not_requested(
    name, frame_factory, args, kwargs, reference_factory
):
    frame = frame_factory()
    before = frame.copy(deep=True)
    original_id = id(frame)

    call_args, call_kwargs = _stats_call_arguments(args, kwargs, reference_factory)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = getattr(frame.bynat, name)(*call_args, inplace=True, **call_kwargs)

    assert returned is None
    assert id(frame) == original_id
    assert not frame.equals(before)
    expected_args, expected_kwargs = _stats_call_arguments(args, kwargs, reference_factory)
    expected = getattr(frame_factory().bynat, name)(*expected_args, **expected_kwargs)
    pd.testing.assert_frame_equal(frame, expected)


@pytest.mark.parametrize(
    ("name", "frame_factory", "args", "kwargs", "reference_factory"), STATS_TRANSFORMS
)
def test_accessor_inplace_stats_returns_statistics_and_still_mutates(
    name, frame_factory, args, kwargs, reference_factory
):
    frame = frame_factory()
    before = frame.copy(deep=True)
    original_id = id(frame)

    call_args, call_kwargs = _stats_call_arguments(args, kwargs, reference_factory)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = getattr(frame.bynat, name)(
            *call_args,
            inplace=True,
            get_hierarchical_stats=True,
            **call_kwargs,
        )

    assert isinstance(returned, pd.DataFrame)
    assert not returned.empty
    assert id(frame) == original_id
    assert not frame.equals(before)
    expected_args, expected_kwargs = _stats_call_arguments(args, kwargs, reference_factory)
    expected_frame, expected_stats = getattr(frame_factory().bynat, name)(
        *expected_args,
        get_hierarchical_stats=True,
        **expected_kwargs,
    )
    pd.testing.assert_frame_equal(frame, expected_frame)
    pd.testing.assert_frame_equal(returned, expected_stats)


def test_accessor_inplace_fill_missing_from_does_not_mutate_the_reference():
    reference = _outlier_stats_frame()
    reference_before = reference.copy(deep=True)
    frame = _missing_stats_frame()
    target_before = frame.copy(deep=True)
    original_id = id(frame)

    returned = frame.bynat.fill_missing_from(reference, "v", inplace=True, hierarchy_cols=["g"])

    assert returned is None
    assert id(frame) == original_id
    assert not frame.equals(target_before)
    pd.testing.assert_frame_equal(reference, reference_before)
