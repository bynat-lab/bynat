import sys
import types

import pytest


@pytest.fixture
def fake_langdetect(monkeypatch):
    module = types.ModuleType("langdetect")

    class DetectorFactory:
        seed = None

    module.DetectorFactory = DetectorFactory
    module.LangDetectException = Exception
    module.detect = lambda text: "en"
    monkeypatch.setitem(sys.modules, "langdetect", module)
    return module
