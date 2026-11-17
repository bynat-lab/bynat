"""`geocode` in-place identity and mutation of the wrapped frame."""

import warnings

import pandas as pd
import pytest

from tests.modules.enrichment.helpers import Geocoder, Location

pytestmark = pytest.mark.unit


def test_geocode_inplace_fill_missing_coordinates_mutates_the_wrapped_frame(tmp_path):
    geocoder = Geocoder({"Paris": Location(10.0, 20.0)})
    frame = pd.DataFrame({"city": ["Paris"], "lat": [None], "lng": [None]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.with_cache(tmp_path).fill_missing_coordinates(
            "city", lat_col="lat", long_col="lng", provider=geocoder, inplace=True
        )

    assert returned is None
    assert id(frame) == original_id
    assert frame["lat"].tolist() == [10.0]
    assert frame["lng"].tolist() == [20.0]
