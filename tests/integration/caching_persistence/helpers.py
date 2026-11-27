import sqlite3


def _seed_cache_entries(manager, func_name, rows):
    """Insert raw cache_entries rows for ``func_name`` and return the manager."""
    manager._storage.initialize()
    created_at = "2026-01-01T00:00:00+00:00"
    with sqlite3.connect(manager._storage.get_database_path()) as connection:
        connection.executemany(
            "INSERT INTO cache_entries VALUES (?, ?, ?, ?, ?)",
            [(func_name, bucket, key, value_json, created_at)
             for bucket, key, value_json in rows],
        )
        connection.commit()


def _rows(manager):
    """Return ``(bucket, key, value_json)`` rows for the shared cache database."""
    with sqlite3.connect(manager._storage.get_database_path()) as connection:
        return connection.execute(
            "SELECT bucket, key, value_json FROM cache_entries ORDER BY bucket, key"
        ).fetchall()


def _migrate_legacy_cache(manager, func_name):
    """Invoke the canonical module-level migration with the manager's storage."""
    from bynat.caching._internal import legacy_json_path
    from bynat.caching._migration import migrate_legacy_json_cache

    return migrate_legacy_json_cache(
        manager.cache_dir_path,
        func_name,
        legacy_json_path(manager.cache_dir_path, func_name),
        manager._storage,
        initialize_fn=manager._storage.initialize,
        connect_fn=manager._storage.connect,
    )
