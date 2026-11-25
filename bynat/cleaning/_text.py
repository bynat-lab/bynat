"""Keyword extraction, truncation, and categorization helpers."""

import re
from typing import Any

import numpy as np
import pandas as pd

from ._internal import (
    FrameT,
    apply_removal_patterns,
    first_literal_matches,
    first_regex_matches,
    import_optional,
)

__all__ = [
    "categorize_by_reference",
    "extract_keywords",
    "truncate_after_substring",
]


def extract_keywords(
    df: FrameT,
    *source_cols: Any,
    remove_extracted: bool = False,
    use_regex: bool = False,
    **target_cols_and_keywords: Any
) -> FrameT:
    """
    Search for keywords or regular expressions across source columns and extract them into new target columns.
    Matches are case-insensitive and are formatted to Title Case in the target column.

    Notes:
        - **Keyword Priority**: Keywords are extracted based on list order. The first item in the list has the highest precedence.
        - **Non-Destructive Updates**: If this method is called multiple times targeting the exact same output column.
            Subsequent calls will only populate empty cells (NaNs) and will NEVER overwrite previously extracted values.
        - **Literal Matching**: Keywords are treated as literal text (e.g., `C++`, `.NET`),
          and will not be interpreted as regular expressions unless `use_regex` is set to True.
        - **Title-Casing**: The extracted value is the matched keyword rendered in
          Title Case. Under `use_regex=True` the first capture group of the match
          is used instead; a pattern with no capture group is wrapped so the whole
          pattern is captured, and a pattern with a group yields that group only.
        - **Text Coercion**: Source columns are converted to strings only
          for matching, so numeric/object columns do not break text search.
        - **Performance**: Each unique combined text is matched once and the
          results are mapped back to every row. Literal keywords are matched
          with one combined pattern (or an Aho-Corasick automaton when the
          optional `pyahocorasick` dependency is installed).
        - **Optional Dependency**: Literal matching uses `pyahocorasick` when
          it is installed and every keyword is ASCII; otherwise it falls back to
          one combined regular expression. Both paths return the same result and
          neither raises when the dependency is missing.
        - Source columns that are absent from `df` are ignored. When none of
          them are present, an unchanged copy of `df` is returned.
        - The standalone function never modifies `df`.

    Args:
        *source_cols: Variable number of column names to search within. Column
            names that do not exist in `df` are ignored.
        remove_extracted (bool): If True, removes the matched keywords from the
            original source columns to clean the text. Defaults to False.
        use_regex (bool): If True, treats the input strings in **target_cols_and_keywords
            as regular expressions for pattern extraction. Defaults to False.
        **target_cols_and_keywords: Keyword arguments where the key is the new
            column name and the value is a list of strings to search for. A
            single string is treated as a one-item list.
        inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
            standalone function has no such parameter and always returns a new
            frame. When True, the receiver is mutated in place. Defaults to
            False.

    Returns:
        With `inplace=False` (default), a new dataframe with the extracted columns; the
        input is not modified. With `inplace=True`, the receiver is mutated in place and
        None is returned.

    Example:
    ```
        Initial Column:
            'description': ["Blue Suede Shoes", "Red Cotton Shirt"]

        Operation:
            extract_keywords('description', colors=['blue', 'red'], remove_extracted=True)

        Result:
            'description': ["Suede Shoes", "Cotton Shirt"]
            'colors':      ["Blue", "Red"]

        Usage:
            df.extract_keywords("comments", "tags", categories=["urgent", "review"])
    ```
    """

    sources = list(source_cols)
    valid_sources = [col for col in sources if col in df.columns]

    if not valid_sources:
        return df.copy()

    source_text = df[valid_sources].fillna('').astype(str)
    combined_text = source_text.iloc[:, 0]

    for position in range(1, source_text.shape[1]):
        combined_text = combined_text + ' ' + source_text.iloc[:, position]

    codes, unique_texts = pd.factorize(combined_text)

    result = df.copy()

    for new_col_name, keywords_list in target_cols_and_keywords.items():
        if isinstance(keywords_list, (str, bytes)) or not hasattr(keywords_list, '__iter__'):
            keywords_list = [keywords_list]

        cleaned_keywords = [
            str(word).strip()
            for word in keywords_list
            if word is not None and str(word).strip()
        ]

        if not cleaned_keywords:
            continue

        extracted = pd.Series(index = combined_text.index, dtype = str)

        if use_regex:
            extract_patterns = []

            for word in cleaned_keywords:
                compiled = re.compile(word)

                if compiled.groups == 0:
                    compiled = re.compile(rf"({word})")

                extract_patterns.append(compiled)

            per_text: np.ndarray = first_regex_matches(unique_texts, extract_patterns).to_numpy()

        else:
            titles = [word.title() for word in cleaned_keywords]
            per_text = np.array(
                [
                    np.nan if priority is None else titles[priority]
                    for priority in first_literal_matches(unique_texts, cleaned_keywords)
                ],
                dtype = object,
            )

        if len(per_text):
            row_values = per_text[codes]
            mask = pd.notna(row_values)

            if mask.any():
                extracted.loc[mask] = row_values[mask]

        if new_col_name in result.columns:
            result[new_col_name] = result[new_col_name].astype('object')
            result[new_col_name] = result[new_col_name].where(result[new_col_name].notna(), extracted)

        else:
            result[new_col_name] = extracted

        mask_extracted = result[new_col_name].notna()
        result.loc[mask_extracted, new_col_name] = result.loc[mask_extracted, new_col_name].astype(str).str.title()

        if remove_extracted:
            if use_regex:
                remove_patterns = [re.compile(pattern) for pattern in cleaned_keywords]

            else:
                escaped_keywords = [re.escape(word) for word in cleaned_keywords]
                remove_patterns = [
                    re.compile(rf"(?<!\w)({'|'.join(escaped_keywords)})(?!\w)", re.IGNORECASE)
                ]

            for col in valid_sources:
                mask = result[col].notna()

                result.loc[mask, col] = apply_removal_patterns(result.loc[mask, col], remove_patterns)

    return result


