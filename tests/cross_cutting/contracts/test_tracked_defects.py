"""Strict pins for tracked production defects that are not fixed yet.

PD-01's function-level half spans `bynat.cleaning.columns` and
`bynat.cleaning.text`, so it is a cross-component contract and lives here.
The accessor half is fixed and covered in
`tests/cross_cutting/accessor/inplace/test_argument_binding.py`.
"""

import pandas as pd
import pytest

from bynat.cleaning import columns, text

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
