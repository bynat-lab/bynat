import types

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
    "disable",
    [
        pytest.param("tok2vec", id="tok2vec"),
        pytest.param("tagger", id="tagger"),
        pytest.param("attribute_ruler", id="attribute-ruler"),
        pytest.param("lemmatizer", id="lemmatizer"),
        pytest.param("morphologizer", id="morphologizer"),
    ],
)
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
