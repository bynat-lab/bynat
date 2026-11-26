"""File-reading core extracted from the public io interface."""

import json
from typing import Any

import pandas as pd

__all__ = ['load_json_payload', 'normalize_records', 'read_csv_records']


def load_json_payload(path: str) -> Any:
    """Load the raw JSON payload from an already validated path."""
    with open(path, encoding = "utf-8") as file:
        return json.load(file)


def normalize_records(raw_data: Any) -> pd.DataFrame:
    """Normalize a decoded JSON payload into a flat frame."""
    return pd.json_normalize(raw_data)


def read_csv_records(path: str, **read_kwargs: Any) -> pd.DataFrame:
    """Parse an already validated CSV path with pandas."""
    return pd.read_csv(path, **read_kwargs)
