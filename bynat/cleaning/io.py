"""JSON and SQL export helpers, and the JSON/CSV loaders."""

import logging
import os
from typing import Any

import pandas as pd

from ._readers import load_json_payload, normalize_records, read_csv_records
from ._writers import IfExists, JsonOrient, write_json, write_sql

__all__ = [
    "IfExists",
    "JsonOrient",
    "read_csv",
    "read_json",
    "save_to_json",
    "save_to_sql",
]

logger = logging.getLogger(__name__)


def read_json(
    json_file_path: str | os.PathLike,
    key: str | None = None,
) -> pd.DataFrame:
    """
    Read a JSON file into a plain `pandas.DataFrame`.

    The payload is flattened with `pandas.json_normalize`, as `JsonFile`
    does. Use the `df.bynat` accessor on the result for bynat methods.

    Args:
        json_file_path (str | os.PathLike): Path to the JSON file.
        key (str | None): Optional top-level key whose value holds the
            records, for dictionary payloads. Defaults to None.

    Returns:
        pandas.DataFrame: The normalized records.

    Raises:
        FileNotFoundError: If the file does not exist.
        TypeError: If `key` is given for a non-dictionary payload.
        KeyError: If `key` is not in the payload.

    Example:
    ```
        from bynat.cleaning.io import read_json

        jobs = read_json("jobs.json", key="items")
        jobs = jobs.bynat.rename_all_DOTS()
    ```
    """
    path = os.fspath(json_file_path)

    if not os.path.isfile(path):
        raise FileNotFoundError(f"JSON file not found: {path}")

    raw_data = load_json_payload(path)

    if key:
        if not isinstance(raw_data, dict):
            raise TypeError("A JSON key can only be selected from a dictionary payload.")

        if key not in raw_data:
            raise KeyError(f"Key '{key}' was not found in JSON payload.")

        raw_data = raw_data[key]

    return normalize_records(raw_data)


def read_csv(csv_file_path: str | os.PathLike, **read_kwargs: Any) -> pd.DataFrame:
    """
    Read a CSV file into a plain `pandas.DataFrame`.

    Args:
        csv_file_path (str | os.PathLike): Path to the CSV file.
        **read_kwargs: Keyword arguments forwarded to `pandas.read_csv`,
            replacing `CsvFile(read_kwargs=...)`.

    Returns:
        pandas.DataFrame: The parsed file.

    Raises:
        FileNotFoundError: If the file does not exist.

    Example:
    ```
        from bynat.cleaning.io import read_csv

        people = read_csv("people.csv", sep=";")
    ```
    """
    path = os.fspath(csv_file_path)

    if not os.path.isfile(path):
        raise FileNotFoundError(f"CSV file not found: {path}")

    return read_csv_records(path, **read_kwargs)


def save_to_json(
    df: pd.DataFrame,
    file_path: str | os.PathLike,
    orient: JsonOrient = 'records',
    append: bool = False,
    force_ascii: bool = False,
    indent: int = 4
) -> None:
    """
    Save the dataframe to a JSON file only when content has changed.

    Notes:
        Before writing, the method compares the current dataframe payload to
        the existing file contents when possible. This avoids unnecessary
        rewrites and keeps the output directory stable across unchanged runs.
        Datetime columns are serialized as `%Y-%m-%d %H:%M:%S` strings to
        keep the JSON output human-readable and stable across environments.
        Paths without a directory component, such as `output.json`, are
        written to the current working directory.

        The input `df` is never modified; datetime values are reformatted on
        an internal copy. An existing file that cannot be read for comparison
        is overwritten, except with `append=True`, where an unreadable file
        raises instead of being destroyed. Missing parent directories are
        created.

    Args:
        file_path (str | os.PathLike): Destination JSON file path.
        orient (str): JSON orientation passed to `pandas.DataFrame.to_json`.
            Defaults to `"records"`.
        append (bool): If True and the target file exists, appends current
            rows to the existing JSON data and removes duplicate rows before
            writing. Duplicate detection compares list and dictionary cell
            values by their JSON content. Defaults to False.
        force_ascii (bool): Whether to escape non-ASCII characters in the
            output. Defaults to False.
        indent (int): Indentation width used when writing to disk. Defaults
            to 4.

    Returns:
        None. Nothing is written when an existing non-append file already
        holds identical content.

    Raises:
        ValueError: If `file_path` is empty, or if `append=True` and the
            existing file cannot be read with the given `orient`.
    """
    file_path = os.fspath(file_path).strip() if file_path is not None else ""

    if not file_path:
        raise ValueError("file_path cannot be empty.")

    write_json(
        df,
        file_path,
        orient = orient,
        append = append,
        force_ascii = force_ascii,
        indent = indent,
    )

