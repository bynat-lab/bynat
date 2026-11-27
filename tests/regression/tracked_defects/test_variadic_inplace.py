import pandas as pd
import pytest

from bynat.cleaning import _columns, _text

pytestmark = pytest.mark.integration


PD01_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="PD-01: the variadic standalone functions absorb `inplace` into their **kwargs; "
    "see docs/TESTING_STANDARDS.md (ML-2)",
)


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


@PD01_XFAIL
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(
            lambda frame: _text.extract_keywords(frame, "text", found=["alpha"], inplace=True),
            id="extract_keywords",
        ),
        pytest.param(
            lambda frame: _text.truncate_after_substring(frame, text="-", inplace=True),
            id="truncate_after_substring",
        ),
        pytest.param(
            lambda frame: _columns.split_list_objects(frame, "items", first=0, inplace=True),
            id="split_list_objects",
        ),
        pytest.param(
            lambda frame: _columns.melt_transform_pivot(
                frame, id_vars="id", value_vars=["left", "right"], inplace=True
            ),
            id="melt_transform_pivot",
        ),
    ],
)
def test_shared_functions_reject_inplace_for_variadic_methods(call):
    with pytest.raises(TypeError):
        call(_variadic_frame())
