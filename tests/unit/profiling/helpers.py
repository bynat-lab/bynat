"""Test helpers and schema contracts for profile module tests."""

EXPECTED_STATS_KEYS_BY_KIND: dict[str, set[str]] = {
    "numeric": {
        "min",
        "max",
        "mean",
        "std",
        "median",
        "q25",
        "q75",
        "iqr",
        "zeros_count",
        "zeros_proportion",
        "outliers_count",
    },
    "categorical": {
        "top",
        "top_frequency",
        "top_proportion",
        "min_length",
        "max_length",
        "mean_length",
    },
    "boolean": {
        "true_count",
        "false_count",
        "true_proportion",
    },
    "datetime": {
        "min",
        "max",
        "range_days",
    },
    "other": {
        "top",
        "top_frequency",
        "top_proportion",
    },
}
