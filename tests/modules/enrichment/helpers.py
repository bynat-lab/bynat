import sys
import types

import pytest


def install_fake_module(monkeypatch, name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


class DictTranslator:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def translate(self, text, target_lang):
        self.calls.append((text, target_lang))
        return self.mapping.get(text)


class BatchTranslator(DictTranslator):
    def __init__(self, mapping):
        super().__init__(mapping)
        self.batches = []

    def translate(self, text, target_lang):
        pytest.fail("translate_batch should be preferred")

    def translate_batch(self, texts, target_lang):
        self.batches.append((list(texts), target_lang))
        return [self.mapping.get(text) for text in texts]


def install_langdetect(monkeypatch, detect):
    class DetectorFactory:
        seed = None

    return install_fake_module(
        monkeypatch, "langdetect", DetectorFactory=DetectorFactory, detect=detect
    )


class Location:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

    def __getitem__(self, index):
        return (self.latitude, self.longitude)[index]


class Geocoder:
    def __init__(self, known):
        self.known = known
        self.calls = []

    def geocode(self, query):
        self.calls.append(query)
        return self.known.get(query)


class RateSource:
    def __init__(self, rates, fail=()):
        self.rates = rates
        self.fail = set(fail)
        self.calls = []

    def yearly_rates(self, currency, start_year, end_year):
        self.calls.append((currency, start_year, end_year))
        if currency in self.fail:
            raise ConnectionError("offline")
        return {
            year: rate
            for (code, year), rate in self.rates.items()
            if code == currency and start_year <= year <= end_year
        }


def install_currency_lookup(monkeypatch):
    class Country:
        def __init__(self, alpha_2):
            self.alpha_2 = alpha_2

    def search_fuzzy(name):
        if name == "Atlantis":
            raise LookupError(name)
        return [Country({"Egypt": "EG", "United States": "US", "France": "FR"}[name])]

    install_fake_module(
        monkeypatch, "pycountry", countries=types.SimpleNamespace(search_fuzzy=search_fuzzy)
    )
    install_fake_module(monkeypatch, "babel")
    install_fake_module(
        monkeypatch,
        "babel.numbers",
        get_territory_currencies=lambda alpha_2: {"EG": ["EGP"], "US": ["USD"], "FR": ["EUR"]}[alpha_2],
    )


def install_spacy(monkeypatch):
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
            pass

        def add(self, name, patterns):
            pass

        def __call__(self, doc):
            return []

    install_fake_module(monkeypatch, "spacy", load=lambda model: Nlp())
    install_fake_module(monkeypatch, "spacy.matcher", Matcher=Matcher)


_install_langdetect = install_langdetect
