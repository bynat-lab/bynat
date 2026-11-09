"""Cross-domain test constants used across multiple testing domains."""

from typing import Any

OUTPUT_COLUMNS: list[str] = [
    "hierarchy_level",
    "hierarchy_columns",
    "group_key",
    "target_column",
    "strategy",
    "statistic",
]

HIERARCHICAL_STATS_OUTPUT_COLUMNS = OUTPUT_COLUMNS

PARITY_DATA: dict[str, list[Any]] = {
    "user.name": ["Ada", "Grace"],
    "user_id": [1, 2],
    "value": [10.0, 20.0],
    "C": [1, 2],
    "A": [3, 4],
    "D": [5, 6],
    "B": [7, 8],
    "longitude": [31.0, 32.0],
    "latitude": [30.0, 29.0],
    "id": [1, 2],
    "items": [["a", "b"], ["c", "d"]],
    "description": ["Blue shoes", "red shirt"],
    "title": ["Software Engineer - Remote", "Data Analyst"],
    "g": ["x", "x"],
    "score": [1.0, None],
}
