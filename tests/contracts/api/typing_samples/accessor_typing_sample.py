"""Static-only mypy sample for the typed ``DataFrame.bynat`` accessor.

This file is deliberately not named ``test_*`` so pytest never collects it.
It exists so ``mypy`` proves the generated accessor stub exposes precise
parameter types while the runtime alias remains plain pandas.
"""

from __future__ import annotations

from typing import assert_type, cast

import pandas as pd

from bynat.pandas_typing import DataFrame

frame = DataFrame({
    'keep': [1, 2, 3],
    'unused': [4, 5, 6],
    'salary': [100.0, 200.0, 300.0],
    'country': ['US', 'EG', 'US'],
    'year': [2020, 2021, 2022],
    'value': [1.0, 2.0, 3.0],
})

assert_type(frame.bynat.drop_by_substring('unused'), pd.DataFrame | None)

# Positional `inplace` slot, then the keyword form.
frame.bynat.drop_by_substring('unused', True)
frame.bynat.drop_by_substring('unused', inplace=True)

# A cached accessor method and a statistics accessor method.
frame.bynat.convert_to_usd('salary', country_col='country', year_col='year')
frame.bynat.get_hierarchical_stats('value')

# Narrow the intentionally widened union for downstream use.
cleaned = cast(pd.DataFrame, frame.bynat.drop_by_substring('unused'))
assert_type(cleaned, pd.DataFrame)

# Negative checks: with warn_unused_ignores each ignore must be required.
frame.bynat.drop_by_substring(123)  # type: ignore[arg-type]
frame.bynat.drop_by_substring('unused', bogus=True)  # type: ignore[call-arg]
