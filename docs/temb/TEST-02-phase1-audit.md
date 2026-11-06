# TEST-02 — Phase 1: Comprehensive Test Suite Inventory & Audit

**Repository:** `bynat` (D:\My Own Environment Libraries\bynat\bynat)
**Revision audited:** `ddca26d76e8874223f5829fee0aea0fef461472a` (`ddca26d docs(testing): add comprehensive test suite audit plan and quality improvement phases`)
**Audit date:** 2026-11-06 (Egypt Standard Time, UTC+02:00)
**Phase:** 1 — audit only. No repository file was created, edited, deleted, or modified. No git state was changed.
**Interpreter used for validation:** `D:\My Own Environment Libraries\bynat\bynat\.venv-check\Scripts\python.exe` — Python 3.11.16, pytest 9.2.0, pandas 3.0.6, numpy 2.5.4, pyahocorasick 2.3.1, SQLAlchemy 2.1.8 (the pre-existing environment used by the repository's own tooling).

> **Note on `337`.** The task instructed: "Do not assume that the previously reported count of 337 is still accurate. Re-establish the current baseline from the repository and report any differences." The independently re-established baseline **is 337 collected cases from 218 test definitions** — the previous count is confirmed, not different. The breakdown is new information: 197 non-parametrized definitions + 21 parametrized definitions producing 140 cases.

---

## A. Audit Summary

### A.1 Repository revision

- Commit: `ddca26d76e8874223f5829fee0aea0fef461472a`
- `git status --porcelain` → empty (clean tree) before and after the audit.
- `git diff --stat` → empty.
- Only ignored, pre-existing directories were present (`Settings/`, `*/__pycache__/`); no tracked or untracked non-ignored file was created or changed.

### A.2 Current test collection baseline (independently established)

| Metric | Value | Command |
| --- | --- | --- |
| Test files | **11** | `ls tests/test_*.py` |
| Test definitions (functions/methods) | **218** | AST scan of `tests/test_*.py` |
| Collected test cases (default invocation, `python -m pytest`) | **337** | `python -m pytest --collect-only -q` |
| Non-parametrized definitions → cases | 197 → 197 | AST + collection diff |
| Parametrized definitions → cases | 21 → 140 | AST + collection diff |
| Collection errors (default invocation, repo root) | **0** | `pytest --collect-only` |
| Deselected by default configuration | **0** | no `[tool.pytest.ini_options]`, no `addopts`, no markers |
| Skipped at collection | **0** | collection report |
| Passed (with extras installed) | **337** | `python -m pytest -q` → `337 passed in 36.01s` |
| Passed (default CI job: no optional extras) | **331** | `pytest -q` with `ahocorasick`/`sqlalchemy` blocked → `331 passed, 6 skipped in 34.23s` |
| Skipped (default CI job: no optional extras) | **6** | 4× `importorskip("ahocorasick")`, 2× `importorskip("sqlalchemy")` |
| Skipped on pandas 2 (not executable here) | **17** | `_LEGACY_RELIABLE` skipif: 16 cases of `test_handle_and_drop_outliers_match_legacy` + 1 case of `test_outliers_match_legacy_with_categorical_hierarchy` |
| Uncollectable in a non-root CWD / via `pytest` console script | **3** | `tests/test_doc_drift.py` — `ModuleNotFoundError: No module named 'tools'` (334 collected, 1 error) |

**Collection baseline is environment-dependent.** The same repository collects 337 cases in both environments, but the *executed* set differs: 337 with `categorization`+`sql` extras, 331 without. On pandas 2 the legacy-equivalence cases (17) are skipped by design. This is the first documented instance of a baseline that cannot be stated as a single number without qualifying the environment.

### A.3 Per-file inventory

| Test file | Lines | Definitions | Collected cases | Primary contracts |
| --- | ---: | ---: | ---: | --- |
| `tests/test_accessor.py` | 201 | 11 | 13 | `df.bynat` accessor, cache sharing, loader helpers |
| `tests/test_caching.py` | 1783 | 57 | 62 | `CacheManager` SQLite cache, transactions, migration, concurrency |
| `tests/test_cleaning.py` | 446 | 24 | 31 | `BaseData`/`JsonFile`/`CsvFile`, columns/text/io, `fill_missing` |
| `tests/test_doc_drift.py` | 86 | 3 | 3 | Docstring/stub sync, typing artifacts, runtime signatures |
| `tests/test_enrichment.py` | 469 | 20 | 20 | Provider protocols, cached-lookup engine, providers |
| `tests/test_equivalence.py` | 382 | 9 | 74 | Optimized vs 0.3.0 legacy / brute-force references |
| `tests/test_fill_missing_from.py` | 354 | 9 | 9 | `fill_missing_from` reference imputation |
| `tests/test_hierarchical_stats.py` | 705 | 30 | 41 | `get_hierarchical_stats`, hierarchy-method stats contracts |
| `tests/test_inplace_deprecation.py` | 174 | 9 | 33 | API-02 new-object default, `inplace=True`, warnings |
| `tests/test_integrations.py` | 612 | 21 | 26 | Offline enrichment integrations, real extras, NLP cache identity |
| `tests/test_profile.py` | 777 | 25 | 25 | `profile` report schema, kinds, statistics, outputs |
| **Total** | **5989** | **218** | **337** | |

### A.4 Audit disposition summary

| Disposition | Definitions | Meaning |
| --- | ---: | --- |
| STRONG | 182 | Assertions are specific, expected values are independent, contract is verified. |
| ADEQUATE | 18 | Contract is verified; minor weakness (parametrize IDs, partial parameter coverage, timing). |
| GUARD | 3 | Legitimate AST/no-merge guard tests explicitly allowed by `docs/TESTING_STANDARDS.md` §4 A-3 / HO-13. |
| CONDITIONAL | 6 | Correct behavior, but cases skip without an optional extra or on pandas 2. |
| WEAK | 7 | Assertion is too permissive, implementation-detail, version-dependent, or misleading. |
| REDUNDANT | 1 | Strict subset of another test; no independent regression value. |
| CRITICAL | 1 | **No assertion at all — the test cannot fail.** |
| **Total** | **218** | |

### A.5 Areas covered vs. requiring further investigation

**Covered well:** `fill_missing` strategies/hierarchy/`min_samples`/`fallback_global`; `fill_missing_from` leakage, reference immutability, hierarchy, `match_cols`, validation, index; outlier IQR rules and equivalence; `get_hierarchical_stats` schema/strategies/output types; `profile` schema/kinds/statistics/JSON; `CacheManager` round-trip, diffed save, rollback, legacy migration, concurrency, delete; accessor registration/signatures/cache sharing; enrichment providers/engine/cache semantics; docstring/stub drift.

**Requiring further investigation:** `inplace` rejection on variadic accessor/shared methods; outlier `min_samples` validation; duplicate-column profiling; README contract mismatches (`noisey_terms`, mode tie-break); positive paths of `rename_by_substring`, `drop_CLASS_columns`, `align_lat_lng`, `reorder_columns`, `truncate_after_substring`, `remove_source_col`, `cartesian_explode`, `impute_by_language`; caching/enrichment export contracts; property tests; collection robustness of `test_doc_drift.py`.

---

## B. Complete Test Inventory

The table below accounts for **every one of the 218 test definitions and 337 collected cases**. Dispositions are defined in A.4. "Cases" is the number of collected pytest node IDs produced by that definition under the default invocation from the repository root.

| # | Test file | Test function / method | Cases | Intended public API / behavior | Disposition | Evidence |
|---|-----------|------------------------|-------|-------------------------------|-------------|----------|
| 1 | `tests/test_accessor.py` | `test_importing_bynat_registers_the_accessor` (line 26) | 1 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | STRONG |  |
| 2 | `tests/test_accessor.py` | `test_accessor_methods_return_new_plain_frames_and_leave_the_source_alone` (line 33) | 1 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | STRONG |  |
| 3 | `tests/test_accessor.py` | `test_accessor_matches_basedata_results` (line 58) | 1 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | STRONG |  |
| 4 | `tests/test_accessor.py` | `test_accessor_methods_expose_signatures_without_the_frame_or_cache_manager` (line 75) | 1 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | STRONG |  |
| 5 | `tests/test_accessor.py` | `test_accessor_uses_one_shared_cache_manager_per_directory` (line 84) | 1 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | STRONG |  |
| 6 | `tests/test_accessor.py` | `test_accessor_cached_methods_use_the_selected_cache` (line 101) | 1 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | STRONG |  |
| 7 | `tests/test_accessor.py` | `test_accessor_save_to_json` (line 117) | 1 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | STRONG |  |
| 8 | `tests/test_accessor.py` | `test_read_json_and_read_csv_return_plain_frames` (line 125) | 1 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | STRONG |  |
| 9 | `tests/test_accessor.py` | `test_read_helpers_raise_like_the_legacy_loaders` (line 141) | 1 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | STRONG |  |
| 10 | `tests/test_accessor.py` | `test_supported_classes_construct_without_warning` (line 161) | 3 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | ADEQUATE | constructor emits no DeprecationWarning; unreadable <lambda>N IDs |
| 11 | `tests/test_accessor.py` | `test_pandas_operations_share_the_legacy_cache_manager` (line 176) | 1 | df.bynat accessor registration, method contracts, cache sharing, loader helpers | STRONG |  |
| 12 | `tests/test_caching.py` | `test_cache_round_trip_via_sqlite` (line 20) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 13 | `tests/test_caching.py` | `test_save_persists_added_changed_and_removed_entries` (line 36) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 14 | `tests/test_caching.py` | `test_save_persists_entirely_removed_buckets` (line 69) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 15 | `tests/test_caching.py` | `test_save_handles_deletion_only_transaction` (line 99) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 16 | `tests/test_caching.py` | `test_failed_removal_transaction_rolls_back_and_retries` (line 121) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 17 | `tests/test_caching.py` | `test_save_advances_baseline_after_removal` (line 187) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 18 | `tests/test_caching.py` | `test_cache_rejects_empty_and_path_like_keys` (line 213) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 19 | `tests/test_caching.py` | `test_corrupt_cache_is_quarantined_and_replaced_with_empty_dict` (line 235) | 4 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 20 | `tests/test_caching.py` | `test_save_unserializable_value_reports_error_without_raising` (line 265) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 21 | `tests/test_caching.py` | `test_cache_directory_is_created_on_save_not_construction` (line 288) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 22 | `tests/test_caching.py` | `test_failed_db_save_keeps_baseline_and_rows_intact_for_retry` (line 301) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 23 | `tests/test_caching.py` | `test_save_transaction_rolls_back_on_commit_failure` (line 357) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 24 | `tests/test_caching.py` | `test_save_serialization_failure_keeps_prior_checkpoint_readable` (line 418) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 25 | `tests/test_caching.py` | `test_cache_dir_defaults_to_environment_variable_then_legacy_path` (line 439) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 26 | `tests/test_caching.py` | `test_sqlite_initialization_is_lazy_until_explicitly_requested` (line 449) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 27 | `tests/test_caching.py` | `test_sqlite_schema_has_required_tables_columns_keys_and_index` (line 460) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | ADEQUATE | exact PRAGMA tuples; brittle but cache is unit under test |
| 28 | `tests/test_caching.py` | `test_sqlite_connection_configures_timeout_wal_and_full_synchronous` (line 502) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | ADEQUATE | PRAGMA connection settings |
| 29 | `tests/test_caching.py` | `test_sqlite_connection_closes_when_pragma_configuration_fails` (line 515) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 30 | `tests/test_caching.py` | `test_sqlite_initialization_rolls_back_and_closes_on_failure` (line 543) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 31 | `tests/test_caching.py` | `test_sqlite_initialization_rolls_back_real_ddl_on_later_schema_failure` (line 572) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 32 | `tests/test_caching.py` | `test_sqlite_initialization_rolls_back_and_closes_when_commit_fails` (line 624) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 33 | `tests/test_caching.py` | `test_repeated_sqlite_initialization_is_safe` (line 654) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 34 | `tests/test_caching.py` | `test_legacy_migration_imports_supported_values_and_maps_filename` (line 668) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 35 | `tests/test_caching.py` | `test_legacy_migration_is_idempotent_and_existing_rows_win` (line 699) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 36 | `tests/test_caching.py` | `test_missing_legacy_source_does_not_create_database_or_marker` (line 729) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 37 | `tests/test_caching.py` | `test_legacy_migration_quarantines_corrupt_source_without_marker` (line 738) | 2 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 38 | `tests/test_caching.py` | `test_legacy_migration_preserves_unsupported_source_for_retry` (line 752) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 39 | `tests/test_caching.py` | `test_legacy_migration_rolls_back_and_can_retry_after_partial_insert_failure` (line 770) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 40 | `tests/test_caching.py` | `test_legacy_migration_rolls_back_and_can_retry_after_marker_insert_failure` (line 822) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 41 | `tests/test_caching.py` | `test_legacy_migration_rolls_back_and_can_retry_after_commit_failure` (line 878) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 42 | `tests/test_caching.py` | `test_legacy_migration_is_safe_for_concurrent_sources` (line 917) | 2 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 43 | `tests/test_caching.py` | `test_rebuild_function_cache_from_sqlite` (line 948) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 44 | `tests/test_caching.py` | `test_rebuild_function_cache_from_sqlite_is_empty_without_rows` (line 979) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 45 | `tests/test_caching.py` | `test_load_function_cache_migrates_legacy_json_through_public_path` (line 986) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 46 | `tests/test_caching.py` | `test_load_function_cache_missing_function_returns_empty_and_builds_backend` (line 1018) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 47 | `tests/test_caching.py` | `test_load_function_cache_reads_sqlite_authoritatively` (line 1032) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 48 | `tests/test_caching.py` | `test_load_function_cache_memoizes_and_preserves_mutations` (line 1049) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 49 | `tests/test_caching.py` | `test_get_column_cache_returns_existing_bucket_identity` (line 1063) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 50 | `tests/test_caching.py` | `test_get_column_cache_creates_missing_bucket` (line 1077) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 51 | `tests/test_caching.py` | `test_get_column_cache_preserves_explicit_none_value` (line 1095) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 52 | `tests/test_caching.py` | `test_get_column_cache_missing_function_creates_empty_bucket` (line 1113) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 53 | `tests/test_caching.py` | `test_load_function_cache_records_baseline_matching_loaded_state` (line 1139) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 54 | `tests/test_caching.py` | `test_baseline_is_deep_copy_and_survives_nested_mutation` (line 1162) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 55 | `tests/test_caching.py` | `test_separate_functions_have_separate_baselines` (line 1191) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 56 | `tests/test_caching.py` | `test_save_persists_added_and_changed_entries` (line 1221) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | REDUNDANT | subset of test_save_persists_added_changed_and_removed_entries |
| 57 | `tests/test_caching.py` | `test_save_detects_nested_mutation_and_writes_only_changed_entries` (line 1250) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 58 | `tests/test_caching.py` | `test_save_advances_baseline_after_success` (line 1286) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 59 | `tests/test_caching.py` | `test_save_conflict_update_last_writer_wins_and_disjoint_merge` (line 1306) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 60 | `tests/test_caching.py` | `test_save_function_cache_is_safe_for_concurrent_disjoint_saves` (line 1354) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 61 | `tests/test_caching.py` | `test_save_function_cache_last_committed_writer_wins_same_key_across_processes` (line 1447) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 62 | `tests/test_caching.py` | `test_delete_column_cache_persists_existing_bucket_removal` (line 1517) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 63 | `tests/test_caching.py` | `test_delete_column_cache_stale_manager_preserves_concurrent_additions` (line 1540) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 64 | `tests/test_caching.py` | `test_delete_column_cache_across_processes_preserves_concurrent_addition` (line 1620) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 65 | `tests/test_caching.py` | `test_delete_column_cache_leaves_unrelated_buckets_intact` (line 1662) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 66 | `tests/test_caching.py` | `test_delete_column_cache_leaves_unrelated_function_intact` (line 1684) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 67 | `tests/test_caching.py` | `test_delete_column_cache_missing_bucket_is_a_no_op` (line 1706) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 68 | `tests/test_caching.py` | `test_delete_column_cache_failed_transaction_is_retryable` (line 1720) | 1 | CacheManager SQLite cache: round-trip, diffed save, transactions, legacy migration, concurrency, delete | STRONG |  |
| 69 | `tests/test_cleaning.py` | `test_public_cleaning_imports_use_the_bundled_cache_manager` (line 13) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 70 | `tests/test_cleaning.py` | `test_basedata_core_column_transformations_preserve_subclass_and_cache` (line 23) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | ADEQUATE | rename_all_DOTS/drop_by_substring/move_column; no immutability |
| 71 | `tests/test_cleaning.py` | `test_basedata_text_list_reshape_and_imputation_helpers` (line 43) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | ADEQUATE | extract_keywords/split_list_objects/melt_transform_pivot/fill_missing; no immutability |
| 72 | `tests/test_cleaning.py` | `test_save_to_json_writes_local_output` (line 76) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | ADEQUATE | save_to_json defaults only |
| 73 | `tests/test_cleaning.py` | `test_basedata_boundary_errors_and_inplace_return` (line 83) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 74 | `tests/test_cleaning.py` | `test_json_and_csv_constructors_read_local_files` (line 95) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 75 | `tests/test_cleaning.py` | `test_file_constructors_raise_for_missing_paths` (line 112) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 76 | `tests/test_cleaning.py` | `test_impute_by_language_missing_reference_returns_before_optional_import` (line 119) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | WEAK | .equals() is the only value assertion (S-1/§5.2) |
| 77 | `tests/test_cleaning.py` | `test_optional_integration_reports_missing_dependency_at_method_use` (line 129) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 78 | `tests/test_cleaning.py` | `test_optional_categorization_reports_missing_dependency_at_method_use` (line 137) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 79 | `tests/test_cleaning.py` | `test_translate_conditional_safe_partition_does_not_import_deep_translator` (line 149) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 80 | `tests/test_cleaning.py` | `test_translate_conditional_missing_langdetect_raises_documented_import_error` (line 188) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 81 | `tests/test_cleaning.py` | `test_save_to_json_append_keeps_existing_rows_with_list_columns` (line 207) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 82 | `tests/test_cleaning.py` | `test_hierarchy_methods_support_named_multi_and_duplicate_indexes` (line 232) | 3 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 83 | `tests/test_cleaning.py` | `test_save_to_json_append_deduplicates_plain_columns_without_json_keys` (line 262) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 84 | `tests/test_cleaning.py` | `test_fill_missing_rejects_unknown_strategy` (line 278) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 85 | `tests/test_cleaning.py` | `test_save_to_json_append_refuses_to_overwrite_unreadable_file` (line 285) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 86 | `tests/test_cleaning.py` | `test_save_to_json_requires_file_path` (line 295) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 87 | `tests/test_cleaning.py` | `test_save_to_sql_rejects_invalid_arguments_before_connecting` (line 312) | 6 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 88 | `tests/test_cleaning.py` | `test_fill_missing_min_samples_and_fallback_global_reproduction` (line 330) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 89 | `tests/test_cleaning.py` | `test_fill_missing_validates_min_samples` (line 379) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 90 | `tests/test_cleaning.py` | `test_fill_missing_hierarchical_fallthrough_multi_level` (line 395) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 91 | `tests/test_cleaning.py` | `test_fill_missing_all_strategies_with_fallbacks` (line 415) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 92 | `tests/test_cleaning.py` | `test_fill_missing_all_nan_column` (line 438) | 1 | BaseData/JsonFile/CsvFile class API, columns/text/io helpers, fill_missing, save_to_sql validation | STRONG |  |
| 93 | `tests/test_doc_drift.py` | `test_docstrings_and_stubs_are_in_sync` (line 15) | 1 | docstring/stub synchronization, typing artifacts, runtime inspect signatures | STRONG |  |
| 94 | `tests/test_doc_drift.py` | `test_package_typing_artifacts_exist` (line 25) | 1 | docstring/stub synchronization, typing artifacts, runtime inspect signatures | STRONG |  |
| 95 | `tests/test_doc_drift.py` | `test_runtime_inspect_signature_and_help_preserved` (line 31) | 1 | docstring/stub synchronization, typing artifacts, runtime inspect signatures | STRONG |  |
| 96 | `tests/test_enrichment.py` | `test_default_providers_satisfy_the_protocols` (line 99) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | WEAK | asserts the test's own fakes, not production defaults |
| 97 | `tests/test_enrichment.py` | `test_translate_categorical_column_accepts_a_plain_provider` (line 110) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 98 | `tests/test_enrichment.py` | `test_translate_skips_and_does_not_cache_empty_translations` (line 122) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 99 | `tests/test_enrichment.py` | `test_translate_batch_is_used_in_save_every_chunks` (line 133) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 100 | `tests/test_enrichment.py` | `test_default_google_provider_uses_one_translator_per_thread` (line 145) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 101 | `tests/test_enrichment.py` | `test_rate_limited_map_runs_calls_concurrently` (line 171) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | ADEQUATE | real threads + Barrier; timing-based |
| 102 | `tests/test_enrichment.py` | `test_rate_limited_map_spaces_call_starts` (line 181) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 103 | `tests/test_enrichment.py` | `test_rate_limited_map_returns_exceptions_in_place` (line 198) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 104 | `tests/test_enrichment.py` | `test_translate_conditional_column_sampling_is_reproducible` (line 217) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 105 | `tests/test_enrichment.py` | `test_translate_conditional_column_translates_only_foreign_partitions` (line 246) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 106 | `tests/test_enrichment.py` | `test_translate_conditional_column_accepts_a_generator` (line 265) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | CRITICAL | NO ASSERTION (§4 A-1) |
| 107 | `tests/test_enrichment.py` | `test_fill_missing_coordinates_accepts_a_plain_provider` (line 281) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 108 | `tests/test_enrichment.py` | `test_geocoding_errors_are_not_cached` (line 308) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 109 | `tests/test_enrichment.py` | `test_convert_to_usd_downloads_once_per_currency` (line 333) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 110 | `tests/test_enrichment.py` | `test_convert_to_usd_does_not_cache_provider_failures` (line 357) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 111 | `tests/test_enrichment.py` | `test_yfinance_rate_source_computes_yearly_means_from_one_download` (line 373) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 112 | `tests/test_enrichment.py` | `test_cached_map_checkpoints_skips_and_retries_failures` (line 398) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | ADEQUATE | asserts internal checkpoint/save call counts |
| 113 | `tests/test_enrichment.py` | `test_cached_map_multi_bucket_requires_every_bucket` (line 429) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 114 | `tests/test_enrichment.py` | `test_cached_map_batch_failure_leaves_the_chunk_uncached` (line 447) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 115 | `tests/test_enrichment.py` | `test_cached_map_rejects_batches_with_the_wrong_length` (line 462) | 1 | provider protocols, cached-lookup engine, translation/geocoding/currency providers | STRONG |  |
| 116 | `tests/test_equivalence.py` | `test_extract_keywords_literal_matches_legacy` (line 194) | 24 | optimized implementations vs 0.3.0 legacy and brute-force references | STRONG |  |
| 117 | `tests/test_equivalence.py` | `test_extract_keywords_regex_matches_legacy` (line 212) | 18 | optimized implementations vs 0.3.0 legacy and brute-force references | STRONG |  |
| 118 | `tests/test_equivalence.py` | `test_extract_keywords_repeated_calls_into_existing_column_match_legacy` (line 224) | 6 | optimized implementations vs 0.3.0 legacy and brute-force references | STRONG |  |
| 119 | `tests/test_equivalence.py` | `test_extract_keywords_aho_corasick_and_regex_paths_agree` (line 237) | 3 | optimized implementations vs 0.3.0 legacy and brute-force references | CONDITIONAL | importorskip('ahocorasick'); 3 cases skip in default CI |
| 120 | `tests/test_equivalence.py` | `test_extract_keywords_overlapping_keywords_respect_priority` (line 248) | 1 | optimized implementations vs 0.3.0 legacy and brute-force references | STRONG |  |
| 121 | `tests/test_equivalence.py` | `test_outliers_match_a_brute_force_reference` (line 333) | 4 | optimized implementations vs 0.3.0 legacy and brute-force references | STRONG |  |
| 122 | `tests/test_equivalence.py` | `test_handle_and_drop_outliers_match_legacy` (line 350) | 16 | optimized implementations vs 0.3.0 legacy and brute-force references | CONDITIONAL | skipif pandas<3; 16 cases skip on pandas 2 |
| 123 | `tests/test_equivalence.py` | `test_outliers_match_legacy_with_categorical_hierarchy` (line 365) | 1 | optimized implementations vs 0.3.0 legacy and brute-force references | CONDITIONAL | skipif pandas<3; 1 case skips on pandas 2 |
| 124 | `tests/test_equivalence.py` | `test_outlier_masks_do_not_merge` (line 375) | 1 | optimized implementations vs 0.3.0 legacy and brute-force references | GUARD | HO-13 no-merge guard |
| 125 | `tests/test_fill_missing_from.py` | `test_fill_missing_from_basic_imputation` (line 10) | 1 | fill_missing_from reference imputation, leakage, match_cols, validation, index | STRONG |  |
| 126 | `tests/test_fill_missing_from.py` | `test_fill_missing_from_prevents_statistical_leakage` (line 69) | 1 | fill_missing_from reference imputation, leakage, match_cols, validation, index | STRONG |  |
| 127 | `tests/test_fill_missing_from.py` | `test_fill_missing_from_hierarchical_fallthrough_and_min_samples` (line 98) | 1 | fill_missing_from reference imputation, leakage, match_cols, validation, index | STRONG |  |
| 128 | `tests/test_fill_missing_from.py` | `test_fill_missing_from_match_cols` (line 148) | 1 | fill_missing_from reference imputation, leakage, match_cols, validation, index | STRONG |  |
| 129 | `tests/test_fill_missing_from.py` | `test_fill_missing_from_validation` (line 193) | 1 | fill_missing_from reference imputation, leakage, match_cols, validation, index | ADEQUATE | FF-6 partial: no empty-string match_cols, no targets variants |
| 130 | `tests/test_fill_missing_from.py` | `test_fill_missing_from_edge_cases` (line 269) | 1 | fill_missing_from reference imputation, leakage, match_cols, validation, index | ADEQUATE | docstring claims unhashable values; not tested |
| 131 | `tests/test_fill_missing_from.py` | `test_fill_missing_from_index_preservation` (line 301) | 1 | fill_missing_from reference imputation, leakage, match_cols, validation, index | STRONG |  |
| 132 | `tests/test_fill_missing_from.py` | `test_fill_missing_from_basedata_and_contracts` (line 320) | 1 | fill_missing_from reference imputation, leakage, match_cols, validation, index | ADEQUATE | FF-24/FF-25 partial: no match_cols stats, no inplace+stats |
| 133 | `tests/test_fill_missing_from.py` | `test_existing_fill_missing_remains_unchanged` (line 344) | 1 | fill_missing_from reference imputation, leakage, match_cols, validation, index | ADEQUATE | overlaps test_cleaning fill_missing cases |
| 134 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_returns_median_levels_and_preserves_source` (line 25) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 135 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_supports_mean_multiple_targets_and_string_hierarchy` (line 75) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 136 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_mode_matches_tie_breaking_and_normalizes_mod` (line 99) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | ADEQUATE | tie-break contradicts README:579 |
| 137 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_handles_null_values_and_empty_groups` (line 120) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 138 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_returns_fixed_empty_schema_for_invalid_inputs` (line 138) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 139 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_does_not_change_fill_missing_behavior` (line 159) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 140 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_supports_explicit_dataframe_and_dict_outputs` (line 178) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 141 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_supports_explicit_basedata_family_outputs` (line 212) | 2 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 142 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_preserves_custom_basedata_subclass_by_default` (line 231) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 143 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_rejects_invalid_output_type_before_aggregation` (line 246) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 144 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_returns_requested_type_for_empty_results` (line 257) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 145 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_has_no_nested_functions_or_apply_lambda` (line 272) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | GUARD | AST guard; allowed by §4 A-3 |
| 146 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_deduplicates_hierarchy_columns_without_adding_levels` (line 292) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 147 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_rejects_target_hierarchy_overlap_before_aggregation` (line 322) | 2 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 148 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_aggregates_all_mode_targets_once_per_level` (line 344) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | WEAK | asserts internal groupby call count (§4 A-3) |
| 149 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_mode_allows_hierarchy_column_named_count` (line 376) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 150 | `tests/test_hierarchical_stats.py` | `test_generic_output_helpers_are_schema_independent` (line 393) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | WEAK | tests private helpers directly (§4 A-3) |
| 151 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_supports_ordered_multiple_strategies` (line 409) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 152 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_rejects_non_string_strategy_values_before_aggregation` (line 460) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 153 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_mode_has_no_melt_and_keeps_null_groups` (line 474) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | GUARD | no-melt guard + behavior |
| 154 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_default_fallback_requires_data_signature` (line 493) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 155 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_propagates_internal_constructor_errors` (line 509) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 156 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_all_output_types_keep_multi_strategy_schema` (line 525) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 157 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_mode_empty_valid_values_returns_empty_rows` (line 544) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 158 | `tests/test_hierarchical_stats.py` | `test_get_hierarchical_stats_falls_back_to_dataframe_for_incompatible_default_subclass` (line 556) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 159 | `tests/test_hierarchical_stats.py` | `test_hierarchy_methods_keep_existing_return_contract_when_stats_disabled` (line 579) | 3 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 160 | `tests/test_hierarchical_stats.py` | `test_hierarchy_methods_skip_stats_calculation_when_disabled` (line 605) | 6 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 161 | `tests/test_hierarchical_stats.py` | `test_hierarchy_methods_return_stats_for_copy_and_inplace_modes` (line 633) | 3 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 162 | `tests/test_hierarchical_stats.py` | `test_hierarchy_stats_are_extracted_before_drop_outliers` (line 666) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 163 | `tests/test_hierarchical_stats.py` | `test_hierarchy_stats_are_extracted_before_progressive_fill` (line 683) | 1 | get_hierarchical_stats schema/strategies/output types; hierarchy method stats contracts | STRONG |  |
| 164 | `tests/test_inplace_deprecation.py` | `test_early_exits_return_an_independent_copy` (line 50) | 21 | API-02 new-object default; inplace=True mutation/None; warning contracts | STRONG |  |
| 165 | `tests/test_inplace_deprecation.py` | `test_early_exit_with_stats_returns_a_copy` (line 66) | 1 | API-02 new-object default; inplace=True mutation/None; warning contracts | WEAK | .equals() is the only value assertion (§5.2) |
| 166 | `tests/test_inplace_deprecation.py` | `test_inplace_true_still_mutates_and_returns_none` (line 76) | 1 | API-02 new-object default; inplace=True mutation/None; warning contracts | STRONG |  |
| 167 | `tests/test_inplace_deprecation.py` | `test_every_inplace_path_is_silent_and_preserves_behavior` (line 102) | 5 | API-02 new-object default; inplace=True mutation/None; warning contracts | ADEQUATE | unreadable <lambda>-False-True IDs |
| 168 | `tests/test_inplace_deprecation.py` | `test_inplace_false_and_default_do_not_warn` (line 125) | 1 | API-02 new-object default; inplace=True mutation/None; warning contracts | STRONG |  |
| 169 | `tests/test_inplace_deprecation.py` | `test_split_list_objects_inplace_explode_reshapes_the_original` (line 134) | 1 | API-02 new-object default; inplace=True mutation/None; warning contracts | STRONG |  |
| 170 | `tests/test_inplace_deprecation.py` | `test_melt_transform_pivot_result_keeps_the_cache_manager` (line 147) | 1 | API-02 new-object default; inplace=True mutation/None; warning contracts | STRONG |  |
| 171 | `tests/test_inplace_deprecation.py` | `test_inplace_results_are_not_aliases` (line 156) | 1 | API-02 new-object default; inplace=True mutation/None; warning contracts | STRONG |  |
| 172 | `tests/test_inplace_deprecation.py` | `test_inplace_on_missing_optional_dependency_still_raises` (line 169) | 1 | API-02 new-object default; inplace=True mutation/None; warning contracts | STRONG |  |
| 173 | `tests/test_integrations.py` | `test_translate_categorical_column_translates_each_unique_value_once` (line 112) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 174 | `tests/test_integrations.py` | `test_fill_missing_coordinates_shortens_queries_and_caches_misses` (line 168) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 175 | `tests/test_integrations.py` | `test_convert_to_usd_looks_back_and_caches_missing_years` (line 251) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 176 | `tests/test_integrations.py` | `test_extract_entities_nlp_default_disable_reaches_both_pipe_calls` (line 298) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 177 | `tests/test_integrations.py` | `test_extract_entities_nlp_skips_unused_pipes_and_reuses_cache` (line 338) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 178 | `tests/test_integrations.py` | `test_extract_entities_nlp_custom_disable_reaches_both_pipe_calls` (line 381) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 179 | `tests/test_integrations.py` | `test_extract_entities_nlp_normalizes_single_string_and_none` (line 398) | 2 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | ADEQUATE | unreadable expected0/expected1 IDs |
| 180 | `tests/test_integrations.py` | `test_extract_entities_nlp_rejects_required_disable_before_spacy_load` (line 411) | 5 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 181 | `tests/test_integrations.py` | `test_extract_entities_nlp_reports_all_required_disabled_components` (line 424) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 182 | `tests/test_integrations.py` | `test_extract_entities_nlp_warns_for_unknown_disable_and_continues` (line 435) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 183 | `tests/test_integrations.py` | `test_extract_entities_nlp_different_disable_configs_do_not_reuse_cache` (line 450) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 184 | `tests/test_integrations.py` | `test_extract_entities_nlp_different_models_do_not_reuse_cache` (line 461) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 185 | `tests/test_integrations.py` | `test_extract_entities_nlp_equivalent_disable_configs_reuse_cache` (line 474) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | ADEQUATE | asserts pipe-call count |
| 186 | `tests/test_integrations.py` | `test_extract_entities_nlp_noisy_terms_filters_matched_terms` (line 485) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 187 | `tests/test_integrations.py` | `test_extract_entities_nlp_signature_exposes_noisy_terms_only` (line 504) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 188 | `tests/test_integrations.py` | `test_extract_entities_nlp_rejects_the_noisey_terms_spelling` (line 510) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 189 | `tests/test_integrations.py` | `test_free_enrichment_extract_entities_nlp_rejects_noisey_terms_spelling` (line 524) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 190 | `tests/test_integrations.py` | `test_categorize_by_reference_with_real_pyahocorasick` (line 541) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | CONDITIONAL | importorskip('ahocorasick') |
| 191 | `tests/test_integrations.py` | `test_save_to_sql_with_real_sqlalchemy_and_sqlite` (line 557) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | CONDITIONAL | importorskip('sqlalchemy') |
| 192 | `tests/test_integrations.py` | `test_save_to_sql_propagates_database_errors` (line 580) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | CONDITIONAL | importorskip('sqlalchemy') |
| 193 | `tests/test_integrations.py` | `test_extract_entities_nlp_raises_for_bad_configuration` (line 597) | 1 | offline enrichment integrations via fake modules; real extras; NLP disable/cache identity | STRONG |  |
| 194 | `tests/test_profile.py` | `test_public_entry_points` (line 89) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 195 | `tests/test_profile.py` | `test_profiling_does_not_modify_input` (line 114) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 196 | `tests/test_profile.py` | `test_report_structure_and_access_patterns` (line 134) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 197 | `tests/test_profile.py` | `test_output_type_parameter` (line 177) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 198 | `tests/test_profile.py` | `test_column_selection_and_errors` (line 210) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 199 | `tests/test_profile.py` | `test_missing_values_and_proportions` (line 232) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 200 | `tests/test_profile.py` | `test_duplicate_rows_counting_semantics` (line 259) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 201 | `tests/test_profile.py` | `test_duplicate_rows_with_unhashable_cells` (line 281) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 202 | `tests/test_profile.py` | `test_numeric_statistics` (line 298) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | ADEQUATE | expected via np/pandas; iqr only non-null |
| 203 | `tests/test_profile.py` | `test_categorical_and_text_statistics` (line 324) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 204 | `tests/test_profile.py` | `test_boolean_statistics` (line 347) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 205 | `tests/test_profile.py` | `test_datetime_statistics` (line 363) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | ADEQUATE | substring match on min/max |
| 206 | `tests/test_profile.py` | `test_mixed_and_other_statistics` (line 380) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | WEAK | version-dependent inferred_type label (§4 A-9) |
| 207 | `tests/test_profile.py` | `test_nullable_dtypes` (line 398) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 208 | `tests/test_profile.py` | `test_empty_dataframe_edge_cases` (line 426) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 209 | `tests/test_profile.py` | `test_all_missing_column_edge_cases` (line 477) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 210 | `tests/test_profile.py` | `test_single_row_statistics` (line 510) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 211 | `tests/test_profile.py` | `test_duplicate_column_names_handling` (line 523) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | WEAK | does not assert rep.columns / to_dict keys; passes despite PD-03 |
| 212 | `tests/test_profile.py` | `test_clean_scalar_bool_before_int` (line 535) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 213 | `tests/test_profile.py` | `test_timedelta_columns_and_clean_scalar` (line 558) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 214 | `tests/test_profile.py` | `test_categorical_pd_categorical` (line 583) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 215 | `tests/test_profile.py` | `test_tz_aware_datetime` (line 596) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 216 | `tests/test_profile.py` | `test_contract_stability_key_sets` (line 609) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 217 | `tests/test_profile.py` | `test_contract_stability_value_types` (line 671) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |
| 218 | `tests/test_profile.py` | `test_contract_json_dumps_mixed_dataframe` (line 743) | 1 | profile report schema, kinds, statistics, output types, JSON serialization | STRONG |  |


---

## C. Test Quality Findings

Each finding has a unique identifier, severity, exact location, intended contract, what is wrong, why it is inadequate, a realistic passing-incorrect-implementation example where applicable, and a Phase 2 recommendation.

### TQ-01 — Critical — Test with no assertion

- **Location:** `tests/test_enrichment.py::test_translate_conditional_column_accepts_a_generator`, lines 265–273.
- **Intended contract:** `translate_conditional_column` accepts a NumPy `Generator` as `random_state` (`README.md:726–731`; `bynat/cleaning/base.py:660`; `bynat/cleaning/enrich/translate.py:188, 265–268`).
- **What is wrong:** the test body only calls the method. There is no `assert`, `pytest.raises`, `pytest.warns`, or warning-escalation helper.
- **Why inadequate:** it passes whether or not the generator path works, whether or not any translation happens, and whether the method returns the frame unchanged. It violates `docs/TESTING_STANDARDS.md` §4 A-1.
- **Incorrect implementation that still passes:** delete the `isinstance(random_state, (np.random.Generator, np.random.RandomState))` branch and treat the generator as a seed (`np.random.default_rng(generator)` would raise, but a silent `random_state = 0` fallback would pass); or return `df.copy()` without translating.
- **Evidence:** AST scan `scan_assertions.py` → `NO ASSERTION: test_enrichment.py::test_translate_conditional_column_accepts_a_generator (line 265)`. `docs/TESTING_STANDARDS.md` §12 Phase 0 lists this exact test as the open "cannot fail" item.
- **Phase 2 recommendation:** inject a `DictTranslator`, assert the translated values and the provider call sequence, and keep the generator path (e.g. `assert result["t"].tolist() == [...]` plus `translator.calls`).

### TQ-02 — High — Provider protocol test exercises the test's own fakes

- **Location:** `tests/test_enrichment.py::test_default_providers_satisfy_the_protocols`, lines 99–102.
- **Intended contract:** provider protocols `Translator`/`Geocoder`/`RateSource` and their documented defaults `GoogleTranslatorProvider`/`NominatimGeocoder`/`YFinanceRateSource` (`README.md:616–624`; `bynat/cleaning/enrich/providers.py`).
- **What is wrong:** the test asserts `issubclass(DictTranslator, Translator)`, `issubclass(DictGeocoder, Geocoder)`, `issubclass(FakeRates, RateSource)`. All three classes are defined in the test file. `runtime_checkable` `issubclass` only checks method presence.
- **Why inadequate:** it verifies the test doubles, not the production defaults. The test name claims "default providers".
- **Incorrect implementation that still passes:** delete `NominatimGeocoder`, rename `GoogleTranslatorProvider.translate`, or make `YFinanceRateSource.yearly_rates` private — the test still passes.
- **Phase 2 recommendation:** assert `issubclass(GoogleTranslatorProvider, Translator)`, `issubclass(NominatimGeocoder, Geocoder)`, `issubclass(YFinanceRateSource, RateSource)`, and pin the documented `bynat.cleaning.enrich` export path.

### TQ-03 — High — Positive-path input immutability is not asserted

- **Location:** `tests/test_cleaning.py::test_basedata_text_list_reshape_and_imputation_helpers` (43–73), `tests/test_cleaning.py::test_fill_missing_*` (330–446), all of `tests/test_fill_missing_from.py`, and all of `tests/test_equivalence.py`.
- **Intended contract:** `docs/TESTING_STANDARDS.md` §6.1 S-1 and §6.10 ML-1 — "Every frame-to-frame transformation returns a new object; the input is unchanged."
- **What is wrong:** only early-exit paths are checked for copy semantics (`tests/test_inplace_deprecation.py::test_early_exits_return_an_independent_copy`), plus `test_accessor.py:55`, `test_hierarchical_stats.py:70`, and `test_profile.py:129`. `fill_missing`, `fill_missing_from`, `handle_outliers`, `drop_outliers`, `extract_keywords`, `split_list_objects`, `melt_transform_pivot`, `categorize_by_reference`, and the enrichment methods never assert `before = df.copy(deep=True)` / `assert_frame_equal(df, before)` on their happy path.
- **Why inadequate:** a regression that mutates the caller's frame in place on the normal path is invisible to the suite.
- **Incorrect implementation that still passes:** `result = df; result[col] = ...; return result` for any of the listed methods.
- **Phase 2 recommendation:** add the S-1 immutability pair to each positive-path test, or add one parametrized property-style test covering all frame-to-frame transformations.

### TQ-04 — Medium — Internal `groupby` call count asserted

- **Location:** `tests/test_hierarchical_stats.py::test_get_hierarchical_stats_aggregates_all_mode_targets_once_per_level`, lines 344–373 (assertion at 372).
- **Intended contract:** `docs/TESTING_STANDARDS.md` §4 A-3 — private state and internal call counts are not contracts unless the contract is about them.
- **What is wrong:** `assert len(groupby_calls) == 4` pins the number of `pd.DataFrame.groupby` calls.
- **Why inadequate:** a semantically identical rewrite using 2 or 8 `groupby` calls fails even though the documented schema and values are unchanged.
- **Phase 2 recommendation:** keep the `target_column` ordering assertion; move the call-count claim to a documented performance-invariant guard with a comment naming the invariant, or drop it.

### TQ-05 — Medium — Private helpers tested directly

- **Location:** `tests/test_hierarchical_stats.py::test_generic_output_helpers_are_schema_independent`, lines 393–406.
- **Intended contract:** §4 A-3.
- **What is wrong:** the test imports and calls `_HIERARCHICAL_STATS_COLUMNS`, `_convert_output`, and `_validate_output_type` from `bynat.cleaning.Cleaning`.
- **Why inadequate:** it pins private module structure rather than public behavior. The public rejection path is already covered by `test_get_hierarchical_stats_rejects_invalid_output_type_before_aggregation`.
- **Phase 2 recommendation:** drop the direct private-helper calls and keep the public `output_type` rejection coverage.

### TQ-06 — Medium — `.equals()` is the only value assertion

- **Locations:** `tests/test_inplace_deprecation.py::test_early_exit_with_stats_returns_a_copy`, lines 66–73 (`assert result.equals(frame)`); `tests/test_cleaning.py::test_impute_by_language_missing_reference_returns_before_optional_import`, lines 119–126 (`assert result.equals(frame)`).
- **Intended contract:** `docs/TESTING_STANDARDS.md` §5.2 — `DataFrame.equals` MUST NOT be the only assertion (it ignores the index name).
- **Why inadequate:** a result with a changed index name or index type passes.
- **Incorrect implementation that still passes:** `result.index = result.index.rename("drift")`.
- **Phase 2 recommendation:** use `pd.testing.assert_frame_equal`.

### TQ-07 — Medium — Duplicate-column report mapping not asserted

- **Location:** `tests/test_profile.py::test_duplicate_column_names_handling`, lines 523–533.
- **Intended contract:** `README.md` §"Working with a report" — `columns` maps column name → `ColumnProfile`; `to_dict()["columns"]`.
- **What is wrong:** the test asserts `dataset.column_count`, `column_list`, and `to_dataframe()`, but never `len(rep.columns)` or `to_dict()["columns"]`. It passes while one of the two duplicate columns is silently dropped from the mapping (see PD-03).
- **Phase 2 recommendation:** assert the documented mapping behavior explicitly, or pin the limitation if it is intended.

### TQ-08 — Medium — Version-dependent pandas label asserted

- **Location:** `tests/test_profile.py::test_mixed_and_other_statistics`, lines 380–395 (assertion at 386).
- **Intended contract:** §4 A-9 — no version overfit.
- **What is wrong:** `assert col.inferred_type in ("mixed", "mixed-integer")` depends on the `pandas.api.types.infer_dtype` label, which has changed across pandas versions.
- **Phase 2 recommendation:** assert `col.kind == "other"` and a stable statistic (e.g. `col.stats["top_frequency"] == 2`) instead of the inferred label.

### TQ-09 — Low — Expected values computed with the same library

- **Location:** `tests/test_profile.py::test_numeric_statistics`, lines 298–321.
- **What is wrong:** `stats["mean"] == float(np.mean(data))`, `stats["median"] == float(np.median(data))`, `stats["std"] == pytest.approx(float(pd.Series(data).std()))` re-implement the aggregation with the same library the implementation uses; `stats["iqr"] is not None` is a non-null check, not a value check.
- **Why inadequate:** a wrong `iqr` or a wrong `std` ddof passes.
- **Phase 2 recommendation:** hand-compute mean/median/std for the fixed 6-value input and assert `iqr == 10.0`.

### TQ-10 — Low — Timestamp assertions by substring

- **Location:** `tests/test_profile.py::test_datetime_statistics`, lines 363–377.
- **What is wrong:** `assert "2024-01-01" in stats["min"]` accepts any string containing that date.
- **Phase 2 recommendation:** assert the exact ISO string.

### TQ-11 — Low — Redundant test

- **Location:** `tests/test_caching.py::test_save_persists_added_and_changed_entries`, lines 1221–1247.
- **What is wrong:** it is a strict subset of `test_save_persists_added_changed_and_removed_entries` (lines 36–66), which additionally covers removal. It adds no independent regression protection.
- **Phase 2 recommendation:** fold the added/changed case into the comprehensive test or add a distinct behavior.

### TQ-12 — Low — Unreadable parametrize IDs

- **Locations:** `tests/test_accessor.py:153–160` → `test_supported_classes_construct_without_warning[<lambda>0..2]`; `tests/test_inplace_deprecation.py:86–101` → `test_every_inplace_path_is_silent_and_preserves_behavior[<lambda>-False-True]`, `[<lambda>-True-True]`, `[<lambda>-False-False0..2]`; `tests/test_integrations.py:394–397` → `test_extract_entities_nlp_normalizes_single_string_and_none[ner-expected0]`, `[None-expected1]`.
- **Intended contract:** §8.2 — "Parametrize IDs MUST be readable: use `pytest.param(value, id="...")`."
- **Phase 2 recommendation:** add explicit `id=` values.

### TQ-13 — Low — 14 unused `tmp_path` fixtures

- **Locations (exact list, 14 functions):**
  - `tests/test_cleaning.py::test_fill_missing_min_samples_and_fallback_global_reproduction`
  - `tests/test_cleaning.py::test_fill_missing_hierarchical_fallthrough_multi_level`
  - `tests/test_cleaning.py::test_fill_missing_all_strategies_with_fallbacks`
  - `tests/test_cleaning.py::test_fill_missing_all_nan_column`
  - `tests/test_fill_missing_from.py::test_fill_missing_from_basic_imputation`
  - `tests/test_fill_missing_from.py::test_fill_missing_from_prevents_statistical_leakage`
  - `tests/test_fill_missing_from.py::test_fill_missing_from_hierarchical_fallthrough_and_min_samples`
  - `tests/test_fill_missing_from.py::test_fill_missing_from_match_cols`
  - `tests/test_fill_missing_from.py::test_fill_missing_from_validation`
  - `tests/test_fill_missing_from.py::test_fill_missing_from_edge_cases`
  - `tests/test_fill_missing_from.py::test_fill_missing_from_index_preservation`
  - `tests/test_fill_missing_from.py::test_existing_fill_missing_remains_unchanged`
  - `tests/test_hierarchical_stats.py::test_get_hierarchical_stats_has_no_nested_functions_or_apply_lambda`
  - `tests/test_hierarchical_stats.py::test_generic_output_helpers_are_schema_independent`
- **Intended contract:** §12 Phase 0 — "Remove the unused `tmp_path` fixtures (14 test functions) or use them." The exact count 14 is confirmed by AST scan.
- **Phase 2 recommendation:** remove the parameter or use it.

### TQ-14 — Low — Unnecessary `DeprecationWarning` suppression

- **Locations:** `tests/test_accessor.py:60–62` and `177–179`; `tests/test_inplace_deprecation.py:13–18` (`_frame` helper) plus inline uses at 54–56, 79–81, 108–110, 128–130, 138–140, 159–161.
- **What is wrong:** `warnings.simplefilter("ignore", DeprecationWarning)` wraps `BaseData(...)` construction. A probe (`probe_defects.py`, section 1) shows `BaseData({"a": [1]}, cache_dir=...)` emits **no** warning, so the suppression is unnecessary. §4 A-6 rejects hiding warnings.
- **Why inadequate:** a future regression that makes construction emit a `DeprecationWarning` would be silently absorbed.
- **Phase 2 recommendation:** remove the unnecessary ignore wrappers; keep escalation (`simplefilter("error", ...)`) where the warning contract is the subject.

### TQ-15 — Low — Brittle exact `PRAGMA` tuples

- **Location:** `tests/test_caching.py::test_sqlite_schema_has_required_tables_columns_keys_and_index`, lines 460–499.
- **What is wrong:** asserts exact `PRAGMA table_info` tuples (column order, PK flags, index columns).
- **Why inadequate:** any schema refactor that preserves behavior fails the test. Cache internals are allowed by §4 A-3, but the assertion is stricter than the contract.
- **Phase 2 recommendation:** assert columns/indexes exist by name, or comment the invariant.

### TQ-16 — Low — Thread-scheduling test

- **Location:** `tests/test_enrichment.py::test_rate_limited_map_runs_calls_concurrently`, lines 171–178.
- **What is wrong:** relies on a real `threading.Barrier(3, timeout=5)`; under CI load the barrier can time out.
- **Phase 2 recommendation:** keep, but treat as flake-prone; prefer a deterministic scheduling probe.

### TQ-17 — Low — Docstring claims coverage the body does not provide

- **Location:** `tests/test_fill_missing_from.py::test_fill_missing_from_edge_cases`, lines 269–298.
- **What is wrong:** the docstring says "and unhashable values"; the body tests empty target, no-missing target, all-missing target, and all-null reference column. No unhashable value is exercised.
- **Phase 2 recommendation:** add the unhashable case or correct the docstring.

### TQ-18 — Low — `tests/test_caching.py` exceeds the split threshold

- **Location:** `tests/test_caching.py` (1783 lines).
- **Intended contract:** §8.1 — split when a file exceeds roughly 800 lines.
- **Why inadequate:** the standard records this as a future maintenance item rather than an immediate exception; it is noted here for the Phase 2 plan.
- **Phase 2 recommendation:** split into topic-named files (e.g. `test_caching_concurrency.py`).

### TQ-19 — Medium — `tests/test_doc_drift.py` cannot be collected from a non-root CWD or via the `pytest` console script

- **Location:** `tests/test_doc_drift.py:10` — `from tools.sync_docs import check`.
- **Intended contract:** the suite must be collectable; `docs/TESTING_STANDARDS.md` §8.6 explicitly flags the unresolved import-mode ambiguity.
- **What is wrong:** `tools` is importable only when the repository root is on `sys.path`. `python -m pytest` from the repo root works; the `pytest` console script from the repo root fails; any invocation from another CWD fails.
- **Evidence:**
  - `pytest --collect-only -q` from repo root → `334 tests collected, 1 error`; `ModuleNotFoundError: No module named 'tools'`.
  - `pytest --collect-only -q D:\...\tests` from the scratch dir → `334 tests collected, 1 error`; same error.
  - `python -m pytest --collect-only -q` from repo root → `337 tests collected`.
- **Why inadequate:** the three `test_doc_drift.py` tests are effectively uncollectable under a documented invocation, so the doc-drift gate silently disappears.
- **Phase 2 recommendation:** add `tests/conftest.py` that inserts the repository root into `sys.path` (or set `--import-mode=importlib` and import via a package-relative path), and add a collection smoke test.
---

## D. Public Contract Coverage Gaps

Reference: `README.md` (behavior), `docs/TESTING_STANDARDS.md` §5/§6 (requirement IDs), `bynat/` docstrings (API).

### D.1 Contracts with meaningful test coverage

| Contract area | Requirement IDs / documentation | Primary evidence |
| --- | --- | --- |
| `fill_missing` strategies, `min_samples`, `fallback_global`, hierarchy, aliases, unknown strategy | FM-1…FM-10, FM-12…FM-18, FM-20…FM-22 | `tests/test_cleaning.py:278–446` |
| `fill_missing_from` leakage, reference immutability, hierarchy, `match_cols`, validation, index | FF-1…FF-7, FF-9…FF-12, FF-14…FF-22, FF-26, FF-27 | `tests/test_fill_missing_from.py` (all) |
| Outlier IQR rules, `min_samples` boundary, duplicate index, no-merge guard, equivalence | HO-1…HO-6, HO-8…HO-15, DO-1…DO-5, DO-7, DO-8 | `tests/test_equivalence.py`, `tests/test_cleaning.py:224–259`, `tests/test_hierarchical_stats.py:575–705` |
| `get_hierarchical_stats` schema, strategies, output types, nulls, dedupe, errors | §3.4, README:532–597 | `tests/test_hierarchical_stats.py` (all) |
| `profile` schema, kinds, statistics, output types, JSON | README:274–457, 831–835 | `tests/test_profile.py` (all) |
| `CacheManager` round-trip, diffed save, rollback, legacy migration, concurrency, delete | README:458–526 | `tests/test_caching.py` (all) |
| Accessor registration, cache sharing, signatures, loaders | README:152–236, 663–706 | `tests/test_accessor.py`, `tests/test_doc_drift.py` |
| Enrichment providers, engine, cache semantics | README:599–660 | `tests/test_enrichment.py`, `tests/test_integrations.py` |

### D.2 Contracts with insufficient coverage

| Contract | Missing / weak | Evidence |
| --- | --- | --- |
| `inplace` rejection by shared functions and accessor (S-4/ML-2) | No test asserts `TypeError`; production silently absorbs it | PD-01 |
| Outlier `min_samples` validation (MS-3a) | No test; `fill_missing`/`fill_missing_from` validation tested only | PD-02 |
| `noisey_terms` README alias | No test of the alias; tests assert the opposite | PD-04 |
| `mode` tie-break "first occurrence" (README:579) | Not documented in the test; behavior is alphabetical | PD-05 |
| `save_to_json` `orient` / `force_ascii` / `indent` / `append` variants | Only defaults and one append/dedupe path | `tests/test_cleaning.py:76–80, 207–292`; `tests/test_accessor.py:117–122` |
| `save_to_sql` non-SQLite dialects, `columns_types`, `chunk_size`, `index`, `fast_executemany` | Only SQLite and argument validation | `tests/test_cleaning.py:300–327`; `tests/test_integrations.py:557–594` |
| `read_json` `KeyError` branch | Docstring documents it; untested | `bynat/cleaning/io.py:59–60` |
| Positive paths of `rename_by_substring`, `drop_CLASS_columns`, `align_lat_lng`, `reorder_columns`, `truncate_after_substring` | Only early-exit parametrization | `tests/test_inplace_deprecation.py:22–46` |
| `split_list_objects(remove_source_col=…)`, `cartesian_explode=True` | Never exercised | no occurrence in `tests/` |
| `impute_by_language` positive path | Only the missing-reference early return | `tests/test_cleaning.py:119–126` |
| HO-7 / DO-6: empty-hierarchy warning; missing named hierarchy `KeyError` | Neither asserted | `tests/test_inplace_deprecation.py:38–39` (no warning assertion) |
| FM-23: non-numeric target with numeric strategy | Not tested (hierarchy path and `fallback_global` both raise; no-hierarchy path returns unchanged) | `bynat/cleaning/stats.py:325–330, 367–371` |
| FF-19: target-only non-numeric + all-NaN control | Only the combined non-numeric reference/target case | `tests/test_fill_missing_from.py:254–258` |
| FF-24 / FF-25: `get_hierarchical_stats=True` with `match_cols`; `inplace=True` with stats | Partially covered | `tests/test_fill_missing_from.py:320–341` |
| FF-8: duplicate targets deduplicated | Not tested | `bynat/cleaning/stats.py:546` |
| FM-11a / FF-13a: some target columns missing, others valid | Not tested (only all-missing) | `bynat/cleaning/stats.py:281–292, 557–563` |
| HF-6: null hierarchy keys remain valid groups | Partially (`test_get_hierarchical_stats_handles_null_values_and_empty_groups`) | `tests/test_hierarchical_stats.py:120–135` |
| MS-4: only non-null observations count toward `min_samples` | Implied by tests, never isolated | — |
| `get_hierarchical_stats` non-numeric target with `median`/`mean` | README:578 documents `TypeError`; untested | `bynat/cleaning/stats.py:861–893` |
| `BaseData.clear_cache_for_column` | Only the accessor version is tested | `tests/test_accessor.py:112` |
| `JsonFile` / `CsvFile` positional-path constructors | Only keyword forms tested | `tests/test_cleaning.py:95–116` |
| Duplicate-column profile mapping | Not asserted; defect passes | PD-03, TQ-07 |

### D.3 Contracts without tests

| Contract | Documentation | Note |
| --- | --- | --- |
| `bynat.caching` exports `CacheManager`, `shared_cache_manager`, `CACHE_DIR_ENV_VAR`, `DEFAULT_CACHE_DIR` | README:164–183, 462–467 | §3.4 records this as an open Phase 0 item; confirmed — no test imports `shared_cache_manager`, `CACHE_DIR_ENV_VAR`, or `DEFAULT_CACHE_DIR` |
| `bynat.cleaning.enrich` default `NominatimGeocoder` and module `__all__` | README:176–181 | §3.4 Phase 0 item; confirmed |
| `bynat.cleaning.enrich.__all__`, `bynat.cleaning.profile.__all__` | README:176–181, 863–873 | Not pinned |
| `bynat.cleaning.io` public functions as a documented module path | README:871 | Exercised, never pinned as an import path |
| Property tests (`tests/property/`) | §3.5, §7.6 | Directory does not exist |
| `tests/conftest.py`, marker registration, pytest config | §3.5, §8.5, §8.6, §12 Phase 1 | None exist |
| CI extras matrix for `translation`, `geocoding`, `currency`, `nlp` | §3.1, §9.2 | CI installs only `categorization,sql` |
| Wheel-installed suite run | §9.2, §12 Phase 3 | Not present |

### D.4 Behaviors that are exercised but not actually verified

| Test | Exercises | Does not verify |
| --- | --- | --- |
| `test_translate_conditional_column_accepts_a_generator` | `random_state=np.random.default_rng(3)` path | Anything — no assertion (TQ-01) |
| `test_default_providers_satisfy_the_protocols` | `issubclass` on three test doubles | Production default providers (TQ-02) |
| `test_get_hierarchical_stats_aggregates_all_mode_targets_once_per_level` | Mode aggregation over two targets/two levels | The call count is not a contract (TQ-04) |
| `test_early_exits_return_an_independent_copy` | 21 methods with non-matching arguments | The methods' real transformation behavior |
| `test_save_to_json_append_deduplicates_plain_columns_without_json_keys` | Fast dedupe path | Only that `_dedupe_key` is not called |
| `test_outlier_masks_do_not_merge` | `drop_outliers` | Only that `DataFrame.merge` is not called |
| `test_duplicate_column_names_handling` | `profile` on duplicate columns | The `columns` mapping and `to_dict()` (TQ-07) |
| `test_generic_output_helpers_are_schema_independent` | Private helpers | Public behavior (TQ-05) |

### D.5 Important missing regression and integration scenarios

1. **pandas 2 vs pandas 3 behavior.** `_LEGACY_RELIABLE` (`tests/test_equivalence.py:281–284`) skips 17 legacy-equivalence cases on pandas 2. The suite has no test that fails on pandas 2 and passes on pandas 3 for the null-hierarchy-key fix recorded in `CHANGELOG.md` (0.6.0 "Fixed").
2. **Windows vs Ubuntu.** CI runs both, but no test asserts Windows-specific path/locking behavior; `tests/test_caching.py` concurrency tests use `multiprocessing` `spawn`, which works on both but is not asserted differently.
3. **Wheel-installed run.** No test executes the suite against an installed wheel (Phase 3 item).
4. **Real optional extras.** `translation`, `geocoding`, `currency`, and `nlp` extras are never exercised in CI; only fakes are used. `pytest.importorskip` covers only `categorization` and `sql`.
5. **`inplace` contract on the accessor.** No test asserts the documented "accessor takes no `inplace`" rule.
6. **Outlier `min_samples` invalid input.** No test; the standard itself records the gap (MS-3a).
7. **Cache key normalization.** ML-4 says cache keys are normalized (`1`, `1.0`, `"1"` collide by design) and "tests pin the documented normalization". No test asserts this explicitly; `tests/test_caching.py` tests key *validation*, not normalization collisions.

---

## E. Production Defects

These are separated from test-quality findings. None were modified.

### PD-01 — High — Variadic accessor/shared methods silently absorb `inplace`

- **Affected public contract:** `README.md:667` "Accessor methods take no `inplace` argument"; `docs/TESTING_STANDARDS.md` §6.1 S-4 and §6.10 ML-2 (the standard itself records this as an open Phase 0 validation decision).
- **Implementation:** `bynat/cleaning/text.py:142–148` (`extract_keywords(**target_cols_and_keywords)`), `bynat/cleaning/text.py:284–292` (`truncate_after_substring(**target_cols_and_substrings)`), `bynat/cleaning/columns.py:496–503` (`split_list_objects(**target_cols_and_indices)`), `bynat/cleaning/columns.py:160–171` (`melt_transform_pivot(**kwargs)`).
- **Expected behavior:** reject `inplace` with `TypeError` (target contract), or handle it explicitly.
- **Observed behavior (probe `probe_inplace.py`, 2026-11-06):**
  - `df.bynat.extract_keywords("description", found=["blue"], inplace=True)` → returns a DataFrame with columns `['description', 'items', 'title', 'found', 'inplace']`; the extra `inplace` column holds `[nan]`. The original frame is not mutated.
  - `df.bynat.split_list_objects("items", first=0, inplace=True)` → extra column `inplace` with value `['b']` (`str[True]` → index 1). The original frame is not mutated.
  - `df.bynat.truncate_after_substring(title="-", inplace=True)` → `inplace` silently ignored; output identical to the non-inplace call.
  - `df.bynat.melt_transform_pivot(..., transform_func=..., inplace=True)` → `RuntimeError: transform_func failed while processing 'variable_value': <lambda>() got an unexpected keyword argument 'inplace'`.
  - The shared functions behave the same: `text.extract_keywords(f, "description", found=["blue"], inplace=True)` → extra `inplace` column.
  - The class API is correct: `BaseData.extract_keywords(..., inplace=True)` returns `None` and mutates the original (explicit `inplace` parameter at `base.py:458–465`).
- **Relevant tests:** `tests/test_inplace_deprecation.py::test_early_exits_return_an_independent_copy` calls these methods without `inplace`; no test asserts `pytest.raises(TypeError)` for an accessor `inplace` argument.
- **Classification:** production defect (silent data corruption / wrong result shape on the accessor path).

### PD-02 — High — `handle_outliers` / `drop_outliers` do not validate `min_samples`

- **Affected public contract:** `docs/TESTING_STANDARDS.md` §6.7 MS-3a — "The current implementation does not consistently validate `min_samples`; this is a Phase 0 implementation/test gap."
- **Implementation:** `bynat/cleaning/stats.py:97–154` (`handle_outliers`) and `157–217` (`drop_outliers`) pass `min_samples` straight into `grouped.count() >= min_samples` (`stats.py:65`) with no `_require_positive_int` call. Contrast `fill_missing` at `stats.py:276–277` and `fill_missing_from` at `stats.py:530–531`.
- **Expected behavior:** `ValueError` naming the parameter, consistent with `fill_missing` / `fill_missing_from`.
- **Observed behavior (probe `probe_defects.py`, section 2):**
  - `handle_outliers(min_samples=0)` → no error; `min_samples=-1` → no error; `min_samples=True` → no error; `min_samples=2.5` → no error.
  - `handle_outliers(min_samples='5')` → `UFuncTypeError: ufunc 'greater_equal' did not contain a loop with signature matching types ...`.
  - `drop_outliers` behaves identically.
- **Relevant tests:** `tests/test_cleaning.py::test_fill_missing_validates_min_samples` covers `fill_missing` only; no test covers the outlier methods.
- **Classification:** production defect (invalid input accepted silently; opaque exception for strings).

### PD-03 — Medium — `profile` report mapping silently drops duplicate column names

- **Affected public contract:** `README.md` §"Working with a report" — `columns` maps column name → `ColumnProfile`; `to_dict()` returns the same structure.
- **Implementation:** `bynat/cleaning/profile.py` builds the report `columns` mapping keyed by column name, so two columns named `"a"` collapse to one entry.
- **Expected behavior:** either both profiles are reachable, or the limitation is documented and pinned.
- **Observed behavior (probe `probe_contracts.py`, section B):** for `pd.DataFrame([[1, 2], [3, 4]], columns=["a", "a"])`:
  - `rep.dataset.column_count == 2`
  - `len(rep.column_list) == 2`
  - `len(rep.columns) == 1`, keys `['a']`
  - `list(rep.to_dict()["columns"].keys()) == ['a']`
  - `len(rep.to_dataframe()) == 2`
- **Relevant tests:** `tests/test_profile.py::test_duplicate_column_names_handling` asserts the first, second, and last facts but not the mapping, so it passes despite the defect.
- **Classification:** suspected production defect / undocumented limitation.

### PD-04 — High (documentation) — README documents a `noisey_terms` alias that the implementation rejects

- **Affected public contract:** `README.md:749` — "The misspelled `noisey_terms` name remains as a separate, deprecated compatibility alias for `noisy_terms`."
- **Implementation:** `bynat/cleaning/base.py:1538–1542` and `bynat/cleaning/enrich/nlp.py:204–208` raise `TypeError("extract_entities_nlp() got an unexpected keyword argument 'noisey_terms'; did you mean 'noisy_terms'?")`.
- **Conflicting documentation:** `CHANGELOG.md:51` "The misspelled `noisey_terms` parameter is not supported. Use `noisy_terms` instead."; `CHANGELOG.md:99` "Removed the deprecated `noisey_terms` parameter; use `noisy_terms` instead."
- **Observed behavior (probe `probe_contracts.py`, section E):** `TypeError: extract_entities_nlp() got an unexpected keyword argument 'noisey_terms'; did you mean 'noisy_terms'?`.
- **Relevant tests:** `tests/test_integrations.py:510–521` and `524–537` assert the `TypeError` — consistent with the CHANGELOG and code, inconsistent with the README.
- **Expected behavior:** reconcile the README with the CHANGELOG and the implementation.
- **Classification:** documentation defect (the tests follow the CHANGELOG; the README is stale).

### PD-05 — Medium (documentation) — README says `mode` breaks ties by first occurrence; behavior is alphabetical

- **Affected public contract:** `README.md:579` — "`mode` works for any hashable values and breaks ties by first occurrence."
- **Implementation:** `bynat/cleaning/stats.py:895–937` — `groupby(...).size()` sorts the grouping keys, then `sort_values(..., kind='mergesort')`; ties resolve to the alphabetically first label.
- **Observed behavior (probe `probe_contracts.py`, section A):** `get_hierarchical_stats("label", strategy="mode", hierarchy_cols="g")` on `label=["z","a"]` → statistic `['a']` (first occurrence would be `'z'`); on `["z","a","m"]` → `['a']`.
- **Relevant tests:** `tests/test_hierarchical_stats.py:99–117` asserts `['a','c','z']` for group `x` with labels `["b","a",None]` — pinning the alphabetical behavior without stating the rule.
- **Expected behavior:** correct the README, or change the implementation and the test together with a CHANGELOG entry.
- **Classification:** documentation/behavior mismatch.

### PD-06 — Low (determinism) — `convert_to_usd` reads the clock

- **Affected public contract:** `docs/TESTING_STANDARDS.md` §2.1 principle 6 — "No unseeded randomness, no clock dependence."
- **Implementation:** `bynat/cleaning/enrich/currency.py:92` — `current_year = time.localtime().tm_year`; used at `currency.py:172` to decide whether a year without data is cached as a miss.
- **Expected behavior:** deterministic output for the same input, or a documented/pinned clock boundary.
- **Observed behavior:** the same data can produce different cache contents depending on the run date (a missing year that is "past" in 2026 is cached as `None`; the same year in 2020 would not be).
- **Relevant tests:** `tests/test_integrations.py:251–295` and `tests/test_enrichment.py:333–370` use years 2019–2021, always in the past, so the boundary is never exercised.
- **Classification:** suspected production defect (determinism), low severity.

### E.1 Defects explicitly recorded in `docs/TESTING_STANDARDS.md`

The standard already records PD-01 (S-4/ML-2) and PD-02 (MS-3a) as open Phase 0 items. PD-03, PD-04, PD-05, and PD-06 are newly identified by this audit.

---

## F. Prioritized Remediation Plan

### F.1 Phase 2 — test-quality and coverage work (in priority order)

| # | Finding | Action | Risk addressed |
| ---: | --- | --- | --- |
| 1 | TQ-01 (Critical) | Add assertions to `test_translate_conditional_column_accepts_a_generator`; assert translated values and provider calls. | A test that cannot fail |
| 2 | TQ-02 | Replace the fake-provider protocol assertions with the production defaults and pin `bynat.cleaning.enrich` exports. | False confidence in provider defaults |
| 3 | TQ-03 | Add S-1 immutability assertions to every positive-path transformation test. | Undetected in-place mutation |
| 4 | TQ-06 | Replace `.equals()`-only assertions with `pd.testing.assert_frame_equal`. | Index-name/index-type drift |
| 5 | TQ-07 | Assert `rep.columns` / `to_dict()["columns"]` for duplicate columns. | Silent profile data loss |
| 6 | TQ-04, TQ-05 | Remove or justify internal call-count and private-helper assertions. | Implementation-detail coupling |
| 7 | TQ-08, TQ-09, TQ-10 | De-version expected values; hand-compute statistics; exact timestamp assertions. | Version overfit; weak numeric checks |
| 8 | TQ-12 | Add readable `id=` values to the three affected parametrizations. | Reviewability |
| 9 | TQ-13 | Remove the 14 unused `tmp_path` fixtures (or use them). | Phase 0 item |
| 10 | TQ-14 | Remove unnecessary `DeprecationWarning` suppression wrappers. | Hidden warning regressions |
| 11 | TQ-19 | Add `tests/conftest.py` / fix import mode so `test_doc_drift.py` always collects. | Silent loss of the doc-drift gate |
| 12 | D.2 / D.3 | Add missing §5/§6 cases: HO-7/DO-6, FM-23, FF-8/19/24/25, FM-11a/FF-13a, MS-4, HF-6; positive paths for `rename_by_substring`, `drop_CLASS_columns`, `align_lat_lng`, `reorder_columns`, `truncate_after_substring`, `remove_source_col`, `cartesian_explode`, `impute_by_language`; caching/enrichment export contract tests. | Documented contracts without regression protection |
| 13 | TQ-11, TQ-15, TQ-16, TQ-17, TQ-18 | Fold the redundant test; loosen exact `PRAGMA` tuples; note the threading test; fix the docstring; plan the `test_caching.py` split. | Maintenance |

### F.2 Phase 3 — contract and production work

| # | Finding | Action |
| ---: | --- | --- |
| 1 | PD-01 | Decide and implement `inplace` rejection (or handling) for the variadic shared functions and accessor methods; add `pytest.raises(TypeError)` tests through both entry points. |
| 2 | PD-02 | Implement `min_samples` validation for `handle_outliers` / `drop_outliers`; add boundary and invalid-value tests consistent with `fill_missing`. |
| 3 | PD-03 | Resolve the duplicate-column profile mapping (represent both profiles or document and pin the limitation). |
| 4 | PD-04 | Correct `README.md:749` to match the CHANGELOG and the implementation. |
| 5 | PD-05 | Correct `README.md:579` to state the actual tie-break rule, and name the rule in the test. |
| 6 | PD-06 | Remove the clock dependence in `convert_to_usd` or document and pin it. |
| 7 | D.3 | Add `tests/property/`, `tests/conftest.py`, marker registration, pytest config, and the Phase 1 coverage baseline. |
| 8 | D.5 | Extend the extras CI matrix to `translation`, `geocoding`, `currency`, `nlp`; add the wheel-installed run. |

---

## Commands Executed and Actual Results

All commands were run from `D:\My Own Environment Libraries\bynat\bynat` unless noted. `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider` were used for pytest runs so no `__pycache__` or `.pytest_cache` writes occurred.

| # | Command | Result |
| ---: | --- | --- |
| 1 | `git rev-parse HEAD` | `ddca26d76e8874223f5829fee0aea0fef461472a` |
| 2 | `git status --porcelain` | empty (clean) |
| 3 | `git log --oneline -5` | `ddca26d docs(testing): add comprehensive test suite audit plan and quality improvement phases` (HEAD) |
| 4 | `git ls-files \| grep -iE "test"` | 11 files under `tests/` + `.github/workflows/test.yml` + `docs/TESTING_STANDARDS.md` |
| 5 | `wc -l tests/*.py` | 5989 total; `test_caching.py` 1783 |
| 6 | `.venv-check/Scripts/python.exe -m pytest --collect-only -q -p no:cacheprovider` | `337 tests collected in 1.21s`, 0 errors |
| 7 | per-file collection count | accessor 13, caching 62, cleaning 31, doc_drift 3, enrichment 20, equivalence 74, fill_missing_from 9, hierarchical_stats 41, inplace_deprecation 33, integrations 26, profile 25 |
| 8 | AST definition scan | 218 definitions; 218 collected base names; 0 unmatched in either direction |
| 9 | `.venv-check/Scripts/python.exe -m pytest -q -rs -p no:cacheprovider` | `337 passed in 36.01s` |
| 10 | same, with `ahocorasick`/`sqlalchemy` blocked via out-of-repo plugin | `331 passed, 6 skipped in 34.23s`; 4× ahocorasick, 2× sqlalchemy |
| 11 | `.venv-check/Scripts/pytest.exe --collect-only -q` (repo root) | `334 tests collected, 1 error`; `ModuleNotFoundError: No module named 'tools'` |
| 12 | `pytest --collect-only -q D:\...\tests` from the scratch dir | `334 tests collected, 1 error`; same `ModuleNotFoundError` |
| 13 | AST no-assertion scan | `NO ASSERTION: test_enrichment.py::test_translate_conditional_column_accepts_a_generator (line 265)` — the only hit |
| 14 | unused-fixture AST scan | 14 functions with an unused `tmp_path` (exact list in TQ-13) |
| 15 | `grep -rn "shared_cache_manager\|CACHE_DIR_ENV_VAR\|DEFAULT_CACHE_DIR\|NominatimGeocoder\|resolve_cache_dir" tests/` | only a false hit in `tests/__pycache__/*.pyc`; **no test source references them** |
| 16 | `grep -rn "__all__" tests/` | only `tests/test_cleaning.py:18–20` (legacy `bynat.cleaning.Cleaning.__all__`) |
| 17 | `grep -rn "importorskip\|skipif\|xfail\|filterwarnings" tests/` | 4 `importorskip`, 1 `skipif`, 0 `xfail`, 0 `filterwarnings` |
| 18 | probe `probe_defects.py` | PD-02 evidence; `BaseData` construction emits no warning; `read_json` `KeyError` works |
| 19 | probe `probe_contracts.py` | PD-03, PD-04, PD-05, FM-23, FF-19 evidence |
| 20 | probe `probe_inplace.py` | PD-01 evidence |
| 21 | `git status --porcelain` (final) | empty; `git diff --stat` empty |

---

## Appendix A — Machine-checkable inventory

The full 218-row inventory is embedded in section B above (generated from `tests/test_*.py` AST + `pytest --collect-only` output; 218 rows, 337 cases, 0 unmatched).

**Disposition totals:** STRONG 182 · ADEQUATE 18 · GUARD 3 · CONDITIONAL 6 · WEAK 7 · REDUNDANT 1 · CRITICAL 1 = **218**.

**Unaccounted tests:** **0.** Every test definition maps to at least one collected case, and every collected case maps to exactly one definition. The only collection failure is environmental and affects 3 definitions in `tests/test_doc_drift.py` under a non-root CWD or the `pytest` console script (TQ-19); those 3 definitions are accounted for in the default invocation.

## Appendix B — Environment and limitations

- The audit was executed with the repository's pre-existing `.venv-check` interpreter (Python 3.11.16, pandas 3.0.6, numpy 2.5.4, pytest 9.2.0). Results on pandas 2 / Python 3.13 / Ubuntu may differ; the `_LEGACY_RELIABLE` skipif is the only version-conditional test and is documented above.
- The 6 extras-dependent skips were reproduced with an out-of-repo pytest plugin that sets `sys.modules["ahocorasick"] = None` and `sys.modules["sqlalchemy"] = None`; this simulates the default CI job without uninstalling anything.
- The 17 pandas-2 skips could not be executed here (pandas 3.0.6 is installed); they are derived from the `skipif` condition `int(pd.__version__.split(".")[0]) < 3` and the parametrize counts.
- Production-defect probes ran in the scratch directory with `sys.path` pointing at the repository; they wrote only to `tempfile` directories under the scratch dir and did not modify the repository.
- `docs/ROADMAP.md`, `benchmarks/`, and `CHANGELOG.md` were read for contract context but are not test files and are not part of the inventory.