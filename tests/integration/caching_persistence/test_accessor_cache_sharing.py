import pandas as pd

from bynat.caching import CacheManager
from bynat.cleaning import BaseData


class _Translator:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def translate(self, text, target_lang):
        self.calls.append((text, target_lang))
        return self.mapping[text]


def _frame(tmp_path, data=None):
    return BaseData(
        data if data is not None else {"id": [1, 2], "latitude": [1.0, 2.0], "name": ["a", "b"]},
        cache_dir=tmp_path,
    )


def test_accessor_uses_one_shared_cache_manager_per_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("BYNAT_CACHE_DIR", str(tmp_path / "default"))
    frame = pd.DataFrame({"status": ["a"]})

    first = frame.bynat.cache_manager
    second = frame.copy().bynat.cache_manager
    explicit = frame.bynat.with_cache(tmp_path / "explicit").cache_manager

    assert first is second
    assert explicit is not first
    assert explicit is frame.bynat.with_cache(tmp_path / "explicit").cache_manager
    assert explicit.cache_dir_path == str(tmp_path / "explicit")

    manager = CacheManager(tmp_path / "manual")
    assert frame.bynat.with_cache(manager).cache_manager is manager


def test_accessor_cached_methods_use_the_selected_cache(tmp_path):
    translator = _Translator({"مكتمل": "Completed"})
    frame = pd.DataFrame({"status": ["مكتمل", "مكتمل"]})
    original = frame.copy(deep=True)

    result = frame.bynat.with_cache(tmp_path).translate_categorical_column("status", provider=translator)
    again = frame.bynat.with_cache(tmp_path).translate_categorical_column("status", provider=translator)

    assert result["status"].tolist() == ["Completed", "Completed"]
    assert again["status"].tolist() == ["Completed", "Completed"]
    assert translator.calls == [("مكتمل", "en")]
    pd.testing.assert_frame_equal(frame, original)

    frame.bynat.with_cache(tmp_path).clear_cache_for_column("translate_categorical_column", "status")
    frame.bynat.with_cache(tmp_path).translate_categorical_column("status", provider=translator)
    assert len(translator.calls) == 2
    pd.testing.assert_frame_equal(frame, original)


def test_pandas_operations_share_the_legacy_cache_manager(monkeypatch, tmp_path):
    frame = BaseData({"g": ["a", "b"], "v": [1, 2]}, cache_dir=tmp_path)

    manager = frame.cache_manager
    built = []
    original_init = CacheManager.__init__

    def counting_init(self, *args, **kwargs):
        built.append(args)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(CacheManager, "__init__", counting_init)

    derived = [
        frame.copy(), frame[frame["v"] > 1], frame.rename_all_DOTS(),
        frame.sort_values("v"), frame.groupby("g").sum(),
    ]

    assert built == []
    assert all(item.cache_manager is manager for item in derived)
    assert isinstance(derived[1], BaseData)


def test_melt_transform_pivot_result_keeps_the_cache_manager(tmp_path):
    frame = _frame(tmp_path, {"id": [1, 2], "left": ["a", "b"], "right": ["c", "d"]})
    original = frame.copy(deep=True)

    result = frame.melt_transform_pivot(id_vars="id", transform_func=lambda values: values.str.upper())

    assert isinstance(result, BaseData)
    assert result.cache_manager is frame.cache_manager
    pd.testing.assert_frame_equal(frame, original)


def test_public_cleaning_imports_use_the_bundled_cache_manager(tmp_path):
    frame = BaseData({"value": [1]}, cache_dir=tmp_path)

    assert isinstance(frame.cache_manager, CacheManager)
    assert BaseData.__module__ == "bynat.cleaning.base"
