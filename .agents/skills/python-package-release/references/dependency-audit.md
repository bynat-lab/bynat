# Python Dependency Audit

Use this decision table while auditing imports for package metadata.

| Source evidence | Metadata action |
| --- | --- |
| Standard-library module (`os`, `json`, `typing`, `pathlib`) | Do not declare it as a runtime dependency. |
| Third-party import executed when the public module imports | Declare its installable distribution under runtime dependencies. |
| Third-party import used only by a genuinely separable feature and not needed for package import/basic use | Consider an optional extra, and document the extra installation command. |
| Import name differs from distribution name | Inspect local `setup.py`, `pyproject.toml`, `*.egg-info`, adjacent local packages, or installed metadata; do not infer silently. |
| Local sibling package imported with a top-level absolute name | Treat it as mandatory if the import executes at module import time; if it is not bundled, document the separate distribution and release risk. |
| Database driver selected through a user-provided SQLAlchemy URL | Do not add every possible driver; document that the caller must install the selected DBAPI driver. |
| spaCy language model or other downloaded model | Document it separately from Python package dependencies unless the project explicitly packages it. |
| Network service used by a method | Document network/rate-limit/cache behavior; do not claim offline functionality for that method. |
| Distribution mapping or minimum version cannot be established locally | Leave the dependency unpinned if necessary and report the unresolved uncertainty before release. |

## Practical audit sequence

1. Parse every source file and collect `import` and `from ... import ...` statements.
2. Classify standard-library imports using the target Python version.
3. Search source usage to distinguish import-time requirements from method-local feature requirements.
4. Search local metadata for the distribution name and version; inspect sibling local packages when an absolute import points outside the package.
5. Compare the resulting dependency set with `[project].dependencies` and any extras.
6. Verify the built wheel's `Requires-Dist` entries instead of trusting the source configuration alone.

## Release-risk rule

If a package contains a bundled implementation but imports a separate top-level distribution instead of the bundled module, do not silently replace the import during a metadata-only task. Declare the dependency when locally identifiable, document the mismatch, and report that PyPI installation remains blocked until the dependency is verified or the import is corrected in a separately authorized source change.