def truncate_after_substring(df: FrameT, regex: bool = True, **target_cols_and_substrings: Any) -> FrameT:
    """
    Remove specific substrings and everything following them from target columns.

    Each named column is processed independently. The first occurrence of each
    substring cuts the text, and the remaining text is stripped of surrounding
    whitespace. Column names that are absent from `df` are ignored, and with no
    keyword arguments an unchanged copy of `df` is returned.

    Args:
        regex (bool): Passed to `pandas.Series.str.split`. When True,
            substring values are interpreted as regular expressions.
            Defaults to True.
        **target_cols_and_substrings: Keyword arguments where the key is the column
            name and the value is a string or a list of strings at which to cut off the text.
        inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
            standalone function has no such parameter and always returns a new
            frame. When True, the receiver is mutated in place. Defaults to
            False.

    Returns:
        With `inplace=False` (default), a new dataframe with truncated columns; the
        input is not modified. With `inplace=True`, the receiver is mutated in place and
        None is returned.

    Example:
    ```
        Initial Data:
            'title': ['Software Engineer - Remote', 'Data Analyst (Junior)']
            'company': ['Tech Corp, LLC', 'Data Inc.']

        Operation:
            df.truncate_after_substring(
                title=['-', '('],
                company=','
            )

        Result:
            'title': ['Software Engineer', 'Data Analyst']
            'company': ['Tech Corp', 'Data Inc']
    ```
    """

    if not target_cols_and_substrings:
        return df.copy()

    result = df.copy()

    for col, substrings in target_cols_and_substrings.items():
        if col not in result.columns:
            continue

        if not isinstance(substrings, list):
            substrings = [substrings]

        if result[col].notna().any():
            result[col] = result[col].astype('object')

        for sub in substrings:
            mask = result[col].notna()
            result.loc[mask, col] = result.loc[mask, col].astype(str).str.split(sub, n = 1, regex = regex).str[0].str.strip()

    return result


