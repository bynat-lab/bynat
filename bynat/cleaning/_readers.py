"""File-reading core extracted from the public io interface."""

import json
from typing import Any

import pandas as pd

__all__ = ['load_json_payload', 'normalize_records', 'read_csv_records']


def load_json_payload(path: str) -> Any:
    """Load the raw JSON payload from an already validated path.

    Args:
        path (str): Path to a JSON file.

    Returns:
        Any: The decoded JSON value.
    """
    with open(path, encoding = "utf-8") as file:
        return json.load(file)


def normalize_records(raw_data: Any) -> pd.DataFrame:
    """Normalize a decoded JSON payload into a flat frame.

    Args:
        raw_data (Any): A decoded JSON value accepted by `pd.json_normalize`.

    Returns:
        pd.DataFrame: The flattened records.
    """
    return pd.json_normalize(raw_data)


def read_csv_records(path: str, **read_kwargs: Any) -> pd.DataFrame:
    """Read a CSV file into a dataframe with all cells as text.

    Args:
        path (str): Path to the CSV file.
        **read_kwargs: Forwarded to `pandas.read_csv`.

    Returns:
        pd.DataFrame: The parsed records.
    """
    return pd.read_csv(path, **read_kwargs)
