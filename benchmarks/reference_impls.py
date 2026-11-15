"""0.3.0 reference implementations shared by the benchmarks and the equivalence tests.

These functions preserve the pre-optimization algorithms verbatim apart from the
``self`` -> ``df`` rename. They live here, outside ``tests/``, so that neither
the benchmark scripts nor the equivalence test module imports a test module.
"""

import re

import numpy as np
import pandas as pd

from bynat.cleaning._common import _left_merge_aligned


def _legacy_extract_keywords(df, *source_cols, remove_extracted=False, use_regex=False, **target_cols_and_keywords):
    valid_sources = [col for col in source_cols if col in df.columns]
    combined_text = df[valid_sources].fillna('').astype(str).agg(' '.join, axis=1)
    result = df.copy()

    for new_col_name, keywords_list in target_cols_and_keywords.items():
        if isinstance(keywords_list, (str, bytes)) or not hasattr(keywords_list, '__iter__'):
            keywords_list = [keywords_list]

        cleaned_keywords = [str(word).strip() for word in keywords_list if word is not None and str(word).strip()]

        if not cleaned_keywords:
            continue

        extracted = pd.Series(index=combined_text.index, dtype=str)

        for word in reversed(cleaned_keywords):
            if use_regex:
                try:
                    extracted_match = combined_text.str.extract(word, expand=True)
                except ValueError:
                    extracted_match = combined_text.str.extract(rf"({word})", expand=True)

                if not extracted_match.empty:
                    match_col = extracted_match.iloc[:, 0]
                    mask = match_col.notna()
                    extracted.loc[mask] = match_col[mask]
            else:
                pattern = rf"(?i)(?<!\w){re.escape(word)}(?!\w)"
                mask = combined_text.str.contains(pattern, na=False, regex=True)
                extracted.loc[mask] = word.title()

        if new_col_name in result.columns:
            result[new_col_name] = result[new_col_name].astype('object')
            result[new_col_name] = result[new_col_name].where(result[new_col_name].notna(), extracted)
        else:
            result[new_col_name] = extracted

        mask_extracted = result[new_col_name].notna()
        result.loc[mask_extracted, new_col_name] = result.loc[mask_extracted, new_col_name].astype(str).str.title()

        if remove_extracted:
            if use_regex:
                for col in valid_sources:
                    mask = result[col].notna()
                    for pattern in cleaned_keywords:
                        result.loc[mask, col] = result.loc[mask, col].astype(str).str.replace(pattern, '', regex=True)
                    result.loc[mask, col] = result.loc[mask, col].str.replace(r'\s+', ' ', regex=True).str.strip()
            else:
                escaped_keywords = [re.escape(word) for word in cleaned_keywords]
                remove_pattern = rf"(?i)(?<!\w)({'|'.join(escaped_keywords)})(?!\w)"
                for col in valid_sources:
                    mask = result[col].notna()
                    result.loc[mask, col] = result.loc[mask, col].astype(str).str.replace(remove_pattern, '', regex=True)
                    result.loc[mask, col] = result.loc[mask, col].str.replace(r'\s+', ' ', regex=True).str.strip()

    return result


def _legacy_outlier_masks(result, target_col, hierarchy_cols, min_samples, on_outliers):
    processed_mask = pd.Series(False, index=result.index)
    current_hierarchy = hierarchy_cols.copy()

    while current_hierarchy:
        unprocessed_mask = (~processed_mask) & result[target_col].notna()

        if unprocessed_mask.sum() == 0:
            break

        grouped = result.groupby(current_hierarchy, dropna=False)[target_col]
        group_sizes = grouped.transform('count')
        valid_group_mask = group_sizes >= min_samples
        valid_data = result[valid_group_mask]

        if not valid_data.empty:
            valid_grouped = valid_data.groupby(current_hierarchy, dropna=False)[target_col]
            q1 = valid_grouped.quantile(0.25).rename('q1')
            q3 = valid_grouped.quantile(0.75).rename('q3')
            bounds = pd.concat([q1, q3], axis=1).reset_index()
            iqr = bounds['q3'] - bounds['q1']
            bounds['lower_bound'] = bounds['q1'] - 1.5 * iqr
            bounds['upper_bound'] = bounds['q3'] + 1.5 * iqr
            merged_df = _left_merge_aligned(result, bounds.drop(columns=['q1', 'q3']), current_hierarchy)
            is_outlier = (
                valid_group_mask & unprocessed_mask &
                merged_df['lower_bound'].notna() &
                ((result[target_col] < merged_df['lower_bound']) | (result[target_col] > merged_df['upper_bound']))
            )
            if is_outlier.sum() > 0:
                on_outliers(is_outlier)

        processed_mask = processed_mask | valid_group_mask
        current_hierarchy.pop()


