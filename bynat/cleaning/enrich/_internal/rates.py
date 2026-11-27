"""Exchange-rate lookback helper for the currency conversion."""

__all__ = ["lookback_years"]


def lookback_years(year: int, min_year: int) -> range:
    """Years checked for a rate, from `year` back to `min_year`.

    Args:
        year (int): Starting year.
        min_year (int): Earliest year to include.

    Returns:
        range: Years in descending order, including both endpoints.
    """
    return range(year, min_year - 1, -1)