def save_to_sql(
    df: pd.DataFrame,
    table_name: str,
    database_type: str,
    database_user: str,
    database_password: str,
    database_host: str,
    database_port: str,
    database_name: str,
    database_driver: str | None = None,
    columns_types: dict | None = None,
    chunk_size: int | None = None,
    fast_executemany: bool = False,
    if_exists: IfExists = 'append',
    index: bool = False
) -> None:
    """
    Save the dataframe to a SQL database table using SQLAlchemy.

    Notes:
        The method supports standard SQLAlchemy URL styles and includes
        dedicated handling for SQL Server drivers and SQLite paths. For
        SQL Server, `database_driver` is required and is URL-encoded.
        For SQLite, only `database_name` is required.

        Credentials are URL-encoded before being placed in the connection
        URL. Timezone-aware datetime columns are converted to naive datetimes
        on an internal copy, so the input `df` is never modified. The engine
        is disposed of after the write, whether it succeeds or fails.

    Args:
        table_name (str): The name of the SQL table to write to.
        database_type (str): SQLAlchemy dialect/driver, for example
            `"postgresql+psycopg2"`, `"mysql+pymysql"`, `"mssql+pyodbc"`,
            or `"sqlite"`.
        database_user (str): Database username.
        database_password (str): Database password.
        database_host (str): Database host address.
        database_port (str): Database port.
        database_name (str): Database/schema name, or SQLite file path. The
            special value `":memory:"` targets an in-memory SQLite database.
        database_driver (str | None): ODBC driver name for SQL Server
            dialects. Defaults to None.
        columns_types (dict | None): Optional SQLAlchemy dtype mapping to
            control target SQL column types. Defaults to None.
        chunk_size (int | None): Optional number of rows per write chunk.
            Defaults to None (single batch).
        fast_executemany (bool): Enables `fast_executemany` for SQL Server
            pyodbc connections when supported. Defaults to False.
        if_exists (str): How to behave if the table already exists.
            Options: 'fail', 'replace', 'append'. Defaults to 'append'.
        index (bool): Whether to write the DataFrame index as a SQL column.
            Defaults to False.

    Returns:
        None

    Raises:
        ValueError: If `table_name` or `database_type` is empty, if
            `if_exists` is not one of 'fail', 'replace', or 'append', or if
            the credentials required by the selected dialect are missing
            (`database_name` for SQLite, `database_driver` and all
            connection fields for SQL Server).
        ImportError: If the optional `SQLAlchemy` dependency is not
            installed.

    Example:
    ```
        df.save_to_sql(
            table_name="cleaned_search_data",
            database_type="postgresql+psycopg2",
            database_user="postgres",
            database_password="secret",
            database_host="localhost",
            database_port="5432",
            database_name="analytics_db",
            if_exists="replace",
            index=False
        )
    ```
    """

    db_type = str(database_type or '').strip().lower()
    db_user = str(database_user or '').strip()
    db_pass = str(database_password or '').strip()
    db_host = str(database_host or '').strip()
    db_port = str(database_port or '').strip()
    db_name = str(database_name or '').strip()
    db_driver = str(database_driver or '').strip() or None
    table_name = str(table_name or '').strip()

    if not table_name:
        raise ValueError("table_name cannot be empty.")

    if if_exists not in ['fail', 'replace', 'append']:
        raise ValueError(f"Invalid if_exists value '{if_exists}'. Use 'fail', 'replace', or 'append'.")

    if not db_type:
        raise ValueError("database_type cannot be empty.")

    write_sql(
        df,
        table_name,
        db_type,
        db_user,
        db_pass,
        db_host,
        db_port,
        db_name,
        db_driver,
        columns_types,
        chunk_size,
        fast_executemany,
        if_exists,
        index,
    )
