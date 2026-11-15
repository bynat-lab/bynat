import sqlite3

import pytest

from bynat.caching import CacheManager

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("content", ["{not json", "[1, 2]"])
def test_legacy_migration_quarantines_corrupt_source_without_marker(tmp_path, content, caplog):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    source = cache_dir / "broken_cache.json"
    source.write_text(content, encoding="utf-8")

    CacheManager(cache_dir)._migrate_legacy_json_cache("broken")

    assert not source.exists()
    assert len(list(cache_dir.glob("broken_cache.json.corrupt.*"))) == 1
    assert "marker" not in caplog.text.lower()
    assert not (cache_dir / "cache.sqlite3").exists()


def test_legacy_migration_preserves_unsupported_source_for_retry(tmp_path, caplog):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    source = cache_dir / "translate_cache.json"
    source.write_text('{"status": ["bad"]}', encoding="utf-8")
    manager = CacheManager(cache_dir)

    manager._migrate_legacy_json_cache("translate")
    assert source.exists()
    assert "unsupported" in caplog.text
    assert not (cache_dir / "cache.sqlite3").exists()

    source.write_text('{"status": {"ok": null}}', encoding="utf-8")
    manager._migrate_legacy_json_cache("translate")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM cache_entries").fetchone() == (1,)


def test_quarantine_corrupt_cache_file_fallbacks(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    source_file = cache_dir / "translate_cache.json"
    source_file.write_text("corrupted content", encoding="utf-8")
    manager = CacheManager(cache_dir)

    monkeypatch.setattr("os.open", lambda *a, **k: (_ for _ in ()).throw(FileExistsError()))
    assert manager._quarantine_corrupt_cache_file(str(source_file)) is None

    monkeypatch.undo()
    monkeypatch.setattr("os.replace", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    assert manager._quarantine_corrupt_cache_file(str(source_file)) is None

    monkeypatch.undo()
    monkeypatch.setattr("os.replace", lambda *a, **k: (_ for _ in ()).throw(OSError("disk error")))
    assert manager._quarantine_corrupt_cache_file(str(source_file)) is None


def test_legacy_migration_quarantine_and_read_errors(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    source_file = cache_dir / "translate_cache.json"
    source_file.write_text("invalid json {", encoding="utf-8")
    manager = CacheManager(cache_dir)

    monkeypatch.setattr(manager, "_quarantine_corrupt_cache_file", lambda f: (_ for _ in ()).throw(OSError("perm error")))
    manager._migrate_legacy_json_cache("translate")

    monkeypatch.undo()
    source_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("builtins.open", lambda *a, **k: (_ for _ in ()).throw(OSError("cannot read")))
    manager._migrate_legacy_json_cache("translate")

    monkeypatch.undo()
    source_file.write_text("[1, 2, 3]", encoding="utf-8")
    monkeypatch.setattr(manager, "_quarantine_corrupt_cache_file", lambda f: (_ for _ in ()).throw(OSError("perm error")))
    manager._migrate_legacy_json_cache("translate")
