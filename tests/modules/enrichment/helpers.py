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


_install_langdetect = install_langdetect
