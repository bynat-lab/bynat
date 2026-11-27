import inspect
import sys
import types

import pytest

from bynat.cleaning import BaseData
from bynat.cleaning.enrich import _nlp

pytestmark = pytest.mark.unit


def _install_matching_spacy(monkeypatch):
    """A spaCy stand-in whose matcher binds every token to the added column.

    Unlike ``_install_fake_spacy`` (which never matches), this lets tests
    observe real matches and therefore the effect of ``noisy_terms``.
    """

    class Doc(list):
        pass

    class Nlp:
        vocab = types.SimpleNamespace(strings={"skills": "skills"})
        pipe_names = ["tok2vec", "tagger", "parser", "ner"]

        def pipe(self, texts, **kwargs):
            docs = []
            for text in texts:
                doc = Doc()
                for token in str(text).split():
                    doc.append(
                        types.SimpleNamespace(
                            text=token, lemma_=token.lower(), pos_="NOUN", is_alpha=True
                        )
                    )
                docs.append(doc)
            return docs

    class Matcher:
        def __init__(self, vocab):
            self._names = []

        def add(self, name, patterns):
            self._names.append(name)

        def __call__(self, doc):
            name = self._names[-1]
            return [(name, i, i + 1) for i in range(len(doc))]

    monkeypatch.setitem(sys.modules, "spacy", types.SimpleNamespace(load=lambda model: Nlp()))
    monkeypatch.setitem(sys.modules, "spacy.matcher", types.SimpleNamespace(Matcher=Matcher))


def test_extract_entities_nlp_signature_exposes_noisy_terms_only():
    parameters = inspect.signature(BaseData.extract_entities_nlp).parameters
    assert "noisy_terms" in parameters
    assert "noisey_terms" not in parameters


def test_extract_entities_nlp_rejects_the_noisey_terms_spelling(monkeypatch, tmp_path):
    _install_matching_spacy(monkeypatch)
    lexicon = {"skills": ["python", "sql"]}

    frame = BaseData({"text": ["python sql"]}, cache_dir=tmp_path / "misspelled")
    with pytest.raises(TypeError, match="did you mean 'noisy_terms'"):
        frame.extract_entities_nlp(
            "text", lexicon_source=lexicon, noisey_terms={"sql"}, skills="skills"
        )


def test_free_enrichment_extract_entities_nlp_rejects_noisey_terms_spelling(tmp_path):
    lexicon = {"skills": ["python", "sql"]}
    frame = BaseData({"text": ["python sql"]}, cache_dir=tmp_path / "free")
    with pytest.raises(TypeError, match="did you mean 'noisy_terms'"):
        _nlp.extract_entities_nlp(
            frame,
            "text",
            lexicon_source=lexicon,
            cache_manager=frame.cache_manager,
            noisey_terms={"sql"},
            skills="skills",
        )
