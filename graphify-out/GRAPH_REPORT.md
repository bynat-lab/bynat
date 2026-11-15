# Graph Report - Bynat  (2026-11-10)

## Corpus Check
- 112 files · ~81,537 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1292 nodes · 2350 edges · 101 communities (74 shown, 8 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 48 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a4dd229c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- base.py
- sync_docs.py
- _shares_doc
- test_accessor.py
- CacheManager
- ._finish_with_stats
- test_translate_batch.py
- DatasetProfile
- providers.py
- ._migrate_legacy_json_cache
- test_properties.py
- Changelog
- profile
- 4. Backlog
- translate.py
- profile.py
- verify_installed_wheel.py
- reference_impls.py
- _cached_map
- fill_missing_from
- test_fill_missing.py
- text.py
- README.md
- test_base_inplace.py
- nlp.py
- save_to_json
- test_nlp.py
- test_optional_sqlalchemy.py
- ColumnProfile
- Data profiling
- accessor.py
- Any
- Using bynat
- test_profile_general.py
- Enrichment with external services
- Cleaning method reference
- Limitations and operational notes
- Caching
- _compute_duplicate_rows
- Enrichment
- handle_outliers
- 3.3 Transformation-Specific Requirements
- test_concurrency.py
- bynat Brand Assets
- _seed_cache_entries
- bynat Testing Standards and Constitution
- .cache_manager
- test_columns_split.py
- get_hierarchical_stats
- 2.3 Universal Anti-Cheating Rules (A-1 through A-12)
- bynat
- test_optional_ahocorasick.py
- test_hierarchical_stats_output_types.py
- 0.6.5
- Milestone 9 (`0.9.0`): API maintenance
- bynat Roadmap
- test_columns_structural.py
- 3. Authority Level 2 — `bynat`-Specific Rules
- 5. Authority Level 3 — Examples and File-Level Applications
- caching/conftest.py
- test_translate_impute.py
- _import_optional
- 0.6.0
- test_persistence_recovery.py
- 6. Governance Framework
- 0.3.0
- 1. Preamble, Purpose, Scope, and Precedence
- test_text.py
- 0.1.2
- 0.2.0
- Development and verification
- fake_langdetect
- benchmarks/README.md
- test_fill_missing_from_imputation.py
- tests/conftest.py
- test_legacy_quarantine.py
- shared/__init__.py
- 4. CI Integration Specification
- test_outliers.py
- test_base_early_exits.py
- BaseData
- test_fill_missing_from_leakage.py

## God Nodes (most connected - your core abstractions)
1. `BaseData` - 163 edges
2. `CacheManager` - 127 edges
3. `profile()` - 34 edges
4. `_shares_doc()` - 30 edges
5. `_seed_cache_entries()` - 26 edges
6. `_cached_map()` - 23 edges
7. `save_to_json()` - 23 edges
8. `_import_optional()` - 19 edges
9. `main()` - 18 edges
10. `fill_missing()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `test_handle_and_drop_outliers_match_legacy()` --calls--> `_legacy_handle_outliers()`  [INFERRED]
  tests/cross_cutting/equivalence/test_equivalence_outliers.py → benchmarks/reference_impls.py
- `test_outliers_match_legacy_with_categorical_hierarchy()` --calls--> `_legacy_handle_outliers()`  [INFERRED]
  tests/cross_cutting/equivalence/test_equivalence_outliers.py → benchmarks/reference_impls.py
- `test_handle_and_drop_outliers_match_legacy()` --calls--> `_legacy_drop_outliers()`  [INFERRED]
  tests/cross_cutting/equivalence/test_equivalence_outliers.py → benchmarks/reference_impls.py
- `test_perf01_translate_categorical_matches_legacy()` --calls--> `_legacy_translate_categorical()`  [INFERRED]
  tests/cross_cutting/equivalence/test_equivalence_enrichment.py → benchmarks/reference_impls.py
- `test_perf01_convert_to_usd_matches_legacy()` --calls--> `_legacy_convert_to_usd()`  [INFERRED]
  tests/cross_cutting/equivalence/test_equivalence_enrichment.py → benchmarks/reference_impls.py

## Import Cycles
- None detected.

## Communities (101 total, 8 thin omitted)

### Community 0 - "base.py"
Cohesion: 0.15
Nodes (22): `pandas.DataFrame` subclasses: `BaseData`, `JsonFile`, and `CsvFile`. They are…, Compatibility shim: `bynat.cleaning.Cleaning` is now `bynat.cleaning.base`., _cache_has_value(), _cache_lookup_value(), _cache_value_key(), _constructor_accepts_data(), _convert_default_output(), _convert_output() (+14 more)

### Community 1 - "sync_docs.py"
Cohesion: 0.05
Nodes (58): AST, ClassDef, Constant, expr, FunctionDef, Module, Name, Verify that literal docstrings and the accessor stub match implementations. (+50 more)

### Community 2 - "_shares_doc"
Cohesion: 0.08
Nodes (25): RandomState, Return `result`, or copy it into this object when `inplace=True`., r""" Categorize text data into broader groups based on a reference lexicon…, Extract entities from free text by matching against a cached lexicon with spaCy…, Drop all columns that contain a specific substring within their names. Args:…, Drop all columns that contain the substring "__CLASS__" from the data. Returns:…, Rename columns by replacing a specific substring with a new one. Args:…, Rename columns by replacing all occurrences of dots ('.') with a unified… (+17 more)

### Community 3 - "test_accessor.py"
Cohesion: 0.06
Nodes (27): Compatibility shim: `bynat.caching.Caching` is now `bynat.caching.manager`., PathLike, Return `cache_dir`, else `$BYNAT_CACHE_DIR`, else the legacy relative default., Initialize the cache manager and resolve its storage directory. Relative paths…, Return one process-wide `CacheManager` per resolved cache directory. The…, resolve_cache_dir(), shared_cache_manager(), BynatAccessor (+19 more)

### Community 4 - "CacheManager"
Cohesion: 0.10
Nodes (32): CacheManager, Manage lightweight JSON cache files for function-level and column-level…, test_legacy_migration_imports_supported_values_and_maps_filename(), test_legacy_migration_is_idempotent_and_existing_rows_win(), test_missing_legacy_source_does_not_create_database_or_marker(), test_legacy_migration_rolls_back_and_can_retry_after_commit_failure(), test_legacy_migration_rolls_back_and_can_retry_after_marker_insert_failure(), test_legacy_migration_rolls_back_and_can_retry_after_partial_insert_failure() (+24 more)

### Community 5 - "._finish_with_stats"
Cohesion: 0.14
Nodes (8): Any, Impute missing values by progressively relaxing a grouping hierarchy. Notes:…, Impute missing values using statistics calculated from a reference dataset.…, Extract statistics for each progressively relaxed hierarchy level. The full…, Generate a structured, non-mutating data quality profile report for a…, `_finish` for methods that can also return hierarchical statistics., Replace outlier values with missing values using hierarchical IQR rules. Notes:…, Remove rows that contain outlier values based on hierarchical IQR rules. Notes:…

### Community 6 - "test_translate_batch.py"
Cohesion: 0.05
Nodes (38): FakeRateSource, _setup_currency_env(), test_perf01_convert_to_usd_matches_legacy(), test_perf01_translate_categorical_matches_legacy(), test_perf03_translate_conditional_partitioning_matches_legacy(), BatchTranslator, DictTranslator, install_fake_module() (+30 more)

### Community 7 - "DatasetProfile"
Cohesion: 0.18
Nodes (7): DatasetProfile, Dataset-level data quality summary metrics for a profiled DataFrame. Implements…, Convert the dataset profile into a plain Python dictionary. Returns: dict[str,…, Retrieve a dataset metric by its field name. Args: item (str): Name of the…, Iterate over the field names of the dataset profile. Returns: Iterator[str]: An…, Return the number of fields in the dataset profile. Returns: int: Total number…, test_report_structure_and_access_patterns()

### Community 8 - "providers.py"
Cohesion: 0.10
Nodes (17): fill_missing_coordinates(), FrameT, Cached geocoding of missing coordinates., Fill missing latitude and longitude values by geocoding fallback location text.…, External-service enrichment: translation, geocoding, currency, and NLP., Geocoder, GoogleTranslatorProvider, NominatimGeocoder (+9 more)

### Community 9 - "._migrate_legacy_json_cache"
Cohesion: 0.11
Nodes (13): Create the SQLite cache schema in one explicit transaction., Move a corrupt cache file aside without overwriting a quarantine., Import one legacy JSON cache into SQLite, without changing the API., Compatibility name for the reusable legacy migration helper., Rebuild the nested cache for one function from its SQLite rows. Reads every…, Validate a cache key before using it in file paths or dictionaries. Args: key…, Build the cache-file path for a specific function name. Args: func_name (str):…, Load a function cache from SQLite into memory on first access. The SQLite… (+5 more)

### Community 10 - "test_properties.py"
Cohesion: 0.06
Nodes (44): align_lat_lng(), drop_by_substring(), drop_CLASS_columns(), melt_transform_pivot(), move_column(), Any, FrameT, Column renaming, dropping, reordering, moving, and reshaping helpers. (+36 more)

### Community 11 - "Changelog"
Cohesion: 0.33
Nodes (3): [0.6.6], Added, Changelog

### Community 12 - "profile"
Cohesion: 0.16
Nodes (18): _clean_scalar(), profile(), Normalize a scalar or container value into a native, JSON-safe Python…, Generate a structured, non-mutating data quality profile report for a…, Test helpers and schema contracts for profile module tests., Tests for the data quality profiling API and report structures., test_contract_json_dumps_mixed_dataframe(), test_contract_stability_key_sets() (+10 more)

### Community 13 - "4. Backlog"
Cohesion: 0.22
Nodes (9): 4. Backlog, `ANALYTICS-01`: integrate the analytics library (P1, M), `COMPAT-01`: Python, pandas, and NumPy compatibility policy (P3, M), `DQ-02`: declarative DataFrame quality checks (P1, M), `IO-01`: append-friendly output (P3, M), Milestone 10 (`1.0.0`): I/O and compatibility, Milestone 7 (`0.7.0`): analytics integration, Milestone 8 (`0.8.0`): data quality (+1 more)

### Community 14 - "translate.py"
Cohesion: 0.14
Nodes (19): Validate integer parameters that control sampling or cache checkpointing.…, _require_positive_int(), Translate one text into `target_lang`. A provider may also define…, Translator, impute_by_language(), Any, FrameT, RandomState (+11 more)

### Community 15 - "profile.py"
Cohesion: 0.18
Nodes (16): _dedupe_key(), Return a hashable stand-in for unhashable values such as lists and dicts., _compute_boolean_stats(), _compute_categorical_stats(), _compute_datetime_stats(), _compute_distinct_count(), _compute_other_stats(), _detect_column_kind() (+8 more)

### Community 16 - "verify_installed_wheel.py"
Cohesion: 0.17
Nodes (32): CompletedProcess, _assert_no_checkout_side_effects(), _base_python(), _build_python(), _build_wheel(), _clean_env(), _copy_source(), _create_venv() (+24 more)

### Community 17 - "reference_impls.py"
Cohesion: 0.07
Nodes (45): main(), make_frame(), PERF-02: `extract_keywords` on unique texts with one combined pattern., main(), make_frame(), PERF-04: one-pass hierarchical IQR for `handle_outliers` and `drop_outliers`., best_of(), print_table() (+37 more)

### Community 18 - "_cached_map"
Cohesion: 0.15
Nodes (21): _cached_map(), Any, _rate_limited_map(), The cached-lookup engine shared by every enrichment method., Return the unique non-null values in first-seen order., Call `func` on every item and return results in input order, with an exception…, Resolve the unique values of `series` through a persistent cache. Every…, _unique_values() (+13 more)

### Community 19 - "fill_missing_from"
Cohesion: 0.16
Nodes (15): fill_missing_from(), Impute missing values using statistics calculated from a reference dataset.…, parametrize, Validation, BaseData, inplace, and edge contracts for fill_missing_from., Test validation of dataset, match_cols, hierarchy, types, and parameters., Test BaseData wrapper, inplace mutation, and get_hierarchical_stats contract., test_fill_missing_from_basedata_and_contracts(), test_fill_missing_from_duplicate_targets_are_deduplicated() (+7 more)

### Community 20 - "test_fill_missing.py"
Cohesion: 0.12
Nodes (18): fill_missing(), Impute missing values by progressively relaxing a grouping hierarchy. Notes:…, parametrize, fill_missing contracts: strategy normalization, min_samples, non-numeric…, test_basedata_fill_missing_helper(), test_fill_missing_and_fill_missing_from_reject_invalid_min_samples(), test_fill_missing_min_samples_and_fallback_global_reproduction(), test_fill_missing_min_samples_counts_only_non_null_observations() (+10 more)

### Community 21 - "text.py"
Cohesion: 0.24
Nodes (9): categorize_by_reference(), _optional_ahocorasick(), Any, FrameT, Keyword extraction, truncation, and categorization helpers., Return the `ahocorasick` module when installed, otherwise None., Remove specific substrings and everything following them from target columns.…, Categorize text data into broader groups based on a reference lexicon… (+1 more)

### Community 22 - "README.md"
Cohesion: 0.18
Nodes (10): Installation, License, Module layout, Optional integrations, Project status, Quick start, Requirements, Ways to use it (+2 more)

### Community 23 - "test_base_inplace.py"
Cohesion: 0.20
Nodes (17): INPLACE_XFAIL, _frame(), parametrize, BaseData inplace mutation, silence, and accessor rejection contracts., test_accessor_rejects_inplace_for_non_variadic_methods(), test_accessor_rejects_inplace_for_variadic_methods(), test_basedata_boundary_errors_and_inplace_return(), test_every_inplace_path_is_silent_and_preserves_behavior() (+9 more)

### Community 24 - "nlp.py"
Cohesion: 0.19
Nodes (13): extract_entities_nlp(), _lexicon_terms(), _nlp_cache_bucket(), _normalize_nlp_disable(), Any, FrameT, PathLike, Cached lexicon-based entity extraction with spaCy. (+5 more)

### Community 25 - "save_to_json"
Cohesion: 0.05
Nodes (59): CsvFile, JsonFile, PathLike, Save the dataframe to a JSON file only when content has changed. Notes: Before…, Load a JSON file into a `BaseData` frame., Load a CSV file into a `BaseData` frame., Initialize the custom dataframe from in-memory tabular data. Args: data:…, Any (+51 more)

### Community 26 - "test_nlp.py"
Cohesion: 0.19
Nodes (19): _install_fake_spacy(), _install_matching_spacy(), parametrize, Offline NLP entity extraction tests using fake spaCy modules., A spaCy stand-in whose matcher binds every token to the added column. Unlike…, _run_fake_nlp(), test_extract_entities_nlp_custom_disable_reaches_both_pipe_calls(), test_extract_entities_nlp_default_disable_reaches_both_pipe_calls() (+11 more)

### Community 27 - "test_optional_sqlalchemy.py"
Cohesion: 0.38
Nodes (15): _fetch_rows(), extras, integration, unit, _sqlite_arguments(), test_save_to_sql_appends_rows_with_the_default_if_exists(), test_save_to_sql_chunk_size_writes_every_row(), test_save_to_sql_columns_types_controls_sql_column_types() (+7 more)

### Community 28 - "ColumnProfile"
Cohesion: 0.25
Nodes (5): ColumnProfile, Data quality metrics and descriptive statistics for a single DataFrame column.…, Convert the column profile into a plain Python dictionary. Returns: dict[str,…, Iterate over the field names of the column profile. Returns: Iterator[str]: An…, Return the number of fields in the column profile. Returns: int: Total number…

### Community 29 - "Data profiling"
Cohesion: 0.18
Nodes (11): Choosing columns, Column fields, Data profiling, Dataset fields, How columns are classified, How values are counted, Output types, Statistics by kind (+3 more)

### Community 30 - "accessor.py"
Cohesion: 0.20
Nodes (9): _cached_frame_method(), _frame_method(), _method_signature(), The `df.bynat` pandas accessor., The accessor-facing signature: `self` replaces the frame, no `cache_manager`., Expose a shared implementation as an accessor method on the wrapped frame., Like `_frame_method`, also passing the accessor's `CacheManager`., JSON and SQL export helpers, and the JSON/CSV loaders. (+1 more)

### Community 31 - "Any"
Cohesion: 0.22
Nodes (6): _compute_numeric_stats(), Any, Compute descriptive statistics for a numeric column. Calculates central…, Retrieve a column profile field by its attribute name. Args: item (str): Name…, Serialize the full profile report to a nested dictionary of Python primitives.…, Retrieve a top-level section of the report by key (``'dataset'`` or…

### Community 32 - "Using bynat"
Cohesion: 0.22
Nodes (9): Class-based API and accessor: key differences, Common tasks, How the cleaning code is organized, Import styles, Supported imports, The class-based API, The pandas accessor, The same job in both styles (+1 more)

### Community 33 - "test_profile_general.py"
Cohesion: 0.09
Nodes (10): ProfileReport, Complete data quality report for a DataFrame. Combines dataset-wide summary…, Iterate over the top-level mapping keys of the report. Returns: Iterator[str]:…, Return the number of top-level sections in the report mapping. Returns: int:…, Return a concise human-readable summary string of the profile report. Returns:…, bynat: reusable pandas cleaning and enrichment utilities. Importing `bynat`…, Tests for the data quality profiling API and report structures., test_column_selection_and_errors() (+2 more)

### Community 34 - "Enrichment with external services"
Cohesion: 0.25
Nodes (8): Advanced features, Choosing the output type, Enrichment with external services, Hierarchical statistics, How currency rates are fetched, How translation providers are called, Providers, The shared lookup engine

### Community 35 - "Cleaning method reference"
Cohesion: 0.20
Nodes (10): Cache and object helpers, Cleaning method reference, Columns, Data profiling, Hierarchical missing value imputation, Outliers, missing values, and statistics, Reference-based missing value imputation (`fill_missing_from`), Returning statistics from cleaning methods (+2 more)

### Community 36 - "Limitations and operational notes"
Cohesion: 0.29
Nodes (7): Cache behavior, External services, Limitations and operational notes, Logging, NLP extraction, Optional integrations, SQL

### Community 37 - "Caching"
Cohesion: 0.29
Nodes (7): Cache rules, CacheManager reference, Caching, Migrating legacy JSON caches, Saving and failures, Using CacheManager directly, Where the cache is stored

### Community 38 - "_compute_duplicate_rows"
Cohesion: 0.40
Nodes (4): _compute_duplicate_rows(), DataFrame, Count duplicate rows in a DataFrame using ``keep='first'`` semantics. The first…, Convert per-column quality profiles into a tabular ``pandas.DataFrame``. Each…

### Community 39 - "Enrichment"
Cohesion: 0.40
Nodes (5): `convert_to_usd`, Enrichment, `extract_entities_nlp`, `fill_missing_coordinates`, `translate_conditional_column`

### Community 40 - "handle_outliers"
Cohesion: 0.14
Nodes (23): drop_outliers(), handle_outliers(), _hierarchical_outlier_masks(), _normalize_hierarchy(), Any, DataFrame, FrameT, ndarray (+15 more)

### Community 41 - "3.3 Transformation-Specific Requirements"
Cohesion: 0.18
Nodes (11): 3.3.10 Mutation and Leakage Standards (ML-1 through ML-7), 3.3.1 Shared Transformation Requirements (S-1 through S-7), 3.3.2 `fill_missing` Requirements (FM-1 through FM-24), 3.3.3 `fill_missing_from` Requirements (FF-1 through FF-27), 3.3.4 `handle_outliers` Requirements (HO-1 through HO-15), 3.3.5 `drop_outliers` Requirements (DO-1 through DO-8), 3.3.6 Hierarchical Fallback Standards (HF-1 through HF-6), 3.3.7 `min_samples` Standards (MS-1 through MS-4) (+3 more)

### Community 42 - "test_concurrency.py"
Cohesion: 0.15
Nodes (17): _add_key_after_baseline_worker(), _concurrent_save_worker(), _first_writer_worker(), _load_baseline_then_delete_worker(), parametrize, First writer: load the shared baseline, then commit ``value_a`` and signal. The…, Second writer: load the shared baseline, wait for the first commit, then commit…, Adding worker: wait for the deleter's baseline, commit one new key, signal.… (+9 more)

### Community 43 - "bynat Brand Assets"
Cohesion: 0.40
Nodes (4): bynat Brand Assets, Logo and Brand Assets, Scope, Software License

### Community 44 - "_seed_cache_entries"
Cohesion: 0.15
Nodes (21): Return ``(bucket, key, value_json)`` rows for the shared cache database., Insert raw cache_entries rows for ``func_name`` and return the manager., _rows(), _seed_cache_entries(), test_delete_column_cache_failed_transaction_is_retryable(), test_delete_column_cache_leaves_unrelated_buckets_intact(), test_delete_column_cache_leaves_unrelated_function_intact(), test_delete_column_cache_missing_bucket_is_a_no_op() (+13 more)

### Community 45 - "bynat Testing Standards and Constitution"
Cohesion: 0.33
Nodes (6): 2.1 General Testing Philosophy, 2.2 Universal Test Types, 2.4 General Test Design and Organization, 2. Authority Level 1 — General Testing Principles and Rules, bynat Testing Standards and Constitution, Contents

### Community 47 - "test_columns_split.py"
Cohesion: 0.22
Nodes (4): parametrize, List splitting and exploding transformations on structured columns., test_basedata_split_list_objects_and_melt_transform_pivot_helpers(), test_split_list_objects_all_index_copies_the_source_list()

### Community 48 - "get_hierarchical_stats"
Cohesion: 0.16
Nodes (16): get_hierarchical_stats(), Extract statistics for each progressively relaxed hierarchy level. The full…, test_get_hierarchical_stats_non_numeric_target_mode_is_allowed(), test_get_hierarchical_stats_skips_missing_targets(), parametrize, Hierarchical statistics validation contracts: invalid output types,…, test_fill_missing_nonexistent_target_with_hierarchical_stats(), test_get_hierarchical_stats_empty_or_no_hierarchy_explicit_output_type() (+8 more)

### Community 49 - "2.3 Universal Anti-Cheating Rules (A-1 through A-12)"
Cohesion: 0.15
Nodes (13): 2.3 Universal Anti-Cheating Rules (A-1 through A-12), A-10: No Network Calls, Secrets, or Persistent User Environment Access, A-11: No Test-Only Hooks in Production Code, A-12: Do Not Weaken Existing Tests, A-1: A Test MUST Be Able to Fail, A-2: Never Replace the Unit Under Test, A-3: Assert the Contract, Not the Implementation, A-4: No Blanket Exception Swallowing (+5 more)

### Community 51 - "test_optional_ahocorasick.py"
Cohesion: 0.36
Nodes (10): extras, integration, unit, test_categorize_by_reference_combines_multiple_source_columns(), test_categorize_by_reference_ignores_blank_keywords(), test_categorize_by_reference_overwrites_an_existing_target_column(), test_categorize_by_reference_prefers_the_longest_matching_keyword(), test_categorize_by_reference_respects_word_boundaries_and_case() (+2 more)

### Community 52 - "test_hierarchical_stats_output_types.py"
Cohesion: 0.18
Nodes (6): parametrize, Hierarchical statistics output type contracts: DataFrame, dict, BaseData…, test_get_hierarchical_stats_all_output_types_keep_multi_strategy_schema(), test_get_hierarchical_stats_returns_requested_type_for_empty_results(), test_get_hierarchical_stats_supports_explicit_basedata_family_outputs(), test_get_hierarchical_stats_supports_explicit_dataframe_and_dict_outputs()

### Community 53 - "0.6.5"
Cohesion: 0.50
Nodes (4): 0.6.5, Added, Changed, Fixed

### Community 54 - "Milestone 9 (`0.9.0`): API maintenance"
Cohesion: 0.50
Nodes (4): `DEPR-02`: standardize transformation behavior and maintenance boundaries (P2, S), Milestone 9 (`0.9.0`): API maintenance, `PERF-05`: rates through the engine (P3, S), `PERF-06`: equivalence and benchmark evidence for `PERF-01` and `PERF-03` (P2, M)

### Community 55 - "bynat Roadmap"
Cohesion: 0.22
Nodes (9): 1. Project context, 2. Principles, 3. Current state (`0.6.6`), 5. Decisions, 6. Definition of done, 7. Corrections to the previous roadmap draft, bynat Roadmap, Done (+1 more)

### Community 58 - "3. Authority Level 2 — `bynat`-Specific Rules"
Cohesion: 0.22
Nodes (9): 3.1 Test-Suite Architecture and Ownership (BYNAT-ARCH), 3.2 Required DataFrame Cases and Assertion Standards (DF and BYNAT-ASSERT), 3.4 Public API, Export Boundaries, and Optional Integrations (BYNAT-API), 3.5 Markers, Pytest Configuration, Hypothesis Profiles, and Static Typing (BYNAT-MARK and BYNAT-CFG), 3.6 Coverage, Property Invariants, Mutation Testing, and Supporting Tooling (BYNAT-METRIC and BYNAT-TOOL), 3.7 Phased Adoption Roadmap Status, 3. Authority Level 2 — `bynat`-Specific Rules, Assertion Standards (BYNAT-ASSERT-1 through BYNAT-ASSERT-5) (+1 more)

### Community 59 - "5. Authority Level 3 — Examples and File-Level Applications"
Cohesion: 0.25
Nodes (8): 5.1 Example 1: Hierarchical Directory Mapping and Decomposed Responsibility Files, 5.2 Example 2: Cross-Domain Shared Constants vs Module-Local Helpers, 5.3 Example 3: Cache Directory Isolation via Autouse Fixture, 5.4 Example 4: Offline Provider Fakes vs Real Optional-Dependency Tests, 5.5 Example 5: Strict DataFrame and Immutability Assertions, 5.6 Example 6: Property-Based Invariant Testing, 5.7 Example 7: Strict Xfail Pinning for Tracked Production Defects, 5. Authority Level 3 — Examples and File-Level Applications

### Community 60 - "caching/conftest.py"
Cohesion: 0.33
Nodes (6): cache_dir(), _isolated_default_cache_dir(), fixture, Module-local fixtures for the caching test suite. Every caching test must run…, Return an isolated cache directory under the test's ``tmp_path``., Redirect the default cache directory to an isolated per-test path.

### Community 61 - "test_translate_impute.py"
Cohesion: 0.29
Nodes (4): test_impute_by_language_inplace_matches_the_copy_result(), test_impute_by_language_missing_reference_returns_before_optional_import(), test_impute_by_language_skips_missing_columns(), usefixtures

### Community 62 - "_import_optional"
Cohesion: 0.15
Nodes (14): _import_optional(), Import a feature dependency only when the feature is used., convert_to_usd(), _lookback_years(), Any, FrameT, Cached conversion of local-currency amounts to USD., Years checked for a rate, from `year` back to `min_year`. (+6 more)

### Community 63 - "0.6.0"
Cohesion: 0.33
Nodes (6): 0.6.0, Added, Breaking changes, Changed, Deprecated, Fixed

### Community 64 - "test_persistence_recovery.py"
Cohesion: 0.25
Nodes (7): parametrize, test_corrupt_cache_is_quarantined_and_replaced_with_empty_dict(), test_failed_db_save_keeps_baseline_and_rows_intact_for_retry(), test_failed_removal_transaction_rolls_back_and_retries(), test_save_serialization_failure_keeps_prior_checkpoint_readable(), test_save_transaction_rolls_back_on_commit_failure(), test_save_unserializable_value_reports_error_without_raising()

### Community 65 - "6. Governance Framework"
Cohesion: 0.33
Nodes (6): 6.1 AI Agent Protocol, 6.2 Human Review Checklist, 6.3 Authoritative References, 6. Governance Framework, External Testing and Packaging Standards, Internal Repository Specifications

### Community 66 - "0.3.0"
Cohesion: 0.40
Nodes (5): 0.3.0, Added, Breaking changes, Changed, Fixed

### Community 67 - "1. Preamble, Purpose, Scope, and Precedence"
Cohesion: 0.40
Nodes (5): 1.1 Purpose, 1.2 Scope, 1.3 Applies to, 1.4 Precedence and Relationship to Other Documents, 1. Preamble, Purpose, Scope, and Precedence

### Community 69 - "0.1.2"
Cohesion: 0.50
Nodes (4): 0.1.2, Added, Changed, Fixed

### Community 70 - "0.2.0"
Cohesion: 0.50
Nodes (4): 0.2.0, Added, Breaking changes, Fixed

### Community 71 - "Development and verification"
Cohesion: 0.50
Nodes (4): Benchmarks, Building packages, Development and verification, Type checking

### Community 76 - "test_fill_missing_from_imputation.py"
Cohesion: 0.13
Nodes (13): Core reference-based missing value imputation workflows and contracts., Test match_cols mapping between target and reference schemas., Test basic column-wide and 1-level hierarchical reference imputation with mean,…, Test empty target, no-missing target, all-missing target, and all-null…, Test index and row-order preservation with named, duplicate, and MultiIndex…, Regression test ensuring existing fill_missing behavior remains unchanged., Test multi-level hierarchies and min_samples fallthrough using reference…, test_existing_fill_missing_remains_unchanged() (+5 more)

### Community 91 - "test_legacy_quarantine.py"
Cohesion: 0.33
Nodes (5): parametrize, test_legacy_migration_preserves_unsupported_source_for_retry(), test_legacy_migration_quarantine_and_read_errors(), test_legacy_migration_quarantines_corrupt_source_without_marker(), test_quarantine_corrupt_cache_file_fallbacks()

### Community 95 - "4. CI Integration Specification"
Cohesion: 0.40
Nodes (5): 4.1 Workflows and Job Matrix, 4.2 Marker Selection and Execution Architecture, 4.3 Windows and Cross-Platform Parity, 4.4 Local vs CI Parity and Verification Invariants, 4. CI Integration Specification

### Community 96 - "test_outliers.py"
Cohesion: 0.36
Nodes (8): MIN_SAMPLES_XFAIL, parametrize, Outlier-method contracts: hierarchy validation, min_samples boundary, and…, test_drop_outliers_rejects_invalid_min_samples(), test_handle_outliers_min_samples_boundary(), test_handle_outliers_rejects_invalid_min_samples(), test_outlier_methods_raise_keyerror_for_a_missing_named_hierarchy(), test_outlier_methods_warn_and_return_an_unchanged_copy_without_hierarchy()

### Community 98 - "test_base_early_exits.py"
Cohesion: 0.47
Nodes (5): _frame(), parametrize, BaseData early exit copy independence contracts., test_early_exit_with_stats_returns_a_copy(), test_early_exits_return_an_independent_copy()

### Community 99 - "BaseData"
Cohesion: 0.07
Nodes (34): BaseData, DataFrame, Delete a cached column bucket for one of the helper methods. Args: func_name…, Save the dataframe to a SQL database table using SQLAlchemy. Notes: The method…, Return the object as a standard pandas DataFrame for inspection and rich…, Extend `pandas.DataFrame` with project-specific cleaning, translation,…, parametrize, Class/accessor parity (S-5): BaseData and the bynat accessor produce equal… (+26 more)

### Community 100 - "test_fill_missing_from_leakage.py"
Cohesion: 0.50
Nodes (3): Statistical isolation and anti-leakage contracts for reference imputation., Verify that target DataFrame values never affect calculated statistics and…, test_fill_missing_from_prevents_statistical_leakage()

## Knowledge Gaps
- **147 isolated node(s):** `bynat`, `Added`, `Added`, `Changed`, `Fixed` (+142 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 543 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BaseData` connect `BaseData` to `base.py`, `sync_docs.py`, `_shares_doc`, `test_accessor.py`, `._finish_with_stats`, `test_translate_batch.py`, `providers.py`, `test_properties.py`, `profile`, `translate.py`, `profile.py`, `fill_missing_from`, `test_fill_missing.py`, `test_base_inplace.py`, `nlp.py`, `save_to_json`, `test_nlp.py`, `test_optional_sqlalchemy.py`, `accessor.py`, `test_profile_general.py`, `.cache_manager`, `test_columns_split.py`, `get_hierarchical_stats`, `test_optional_ahocorasick.py`, `test_hierarchical_stats_output_types.py`, `test_columns_structural.py`, `test_translate_impute.py`, `test_text.py`, `test_base_early_exits.py`?**
  _High betweenness centrality (0.372) - this node is a cross-community bridge._
- **Why does `CacheManager` connect `CacheManager` to `base.py`, `sync_docs.py`, `test_persistence_recovery.py`, `test_accessor.py`, `test_translate_batch.py`, `providers.py`, `._migrate_legacy_json_cache`, `test_concurrency.py`, `_seed_cache_entries`, `.cache_manager`, `translate.py`, `_cached_map`, `save_to_json`, `_import_optional`, `nlp.py`, `test_legacy_quarantine.py`, `accessor.py`?**
  _High betweenness centrality (0.161) - this node is a cross-community bridge._
- **Why does `profile()` connect `profile` to `test_profile_general.py`, `BaseData`, `_compute_duplicate_rows`, `DatasetProfile`, `profile.py`, `ColumnProfile`, `Any`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `BaseData` (e.g. with `Geocoder` and `RateSource`) actually correct?**
  _`BaseData` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bynat`, `Added`, `Added` to the rest of the system?**
  _147 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sync_docs.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05480769230769231 - nodes in this community are weakly interconnected._
- **Should `_shares_doc` be split into smaller, more focused modules?**
  _Cohesion score 0.0797979797979798 - nodes in this community are weakly interconnected._

## Project Design & Styling Instructions (bynat Brand Theme)

> **Persistent Instruction for Agents & Maintainers:** Whenever `graphify update .`, `graphify cluster-only`, or `graphify export html` is executed on this repository, the knowledge graph visualization (`graphify-out/graph.html`) and this design specification section in `graphify-out/GRAPH_REPORT.md` **must** maintain the official `bynat` brand identity derived from `assets/Full Logo/logo-dark.svg`, `assets/Logo/symbol-dark.svg`, and `assets/347981844.png`.

### 1. Brand Color Tokens & Surface Hierarchy
- **Midnight Navy (`#14213D`)** — Primary brand background and eye-pupil tone from `logo.svg` / `logo-dark.svg`. Used as the radial center of the graph canvas, elevated inspector cards, and primary surface anchor.
- **Deepest Navy (`#0B1324` / `#101B33`)** — Outer canvas vignette (`#0B1324`) and sidebar container surface (`#101B33`), with `#243863` structural borders.
- **Bynat Vermilion (`#F9442A`)** — Primary brand accent from the `bynat` arch mark. Used for Community 0, primary focus rings, active checkboxes, God-node badges, hyperedge regions, and interactive highlights.
- **Warm Cream (`#FFF1DC`)** — Primary foreground and data-column pill color from `logo-dark.svg`. Used for primary typography, high-degree node labels, selected node highlights, and Community 1.
- **Muted Cream & Slate (`#DFD0BA` / `#8FA4C7`)** — Secondary body copy (`#DFD0BA`) and uppercase section headers, degree counters, and source-file metadata (`#8FA4C7`).

### 2. Visual Motifs & Typography
- **Brand Header & Favicon:** `graphify-out/graph.html` embeds `assets/Full Logo/logo-dark.svg` in `#brand-header` alongside a pill-shaped `KNOWLEDGE GRAPH` badge and uses `assets/Logo/symbol-dark.svg` on a `#14213D` rounded-square canvas as its inline SVG favicon.
- **Rounded Data-Column Pill Geometry:** Cards, search inputs, neighbor links, and badges use `10px`–`14px` / `999px` border radii echoing the three rounded vertical data-column pills (`rx="14"`) of the `bynat` symbol.
- **Typography:** `Plus Jakarta Sans` for UI controls and graph labels paired with `JetBrains Mono` for source file paths, line numbers, degree badges, and graph statistics.
- **Community Color Sequence:** Anchored by `#F9442A` (Vermilion) and `#FFF1DC` (Warm Cream), followed by a 20-color high-contrast palette tuned for legibility over `#14213D` Midnight Navy.

### 3. Automatic Maintenance Workflow during Updates
- **Custom Builder Hook (`graphify-out/build_graph_html.js`):** `graphify`'s `to_html()` exporter automatically detects and executes `graphify-out/build_graph_html.js` via Node.js whenever `graphify update .` or `graphify export html` runs.
- **Report Instruction Persistence:** `graphify-out/build_graph_html.js` also idempotently ensures this `## Project Design & Styling Instructions (bynat Brand Theme)` section remains present at the end of `graphify-out/GRAPH_REPORT.md` whenever the report is regenerated.
- **Manual Re-application Command:** If `graph.html` or `GRAPH_REPORT.md` is ever manually overwritten, run `node graphify-out/build_graph_html.js` (or `graphify update .`) to restore the full `bynat` brand theme and report instructions.
