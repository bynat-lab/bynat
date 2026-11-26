"""SQLAlchemy connection-URL construction for the SQL export helper."""

import urllib.parse
from typing import Any

__all__ = ["build_engine_url"]


def build_engine_url(
    db_type: str,
    db_user: str,
    db_pass: str,
    db_host: str,
    db_port: str,
    db_name: str,
    db_driver: str | None,
    fast_executemany: bool,
) -> tuple[str, dict[str, Any]]:
    """
    Build the SQLAlchemy engine URL and engine keyword arguments.

    Handles three URL styles: SQLite (only `db_name` is required, and
    `":memory:"` targets an in-memory database), SQL Server (`mssql` or
    `sqlserver` dialects, which require every connection field plus
    `db_driver`), and the generic `dialect://user:password@host:port/name`
    form. Credentials and the ODBC driver are URL-encoded.

    Args:
        db_type (str): Lower-cased, stripped dialect/driver string.
        db_user (str): Stripped database username.
        db_pass (str): Stripped database password.
        db_host (str): Stripped database host address.
        db_port (str): Stripped database port.
        db_name (str): Stripped database name, or SQLite file path.
        db_driver (str | None): ODBC driver name, or None when not given.
        fast_executemany (bool): Whether to enable `fast_executemany`. Only
            used for SQL Server dialects.

    Returns:
        tuple[str, dict[str, Any]]: The engine URL and the keyword arguments
        for `sqlalchemy.create_engine`. The keyword arguments are empty
        except for SQL Server, which carries `fast_executemany`.

    Raises:
        ValueError: If a field required by the selected dialect is missing:
            `db_name` for SQLite, `db_driver` and all connection fields for
            SQL Server, or all connection fields for other dialects.
    """
    engine_kwargs: dict[str, Any] = {}

    if db_type.startswith('sqlite'):
        if not db_name:
            raise ValueError("database_name is required for SQLite.")

        if db_name == ':memory:':
            engine_url = "sqlite:///:memory:"

        else:
            engine_url = f"sqlite:///{db_name}"

    elif 'mssql' in db_type or 'sqlserver' in db_type:
        if not all([db_user, db_pass, db_host, db_port, db_name]):
            raise ValueError("SQL Server needs database_user, database_password, database_host, database_port, and database_name.")

        if not db_driver:
            raise ValueError("database_driver is required for SQL Server.")

        encoded_driver = urllib.parse.quote_plus(db_driver)
        encoded_user = urllib.parse.quote_plus(db_user)
        encoded_pass = urllib.parse.quote_plus(db_pass)

        engine_url = f"{db_type}://{encoded_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}?driver={encoded_driver}"
        engine_kwargs['fast_executemany'] = fast_executemany

    else:
        if not all([db_user, db_pass, db_host, db_port, db_name]):
            raise ValueError("database_user, database_password, database_host, database_port, and database_name are required.")

        encoded_user = urllib.parse.quote_plus(db_user)
        encoded_pass = urllib.parse.quote_plus(db_pass)

        engine_url = f"{db_type}://{encoded_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}"

    return engine_url, engine_kwargs
