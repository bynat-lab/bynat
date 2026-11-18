"""`nlp` in-place identity and mutation of the wrapped frame."""

import warnings

import pandas as pd
import pytest

from tests.modules.enrichment.helpers import install_spacy

pytestmark = pytest.mark.unit


def test_nlp_inplace_extract_entities_mutates_the_wrapped_frame(tmp_path, monkeypatch):
    install_spacy(monkeypatch)
    lexicon = {"skills": ["python"]}
    frame = pd.DataFrame({"text": ["python developer"]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.with_cache(tmp_path).extract_entities_nlp(
            "text", lexicon_source=lexicon, skills="skills", inplace=True
        )

    assert returned is None
    assert id(frame) == original_id
    assert "inplace" not in frame.columns
    assert "skills" in frame.columns
