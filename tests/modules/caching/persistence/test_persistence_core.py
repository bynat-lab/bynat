import pytest

from bynat.caching import CacheManager

pytestmark = pytest.mark.integration


def test_cache_round_trip_via_sqlite(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    bucket = manager.get_column_cache("translate", "status")
    bucket["pending"] = "Pending"
    manager.save_function_cache("translate")

    reloaded = CacheManager(tmp_path / "cache")
    assert reloaded.load_function_cache("translate") == {
        "status": {"pending": "Pending"},
    }
    assert not (tmp_path / "cache" / "translate_cache.json").exists()
    assert (tmp_path / "cache" / "cache.sqlite3").exists()


def test_cache_rejects_empty_and_path_like_keys(tmp_path):
    manager = CacheManager(tmp_path)

    with pytest.raises(ValueError):
        manager.load_function_cache("   ")
    with pytest.raises(ValueError):
        manager.load_function_cache("nested/cache")
    with pytest.raises(TypeError):
        manager.get_column_cache("function", 123)


def test_cache_directory_is_created_on_save_not_construction(tmp_path):
    cache_dir = tmp_path / "not-yet-created"
    CacheManager(cache_dir)
    assert not cache_dir.exists()

    manager = CacheManager(cache_dir)
    manager.caches["function"] = {"column": {"key": "value"}}
    manager.save_function_cache("function")
    assert (cache_dir / "cache.sqlite3").exists()


def test_cache_dir_defaults_to_environment_variable_then_legacy_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BYNAT_CACHE_DIR", raising=False)
    assert CacheManager().cache_dir_path == str(tmp_path / "Settings" / "Cache Data" / "Automated")

    monkeypatch.setenv("BYNAT_CACHE_DIR", str(tmp_path / "from-env"))
    assert CacheManager().cache_dir_path == str(tmp_path / "from-env")
    assert CacheManager(tmp_path / "explicit").cache_dir_path == str(tmp_path / "explicit")


def test_get_column_cache_returns_existing_bucket_identity(tmp_path):
    manager = CacheManager(tmp_path / "cache")
    func_cache = manager.load_function_cache("translate")

    first = manager.get_column_cache("translate", "status")
    first["pending"] = "Pending"

    second = manager.get_column_cache("translate", "status")
    assert second is first
    assert func_cache["status"] is second


def test_get_column_cache_creates_missing_bucket(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    bucket = manager.get_column_cache("translate", "status")
    assert bucket == {}
    assert isinstance(bucket, dict)

    bucket["pending"] = "Pending"
    assert manager.load_function_cache("translate") == {"status": {"pending": "Pending"}}

    other = manager.get_column_cache("translate", "coordinates")
    assert other == {}
    assert other is not bucket


def test_get_column_cache_preserves_explicit_none_value(tmp_path):
    manager = CacheManager(tmp_path / "cache")
    bucket = manager.get_column_cache("translate", "status")

    bucket["missing"] = None

    assert "missing" in bucket
    assert bucket["missing"] is None
    assert dict(bucket) == {"missing": None}
    assert list(bucket) == ["missing"]
    bucket["pending"] = "Pending"
    assert sorted(bucket) == ["missing", "pending"]

    assert manager.get_column_cache("translate", "status") == {"missing": None, "pending": "Pending"}


def test_get_column_cache_missing_function_creates_empty_bucket(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    bucket = manager.get_column_cache("ghost", "status")
    assert bucket == {}

    bucket["pending"] = "Pending"
    assert manager.get_column_cache("ghost", "status") is bucket
    assert manager.load_function_cache("ghost") == {"status": {"pending": "Pending"}}


def test_cache_manager_constructor_validation_rejects_non_string_and_empty():
    with pytest.raises(TypeError, match="cache_dir must be a string or path-like object"):
        CacheManager(12345)

    with pytest.raises(ValueError, match="cache_dir cannot be empty"):
        CacheManager("   ")
