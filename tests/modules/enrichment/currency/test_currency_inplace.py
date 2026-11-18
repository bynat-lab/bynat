"""`currency` in-place identity and mutation of the wrapped frame."""

import warnings

import pandas as pd
import pytest

from tests.modules.enrichment.helpers import RateSource, install_currency_lookup

pytestmark = pytest.mark.unit


def test_currency_inplace_convert_to_usd_mutates_the_wrapped_frame(tmp_path, monkeypatch):
    install_currency_lookup(monkeypatch)
    rates = RateSource({("EGP", 2020): 17.0})
    frame = pd.DataFrame({"country": ["Egypt"], "year": [2020], "salary": [170.0]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.with_cache(tmp_path).convert_to_usd(
            "salary", country_col="country", year_col="year", provider=rates, inplace=True
        )

    assert returned is None
    assert id(frame) == original_id
    assert frame["salary_usd"].tolist() == [10.0]
