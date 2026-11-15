import sqlite3


def _seed_cache_entries(manager, func_name, rows):
    """Insert raw cache_entries rows for ``func_name`` and return the manager."""
    manager._initialize_sqlite()
    created_at = "2026-01-01T00:00:00+00:00"
    with sqlite3.connect(manager._get_database_path()) as connection:
        connection.executemany(
            "INSERT INTO cache_entries VALUES (?, ?, ?, ?, ?)",
            [(func_name, bucket, key, value_json, created_at)
             for bucket, key, value_json in rows],
        )
        connection.commit()


def _rows(manager):
    """Return ``(bucket, key, value_json)`` rows for the shared cache database."""
    with sqlite3.connect(manager._get_database_path()) as connection:
        return connection.execute(
            "SELECT bucket, key, value_json FROM cache_entries ORDER BY bucket, key"
        ).fetchall()
