import pandas as pd
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.integration.enrichment.helpers import DictTranslator, install_langdetect


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(seed=st.integers(min_value=0, max_value=5000))
def test_translate_conditional_column_determinism_property(monkeypatch, tmp_path, seed):
    install_langdetect(monkeypatch, lambda t: "ar" if "arabic" in t else "en")
    translator = DictTranslator({"arabic_word": "english_word", "hello": "hello"})

    df = pd.DataFrame(
        {
            "part": ["p1", "p1", "p2", "p2"] * 4,
            "detect": ["arabic text", "arabic more", "english word", "english more"] * 4,
            "target": ["arabic_word", "arabic_word", "hello", "hello"] * 4,
        }
    )
    original = df.copy(deep=True)

    cache_dir1 = tmp_path / f"c1_{seed}"
    cache_dir2 = tmp_path / f"c2_{seed}"

    res1 = df.bynat.with_cache(cache_dir1).translate_conditional_column(
        "part", "detect", "target", sample_size=2, number_of_samples=2, random_state=seed, provider=translator
    )
    res2 = df.bynat.with_cache(cache_dir2).translate_conditional_column(
        "part", "detect", "target", sample_size=2, number_of_samples=2, random_state=seed, provider=translator
    )

    pd.testing.assert_frame_equal(df, original)
    pd.testing.assert_frame_equal(res1, res2)