def categorize_by_reference(
    df: FrameT,
    *source_cols: str,
    target_col: str,
    reference: dict,
    default_category: str = 'Other'
) -> FrameT:
    """
    Categorize text data into broader groups based on a reference lexicon dictionary.

    This method scans one or more source text columns for specific keywords defined in a
    lexicon dictionary. If a match is found, the dictionary's key (the category)
    is assigned to a new target column.

    Notes:
        - Matching is case-insensitive and restricted to whole words, so
          'React' does not trigger on 'Reactor' and 'score' does not trigger
          on 'under_score'.
        - The implementation builds an Aho-Corasick automaton and evaluates
          each unique combined text once, then maps results back to all rows.
        - Longer keywords take precedence over shorter ones (e.g., "Data Analyst"
          matches before "Data"). On an equal-length tie the category listed
          later in `reference` wins.
        - Empty keyword lists and blank keyword values are ignored safely.
        - A keyword value that is not a list is treated as a one-item list.
        - A missing `reference` column match, an empty `reference`, or a
          `reference` that is not a dictionary assigns `default_category` to
          every row.
        - Source columns that are absent from `df` are ignored. When none of
          them are present, an unchanged copy of `df` is returned.
        - The standalone function never modifies `df`.

    Args:
        *source_cols (str): Source columns containing the raw text to search.
            Names that do not exist in `df` are ignored.
        target_col (str): The new or existing column where categories will be saved.
        reference (dict): A dictionary where keys are category names and values
            are lists of keywords to search for. A non-list value is treated as
            a one-item list, and a non-dictionary value is treated as empty.
        default_category (str): The fallback value if no keywords are matched.
            Defaults to 'Other'.
        inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
            standalone function has no such parameter and always returns a new
            frame. When True, the receiver is mutated in place. Defaults to
            False.

    Returns:
        With `inplace=False` (default), a new dataframe with the category column; the
        input is not modified. With `inplace=True`, the receiver is mutated in place and
        None is returned.

    Raises:
        ImportError: If the optional `pyahocorasick` dependency is not
            installed. The dependency is required for this method; there is no
            regex fallback.

    Example:
    ```
        reference = {
            "Data": ["data analyst", "business intelligence"],
            "Software": ["python developer", "backend engineer"]
        }

        jobs.categorize_by_reference(
            "title",
            "description",
            target_col = "field_label",
            reference = reference
        )
    ```
    """
    sources = list(source_cols)
    valid_sources = [col for col in sources if col in df.columns]

    if not valid_sources:
        return df.copy()

    result = df.copy()

    combined_series = result[valid_sources[0]].fillna('').astype(str)

    if len(valid_sources) > 1:
        for col in valid_sources[1:]:
            combined_series += " " + result[col].fillna('').astype(str)

    if not isinstance(reference, dict) or not reference:
        result[target_col] = default_category

        return result

    ahocorasick = import_optional(
        "ahocorasick", "pyahocorasick", "categorize_by_reference"
    )
    automaton = ahocorasick.Automaton()

    category_priority = {cat: idx for idx, cat in enumerate(reversed(list(reference.keys())))}
    valid_keyword_found = False

    for category, keywords in reference.items():
        if not isinstance(keywords, list):
            keywords = [keywords]

        for kw in keywords:
            if kw is not None and str(kw).strip():
                clean_kw = str(kw).strip().lower()

                automaton.add_word(clean_kw, (len(clean_kw), category_priority[category], category))
                valid_keyword_found = True

    if not valid_keyword_found:
        result[target_col] = default_category

        return result

    automaton.make_automaton()

    unique_texts = combined_series.unique()
    mapping_dict = {}

    for text in unique_texts:
        if not text:
            mapping_dict[text] = default_category
            continue

        text_lower = text.lower()
        text_len = len(text_lower)

        best_match = None
        best_len = -1
        best_priority = float('inf')

        for end_index, (kw_len, priority, category) in automaton.iter(text_lower):
            start_index = end_index - kw_len + 1

            if start_index > 0 and text_lower[start_index - 1].isalnum():
                continue

            if end_index + 1 < text_len and text_lower[end_index + 1].isalnum():
                continue

            if kw_len > best_len or (kw_len == best_len and priority < best_priority):
                best_match = category
                best_len = kw_len
                best_priority = priority

        mapping_dict[text] = best_match if best_match else default_category

    result[target_col] = combined_series.map(mapping_dict)

    return result