import sys
import types
import warnings

import pytest

from bynat.cleaning import BaseData
from tests.integration.enrichment.helpers import install_fake_module

_install = install_fake_module


def _install_fake_spacy(monkeypatch, pipe_calls, load_calls=None, pipe_names=None):
    configured_pipe_names = pipe_names or ["tok2vec", "tagger", "parser", "ner"]

    class Doc(list):
        pass

    class Nlp:
        vocab = types.SimpleNamespace(strings={})
        pipe_names = configured_pipe_names

        def pipe(self, texts, **kwargs):
            texts = list(texts)
            pipe_calls.append((texts, kwargs))
            return [Doc() for _ in texts]

    class Matcher:
        def __init__(self, vocab):
            pass

        def add(self, name, patterns):
            pass

        def __call__(self, doc):
            return []

    def load(model):
        if load_calls is not None:
            load_calls.append(model)
        return Nlp()

    _install(monkeypatch, "spacy", load=load)
    _install(monkeypatch, "spacy.matcher", Matcher=Matcher)


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


def _run_fake_nlp(frame, disable, spacy_model="en_core_web_sm"):
    return frame.extract_entities_nlp(
        "text",
        lexicon_source={"skills": ["python"]},
        spacy_model=spacy_model,
        disable=disable,
        skills="skills",
    )


@pytest.mark.parametrize(
    ("disable", "expected"),
    [
        pytest.param("ner", ("ner",), id="single_string"),
        pytest.param(None, (), id="none"),
    ],
)
def test_extract_entities_nlp_normalizes_single_string_and_none(
    monkeypatch, tmp_path, disable, expected
):
    pipe_calls = []
    _install_fake_spacy(monkeypatch, pipe_calls)
    frame = BaseData({"text": ["python"]}, cache_dir=tmp_path)

    _run_fake_nlp(frame, disable)

    assert [call[1]["disable"] for call in pipe_calls] == [expected, expected]


def test_extract_entities_nlp_noisy_terms_filters_matched_terms(monkeypatch, tmp_path):
    _install_matching_spacy(monkeypatch)
    lexicon = {"skills": ["python", "sql"]}

    baseline = BaseData({"text": ["python sql"]}, cache_dir=tmp_path / "baseline")
    result = baseline.extract_entities_nlp("text", lexicon_source=lexicon, skills="skills")
    assert set(result["skills"].iloc[0]) == {"Python", "Sql"}

    filtered = BaseData({"text": ["python sql"]}, cache_dir=tmp_path / "filtered")
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        filtered_result = filtered.extract_entities_nlp(
            "text", lexicon_source=lexicon, noisy_terms={"sql"}, skills="skills"
        )
    assert set(filtered_result["skills"].iloc[0]) == {"Python"}
