import pandas as pd
import pytest

from bynat.cleaning import BaseData
from tests.shared.constants import PARITY_DATA

pytestmark = pytest.mark.unit


EXTRAS_METHODS = {"categorize_by_reference"}


def _require_optional_dependency(name):
    if name in EXTRAS_METHODS:
        pytest.importorskip("ahocorasick")


TEXT_TRANSFORMS = [
    pytest.param("extract_keywords", ("description",), {"colors": ["blue", "red"]}, id="extract_keywords"),
    pytest.param("truncate_after_substring", (), {"regex": False, "title": "-"}, id="truncate_after_substring"),
    pytest.param(
        "categorize_by_reference",
        ("description",),
        {"target_col": "field", "reference": {"Colors": ["blue", "red"]}},
        id="categorize_by_reference",
        marks=pytest.mark.extras,
    ),
]


def _frame():
    return pd.DataFrame(PARITY_DATA)


@pytest.mark.parametrize(("name", "args", "kwargs"), TEXT_TRANSFORMS)
def test_text_inplace_result_matches_the_class_api(name, args, kwargs):
    _require_optional_dependency(name)
    base = BaseData(PARITY_DATA)
    plain = _frame()

    class_result = getattr(base, name)(*args, **kwargs)
    accessor_result = getattr(plain.bynat, name)(*args, **kwargs)

    pd.testing.assert_frame_equal(pd.DataFrame(class_result), accessor_result)
