"""JSON and SQL write core extracted from the public io interface."""

import json
import logging
import os
from typing import Literal

import pandas as pd

from bynat._internal import dedupe_key as _dedupe_key

from ._internal import build_engine_url, import_optional

# Keep the public io module's logger name so log records do not change when
# the write core moves into this private module.
logger = logging.getLogger("bynat.cleaning.io")

__all__ = ['IfExists', 'JsonOrient', 'write_json', 'write_sql']

JsonOrient = Literal['split', 'records', 'index', 'columns', 'values', 'table']
IfExists = Literal['fail', 'replace', 'append']


def write_json(
    df: pd.DataFrame,
    file_path: str,
    orient: JsonOrient = 'records',
    append: bool = False,
    force_ascii: bool = False,
    indent: int = 4,
) -> None:
    """Write a dataframe payload to JSON, comparing or appending when needed."""
    export_df = df.copy()

    for col in export_df.select_dtypes(include = ['datetime', 'datetimetz']).columns:
        export_df[col] = export_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')

    is_append_successful = False
    new_rows_count = len(export_df)

    duplicates_removed = 0

    if os.path.exists(file_path):
        if append:
            try:
                existing_df = pd.read_json(file_path, orient = orient)

            except ValueError as e:
                # Overwriting here would silently destroy the existing file.
                raise ValueError(
                    f"Cannot append to '{file_path}': it is not readable as orient='{orient}' JSON."
                ) from e

            combined_df = pd.concat([existing_df, export_df], ignore_index = True)

            initial_count = len(combined_df)

            try:
                duplicate_mask = combined_df.duplicated()

            except TypeError:
                # Lists and dicts are unhashable, so compare object columns by a JSON key.
                dedupe_view = combined_df.copy(deep = False)

                for col in dedupe_view.select_dtypes(include = 'object').columns:
                    dedupe_view[col] = dedupe_view[col].map(_dedupe_key)

                duplicate_mask = dedupe_view.duplicated()

            combined_df = combined_df[~duplicate_mask].reset_index(drop = True)
            duplicates_removed = initial_count - len(combined_df)

            export_df = combined_df
            is_append_successful = True

        else:
            try:
                json_str = export_df.to_json(orient = orient, force_ascii = force_ascii)
                current_data = json.loads(json_str)

                with open(file_path, encoding = 'utf-8') as f:
                    existing_data = json.load(f)

                if current_data == existing_data:
                    logger.info("[SKIP] No changes detected. '%s' is already up to date.", os.path.basename(file_path))

                    return None

            except Exception as e:
                logger.warning("Could not read existing file for comparison (%s). Overwriting...", e)

    output_dir = os.path.dirname(file_path)

    if output_dir:
        os.makedirs(output_dir, exist_ok = True)

    export_df.to_json(file_path, orient = orient, force_ascii = force_ascii, indent = indent)

    if is_append_successful:
        logger.info("[APPEND] Added %s new rows. Removed %s duplicates. Total jobs: %s.", new_rows_count, duplicates_removed, len(export_df))

    else:
        logger.info("[OVERWRITE] Save completed successfully! Total rows: %s.", len(export_df))

    return None



def write_sql(
    df: pd.DataFrame,
    table_name: str,
    db_type: str,
    db_user: str,
    db_pass: str,
    db_host: str,
    db_port: str,
    db_name: str,
    db_driver: str | None,
    columns_types: dict | None,
    chunk_size: int | None,
    fast_executemany: bool,
    if_exists: IfExists,
    index: bool,
) -> None:
    """Write a dataframe to a SQL table through an optional SQLAlchemy engine."""
    engine_url, engine_kwargs = build_engine_url(
        db_type = db_type,
        db_user = db_user,
        db_pass = db_pass,
        db_host = db_host,
        db_port = db_port,
        db_name = db_name,
        db_driver = db_driver,
        fast_executemany = fast_executemany,
    )

    sqlalchemy = import_optional("sqlalchemy", "SQLAlchemy", "save_to_sql")

    export_df = df.copy()

    # Normalize timezone-aware datetimes for SQL drivers that do not accept timezone-aware pandas dtypes.
    for col in export_df.select_dtypes(include = ['datetimetz']).columns:
        export_df[col] = export_df[col].dt.tz_localize(None)

    engine = sqlalchemy.create_engine(engine_url, **engine_kwargs)

    try:
        logger.info("Pushing data to SQL table '%s' at %s...", table_name, db_host)

        export_df.to_sql(
            table_name,
            con = engine,
            if_exists = if_exists,
            index = index,
            dtype = columns_types,
            chunksize = chunk_size if chunk_size else None
        )

        logger.info("Database save completed successfully!")

    finally:
        engine.dispose()

    return None
