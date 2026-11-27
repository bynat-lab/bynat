import pytest

from bynat.cleaning.enrich import (
    Geocoder,
    GoogleTranslatorProvider,
    NominatimGeocoder,
    RateSource,
    Translator,
    YFinanceRateSource,
)

pytestmark = pytest.mark.unit


def test_default_providers_satisfy_the_protocols():
    assert issubclass(GoogleTranslatorProvider, Translator)
    assert issubclass(NominatimGeocoder, Geocoder)
    assert issubclass(YFinanceRateSource, RateSource)


def test_documented_enrich_exports_include_the_default_providers():
    import bynat.cleaning.enrich as enrich

    assert set(enrich.__all__) == {
        "Translator",
        "Geocoder",
        "RateSource",
        "GoogleTranslatorProvider",
        "NominatimGeocoder",
        "YFinanceRateSource",
    }
    for name in enrich.__all__:
        assert callable(getattr(enrich, name))
