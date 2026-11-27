import types

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