def _legacy_handle_outliers(df, *target_cols, hierarchy_cols, min_samples=5):
    result = df.copy()

    for target_col in target_cols:
        if target_col not in result.columns:
            continue

        def blank(is_outlier, target_col=target_col):
            result.loc[is_outlier, target_col] = np.nan

        _legacy_outlier_masks(result, target_col, hierarchy_cols, min_samples, blank)

    return result


def _legacy_drop_outliers(df, *target_cols, hierarchy_cols, min_samples=5):
    result = df.copy()
    drop_mask = np.zeros(len(result), dtype=bool)

    def collect(is_outlier):
        nonlocal drop_mask
        drop_mask |= is_outlier.to_numpy(dtype=bool)

    for target_col in target_cols:
        if target_col in result.columns:
            _legacy_outlier_masks(result, target_col, hierarchy_cols, min_samples, collect)

    if drop_mask.any():
        original_index = result.index
        result.index = pd.RangeIndex(len(result))
        result = result.drop(index=np.flatnonzero(drop_mask))
        result.index = original_index[~drop_mask]

    return result


def _legacy_translate_categorical(df, target_col, target_lang="en", provider=None):
    result = df.copy()
    if target_col not in result.columns:
        return result
    unique_vals = result[target_col].dropna().unique()
    mapping = {}
    for val in unique_vals:
        if provider is not None:
            if hasattr(provider, "mapping"):
                translated = provider.mapping.get(val)
            else:
                translated = provider.translate(str(val), target_lang)
            if translated:
                mapping[val] = translated
        else:
            mapping[val] = str(val)
    result[target_col] = result[target_col].map(mapping).fillna(result[target_col])
    return result


def _legacy_convert_to_usd(
    df,
    *target_cols,
    country_col,
    year_col,
    rate_source=None,
    country_to_currency=None,
    new_cols=False,
    round_decimals=None,
):
    result = df.copy()
    valid_cols = [c for c in target_cols if c in result.columns]
    if not valid_cols or country_col not in result.columns or year_col not in result.columns:
        return result
    rates_mapping = {}
    for _, row in result[[country_col, year_col]].drop_duplicates().dropna().iterrows():
        country = str(row[country_col]).strip()
        try:
            year = int(float(row[year_col]))
        except (TypeError, ValueError):
            year = None
        curr_code = country_to_currency.get(country) if country_to_currency else None
        rate = None
        if curr_code and curr_code.upper() == "USD":
            rate = 1.0
        elif curr_code and year is not None and rate_source is not None:
            rates = rate_source.yearly_rates(curr_code, year, year)
            rate = rates.get(year)
        rates_mapping[(row[country_col], row[year_col])] = rate

    rates_df = pd.Series(rates_mapping).reset_index()
    if not rates_df.empty:
        rates_df.columns = [country_col, year_col, "_conversion_rate"]
        temp_df = _left_merge_aligned(result, rates_df, [country_col, year_col])
        for col in valid_cols:
            col_name = f"{col}_usd" if new_cols else col
            result[col_name] = result[col] / temp_df["_conversion_rate"]
            if round_decimals is not None:
                result[col_name] = result[col_name].round(round_decimals)
    return result


def _legacy_translate_conditional_column(
    df,
    partition_col,
    detect_col,
    target_col,
    target_lang="en",
    sample_size=10,
    number_of_samples=3,
    threshold=0.5,
    random_state=0,
    provider=None,
    detect=None,
):
    result = df.copy()
    if not all(col in result.columns for col in [partition_col, detect_col, target_col]):
        return result
    if detect is None:
        import langdetect
        detect = langdetect.detect

    if isinstance(random_state, (np.random.Generator, np.random.RandomState)):
        rng = random_state
    else:
        rng = np.random.default_rng(random_state)

    safe_partitions = []
    unique_partitions = result[partition_col].dropna().unique()
    for partition in unique_partitions:
        texts = result.loc[result[partition_col] == partition, detect_col]
        available_texts = texts.dropna().drop_duplicates()
        if available_texts.empty:
            continue
        actual_sample_size = min(sample_size, len(available_texts))
        lang_match_count = 0
        for _ in range(number_of_samples):
            sample_texts = available_texts.sample(n=actual_sample_size, random_state=rng)
            combined_text = " . ".join(sample_texts.astype(str).tolist())
            try:
                if detect(str(combined_text)) == target_lang:
                    lang_match_count += 1
            except Exception:
                pass
        if lang_match_count >= (number_of_samples * threshold):
            safe_partitions.append(partition)

    mask_foreign = ~result[partition_col].isin(safe_partitions)
    foreign_values = result.loc[mask_foreign, target_col].dropna().unique()
    mapping = {}
    for val in foreign_values:
        if provider is not None:
            translated = provider.translate(str(val), target_lang)
            if translated:
                mapping[val] = translated
        else:
            mapping[val] = str(val)

    result[target_col] = result[target_col].map(mapping).fillna(result[target_col])
    mask_translated = result[target_col].notna()
    result.loc[mask_translated, target_col] = result.loc[mask_translated, target_col].astype(str).str.title()
    return result
