"""Offline NLP entity extraction tests using fake spaCy modules."""

import inspect
import sys
import types
import warnings

import pytest

from bynat.cleaning import BaseData
from bynat.cleaning.enrich import nlp
from tests.modules.enrichment.helpers import install_fake_module

pytestmark = pytest.mark.unit


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


def test_extract_entities_nlp_default_disable_reaches_both_pipe_calls(monkeypatch, tmp_path):
    pipe_calls = []

    class Doc(list):
        pass

    class Nlp:
        vocab = types.SimpleNamespace(strings={})
        pipe_names = ["tok2vec", "tagger", "parser", "ner"]

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

    _install(monkeypatch, "spacy", load=lambda model: Nlp())
    _install(monkeypatch, "spacy.matcher", Matcher=Matcher)

    frame = BaseData({"text": ["python"]}, cache_dir=tmp_path)
    result = frame.extract_entities_nlp(
        "text", lexicon_source={"skills": ["python"]}, skills="skills"
    )

    assert result["skills"].tolist() == [[]]
    assert [call[1]["disable"] for call in pipe_calls] == [
        ("parser", "ner"),
        ("parser", "ner"),
    ]


def test_extract_entities_nlp_skips_unused_pipes_and_reuses_cache(monkeypatch, tmp_path):
    pipe_calls = []

    class Doc(list):
        pass

    class Nlp:
        vocab = types.SimpleNamespace(strings={})
        pipe_names = ["tok2vec", "tagger", "parser", "ner"]

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

    _install(monkeypatch, "spacy", load=lambda model: Nlp())
    _install(monkeypatch, "spacy.matcher", Matcher=Matcher)

    frame = BaseData({"text": ["python and sql", "python and sql", "excel"]}, cache_dir=tmp_path)
    lexicon = {"skills": ["python", "sql"]}

    result = frame.extract_entities_nlp("text", lexicon_source=lexicon, skills="skills")

    assert result["skills"].tolist() == [[], [], []]
    text_pipe = pipe_calls[-1]
    assert text_pipe[0] == ["python and sql", "excel"]
    assert text_pipe[1]["disable"] == ("parser", "ner")

    pipe_calls.clear()
    frame.extract_entities_nlp("text", lexicon_source=lexicon, skills="skills")
    assert pipe_calls == []


def test_extract_entities_nlp_custom_disable_reaches_both_pipe_calls(monkeypatch, tmp_path):
    pipe_calls = []
    _install_fake_spacy(monkeypatch, pipe_calls)
    frame = BaseData({"text": ["python"]}, cache_dir=tmp_path)

    _run_fake_nlp(frame, ("ner", "parser"))

    assert [call[1]["disable"] for call in pipe_calls] == [
        ("ner", "parser"),
        ("ner", "parser"),
    ]


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


@pytest.mark.parametrize("disable", ["tok2vec", "tagger", "attribute_ruler", "lemmatizer", "morphologizer"])
def test_extract_entities_nlp_rejects_required_disable_before_spacy_load(
    monkeypatch, tmp_path, disable
):
    load_calls = []
    _install_fake_spacy(monkeypatch, [], load_calls=load_calls)
    frame = BaseData({"text": ["python"]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match=disable):
        _run_fake_nlp(frame, disable)

    assert load_calls == []


def test_extract_entities_nlp_reports_all_required_disabled_components(monkeypatch, tmp_path):
    load_calls = []
    _install_fake_spacy(monkeypatch, [], load_calls=load_calls)
    frame = BaseData({"text": ["python"]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match="attribute_ruler.*lemmatizer"):
        _run_fake_nlp(frame, ("lemmatizer", "attribute_ruler"))

    assert load_calls == []


def test_extract_entities_nlp_warns_for_unknown_disable_and_continues(monkeypatch, tmp_path, caplog):
    pipe_calls = []
    _install_fake_spacy(monkeypatch, pipe_calls, pipe_names=["tok2vec", "tagger", "parser", "ner"])
    frame = BaseData({"text": ["python"]}, cache_dir=tmp_path)

    result = _run_fake_nlp(frame, ("parser", "sentencizer"))

    assert result["skills"].tolist() == [[]]
    assert len(pipe_calls) == 2
    warning = " ".join(record.getMessage() for record in caplog.records)
    assert "sentencizer" in warning
    assert "tok2vec" in warning
    assert "parser" not in warning.split("not present", 1)[0]


def test_extract_entities_nlp_different_disable_configs_do_not_reuse_cache(monkeypatch, tmp_path):
    pipe_calls = []
    _install_fake_spacy(monkeypatch, pipe_calls)
    frame = BaseData({"text": ["python"]}, cache_dir=tmp_path)

    _run_fake_nlp(frame, ("parser", "ner"))
    _run_fake_nlp(frame, ("parser",))

    assert len(pipe_calls) == 4


def test_extract_entities_nlp_different_models_do_not_reuse_cache(monkeypatch, tmp_path):
    pipe_calls = []
    load_calls = []
    _install_fake_spacy(monkeypatch, pipe_calls, load_calls=load_calls)
    frame = BaseData({"text": ["python"]}, cache_dir=tmp_path)

    _run_fake_nlp(frame, ("parser", "ner"), spacy_model="model_a")
    _run_fake_nlp(frame, ("parser", "ner"), spacy_model="model_b")

    assert len(pipe_calls) == 4
    assert load_calls == ["model_a", "model_b"]


def test_extract_entities_nlp_equivalent_disable_configs_reuse_cache(monkeypatch, tmp_path):
    pipe_calls = []
    _install_fake_spacy(monkeypatch, pipe_calls)
    frame = BaseData({"text": ["python"]}, cache_dir=tmp_path)

    _run_fake_nlp(frame, ("ner", " parser "))
    _run_fake_nlp(frame, ("parser", "ner"))

    assert len(pipe_calls) == 2


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
        nlp.extract_entities_nlp(
            frame,
            "text",
            lexicon_source=lexicon,
            cache_manager=frame.cache_manager,
            noisey_terms={"sql"},
            skills="skills",
        )


def test_extract_entities_nlp_raises_for_bad_configuration(monkeypatch, tmp_path):
    def load(model):
        raise OSError(f"Can't find model '{model}'")

    _install(monkeypatch, "spacy", load=load)
    _install(monkeypatch, "spacy.matcher", Matcher=object)
    frame = BaseData({"text": ["python"]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match="target column"):
        frame.extract_entities_nlp("text", lexicon_source={"skills": ["python"]})
    with pytest.raises(ValueError, match="No valid terms"):
        frame.extract_entities_nlp("text", lexicon_source={"other": ["x"]}, skills="skills")
    with pytest.raises(OSError, match="missing_model"):
        frame.extract_entities_nlp(
            "text", lexicon_source={"skills": ["python"]}, spacy_model="missing_model", skills="skills"
        )
