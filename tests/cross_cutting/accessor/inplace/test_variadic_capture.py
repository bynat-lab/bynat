"""Variadic accessor `**kwargs` must not capture the `inplace` flag (PD-01)."""

import warnings

import pandas as pd
import pytest

from tests.modules.enrichment.helpers import install_spacy

pytestmark = pytest.mark.integration


def _variadic_frame():
    return pd.DataFrame(
        {
            "id": [1, 2],
            "text": ["alpha-beta", "gamma"],
            "items": [["a", "b"], ["c"]],
            "left": ["x", "y"],
            "right": ["p", "q"],
            "title": ["alpha-beta", "gamma"],
        }
    )


VARIADIC_TRANSFORMS = [
    pytest.param("extract_keywords", ("text",), {"found": ["alpha"]}, id="extract_keywords"),
    pytest.param("split_list_objects", (), {"source_col": "items", "first": 0}, id="split_list_objects"),
    pytest.param("truncate_after_substring", (), {"regex": False, "title": "-"}, id="truncate_after_substring"),
    pytest.param("melt_transform_pivot", (), {"id_vars": "id", "value_vars": ["left", "right"]}, id="melt_transform_pivot"),
    pytest.param(
        "extract_entities_nlp",
        ("text",),
        {"lexicon_source": {"skills": ["alpha"]}, "skills": "skills"},
        id="extract_entities_nlp",
    ),
]


@pytest.mark.parametrize(("name", "args", "kwargs"), VARIADIC_TRANSFORMS)
def test_accessor_inplace_is_recognised_and_not_absorbed_by_variadic_arguments(name, args, kwargs, monkeypatch):
    if name == "extract_entities_nlp":
        install_spacy(monkeypatch)

    frame = _variadic_frame()
    before = frame.copy(deep=True)
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = getattr(frame.bynat, name)(*args, inplace=True, **kwargs)

    assert returned is None
    assert id(frame) == original_id
    assert "inplace" not in frame.columns
    assert not frame.equals(before)


@pytest.mark.parametrize(("name", "args", "kwargs"), VARIADIC_TRANSFORMS)
def test_accessor_variadic_arguments_still_work_without_inplace(name, args, kwargs, monkeypatch, tmp_path):
    if name == "extract_entities_nlp":
        install_spacy(monkeypatch)

    frame = _variadic_frame()
    before = frame.copy(deep=True)
    accessor = frame.bynat.with_cache(tmp_path) if name == "extract_entities_nlp" else frame.bynat

    result = getattr(accessor, name)(*args, **kwargs)

    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)
    if name == "melt_transform_pivot":
        assert list(result.columns) == ["id", "left", "right"]
    elif name == "extract_entities_nlp":
        assert "skills" in result.columns
    elif name == "extract_keywords":
        assert "found" in result.columns
        assert result["found"].iloc[0] == "Alpha"
    elif name == "split_list_objects":
        assert "first" in result.columns
        assert result["first"].tolist() == ["a", "c"]
    else:
        assert result["title"].tolist() == ["alpha", "gamma"]


def test_accessor_inplace_is_not_forwarded_to_transform_func_kwargs():
    recorder_kwargs = []
    seen_lengths = []

    def recorder(series, **kwargs):
        seen_lengths.append(len(series))
        recorder_kwargs.extend(sorted(kwargs))
        return series

    frame = _variadic_frame()
    before = frame.copy(deep=True)
    original_id = id(frame)

    returned = frame.bynat.melt_transform_pivot(
        id_vars="id", value_vars=["left", "right"], transform_func=recorder, inplace=True
    )

    assert returned is None
    assert recorder_kwargs == []
    assert seen_lengths == [4]
    assert id(frame) == original_id
    assert list(frame.columns) == ["id", "left", "right"]
    assert not frame.equals(before)
