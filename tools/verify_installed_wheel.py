"""Verify the built wheel in a clean environment instead of the checkout.

Phase 3 of the testing roadmap (``docs/TESTING_STANDARDS.md`` §9.2, "Build and
install") requires the suite to run against the installed distribution, not the
source tree, so that missing package files and dependency gaps are caught. This
script makes that check reproducible and offline:

1. copy the checkout into a scratch directory and build the wheel there, so the
   checkout never gains ``*.egg-info`` or ``build/`` artifacts;
2. create a clean virtualenv, install the wheel into it, and expose the project
   interpreter's numpy/pandas/pytest through a ``.pth`` file in the venv
   site-packages. The venv site-packages precedes that path, so ``bynat`` and
   its distribution metadata always resolve from the venv;
3. import ``bynat`` from a directory outside the checkout and assert that the
   imported package, its distribution metadata, and its public package files
   all come from the installed wheel rather than any source tree;
4. copy the complete ``tests/`` tree, the development tooling
   ``tools/sync_docs.py``, and the source artifacts the doc-drift test reads
   into a scratch test root, then run the full suite, the four target
   verification files, and an installed-distribution smoke test against the
   installed wheel.

The doc-drift test reads source files (``bynat/py.typed``,
``bynat/cleaning/base.py``, ``bynat/cleaning/accessor.py``, and
``bynat/cleaning/accessor.pyi``). Those files are copied into the scratch test
root without ``__init__.py``, so they form a PEP 420 namespace portion that
never shadows the regular ``bynat`` package installed in the venv
site-packages; the test still compares the source artifacts with the installed
modules.

Usage:
    python tools/verify_installed_wheel.py [--python PATH] [--keep]

Run it with a project interpreter that has numpy, pandas, and pytest (for
example ``.venv-check/Scripts/python.exe``). The build step uses that
interpreter when it provides the setuptools/wheel/build backend, and otherwise
falls back to the interpreter's base environment, which usually carries them.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "bynat"
PHASE3_TESTS = (
    "tests/modules/io/test_io_append.py",
    "tests/modules/io/test_io_json.py",
    "tests/modules/io/test_io_read.py",
    "tests/modules/enrichment/test_optional_ahocorasick.py",
    "tests/modules/enrichment/test_optional_sqlalchemy.py",
    "tests/modules/columns/test_columns_pivot.py",
    "tests/modules/columns/test_columns_split.py",
    "tests/modules/columns/test_columns_structural.py",
    "tests/cross_cutting/accessor/test_parity.py",
)
TOP_LEVEL_EXPORTS = {"BynatAccessor", "ProfileReport", "profile", "read_csv", "read_json"}
CLEANING_EXPORTS = {"BaseData", "CsvFile", "JsonFile"}
PACKAGE_DATA = ("bynat/py.typed", "bynat/cleaning/accessor.pyi")

# Development tooling the copied suite imports. It is not part of the wheel.
# `benchmarks/reference_impls.py` backs the equivalence tests' shared 0.3.0
# reference implementations (see benchmarks/_common.py), so it is copied
# alongside tools/sync_docs.py.
TEST_TOOLING = ("tools/sync_docs.py", "benchmarks/reference_impls.py")

# Source artifacts the doc-drift test reads. They are copied into the scratch
# test root without __init__.py so they stay a namespace portion and cannot
# shadow the installed regular package.
DOC_DRIFT_SOURCE_FILES = (
    "bynat/py.typed",
    "bynat/cleaning/base.py",
    "bynat/cleaning/accessor.py",
    "bynat/cleaning/accessor.pyi",
)

# Never copy VCS metadata, virtualenvs, caches, or build artifacts into the
# scratch source tree.
SOURCE_COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    ".github",
    ".venv",
    ".venv-check",
    "venv",
    "env",
    "build",
    "dist",
    "*.egg-info",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov",
    "Settings",
)

PROBE = '''\
import importlib.metadata
import json
import sys
import sysconfig

import pandas as pd

import bynat
import bynat.cleaning as cleaning

frame = pd.DataFrame({"a": [1.0, None, 3.0]})
default_result = frame.bynat.fill_missing("a")
fallback_result = frame.bynat.fill_missing("a", fallback_global=True)

distribution = importlib.metadata.distribution("bynat")
info = {
    "executable": sys.executable,
    "bynat_file": bynat.__file__,
    "dist_path": str(distribution._path),
    "dist_version": importlib.metadata.version("bynat"),
    "site_packages": sysconfig.get_paths()["purelib"],
    "installed_files": sorted(
        str(item)
        for item in distribution.files or []
        if str(item).startswith("bynat/") and "__pycache__" not in str(item)
    ),
    "top_level_exports": sorted(name for name in bynat.__all__ if hasattr(bynat, name)),
    "cleaning_exports": sorted(name for name in cleaning.__all__ if hasattr(cleaning, name)),
    "smoke": {
        "rows": int(default_result.shape[0]),
        "default_nulls": int(default_result["a"].isna().sum()),
        "fallback_nulls": int(fallback_result["a"].isna().sum()),
    },
    "sys_path": list(sys.path),
}
print(json.dumps(info))
'''

SMOKE_TEST = '''\
"""Smoke: the Phase 3 suite imports the installed wheel, not the checkout."""

import importlib.metadata
import os
import sys
from pathlib import Path

import bynat

REPO_ROOT = Path(os.environ["BYNAT_VERIFY_REPO_ROOT"])
SCRATCH_SOURCE = Path(os.environ["BYNAT_VERIFY_SOURCE_ROOT"])
SITE_PACKAGES = Path(os.environ["BYNAT_VERIFY_SITE_PACKAGES"])
EXPECTED_VERSION = os.environ["BYNAT_VERIFY_VERSION"]


def test_imported_bynat_resolves_to_the_installed_wheel():
    resolved = Path(bynat.__file__).resolve()
    assert resolved.is_relative_to(SITE_PACKAGES.resolve())
    assert not resolved.is_relative_to(REPO_ROOT.resolve())
    assert not resolved.is_relative_to(SCRATCH_SOURCE.resolve())


def test_installed_distribution_version_matches_the_project():
    assert importlib.metadata.version("bynat") == EXPECTED_VERSION


def test_checkout_root_is_not_on_sys_path():
    resolved_entries = {str(Path(entry).resolve()) for entry in sys.path if entry}
    assert str(REPO_ROOT.resolve()) not in resolved_entries
    assert str(SCRATCH_SOURCE.resolve()) not in resolved_entries
'''

# Generated into the scratch test root. It fails every test if bynat does not
# resolve from the verification venv, so the copied suite cannot silently run
# against a source tree.
GUARD_CONFTEST = '''\
"""Generated by verify_installed_wheel.py.

Fails every test if ``bynat`` does not resolve from the verification venv's
site-packages, so the copied suite cannot accidentally run against a source
tree.
"""

import os
from pathlib import Path

import pytest

SITE_PACKAGES = Path(os.environ["BYNAT_VERIFY_SITE_PACKAGES"]).resolve()


@pytest.fixture(autouse=True)
def _bynat_resolves_from_the_installed_wheel():
    import bynat

    resolved = Path(bynat.__file__).resolve()
    assert resolved.is_relative_to(SITE_PACKAGES), (
        f"bynat resolved outside the verification venv site-packages: {resolved}"
    )
'''


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
        env.pop(key, None)
    return env


def _project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def _source_package_files(base: Path) -> set[str]:
    package_dir = base / PACKAGE
    files: set[str] = set()
    for path in package_dir.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        files.add(path.relative_to(base).as_posix())
    return files


def _wheel_record_files(wheel: Path) -> set[str]:
    with zipfile.ZipFile(wheel) as archive:
        record_name = next(name for name in archive.namelist() if name.endswith(".dist-info/RECORD"))
        lines = archive.read(record_name).decode("utf-8").splitlines()
    return {line.split(",", 1)[0] for line in lines}


def _wheel_requires(wheel: Path) -> set[str]:
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        text = archive.read(metadata_name).decode("utf-8")
    return {
        line.split(":", 1)[1].split(";")[0].strip().lower()
        for line in text.splitlines()
        if line.startswith("Requires-Dist:")
    }


def _copy_source(scratch: Path) -> Path:
    """Copy the checkout into the scratch directory for an isolated build."""
    source = scratch / "source"
    shutil.copytree(ROOT, source, ignore=SOURCE_COPY_IGNORE)
    return source


def _base_python(python: str, scratch: Path) -> str | None:
    result = _run(
        [python, "-c", "import sys; print(getattr(sys, '_base_executable', sys.base_prefix))"],
        cwd=scratch,
        env=_clean_env(),
    )
    if result.returncode != 0:
        return None
    candidate = Path(result.stdout.strip().splitlines()[-1])
    if candidate.is_file():
        return str(candidate)
    alt = candidate / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(alt) if alt.is_file() else None


def _has_build_backend(python: str, scratch: Path) -> bool:
    result = _run(
        [python, "-c", "import setuptools, wheel, build"],
        cwd=scratch,
        env=_clean_env(),
    )
    return result.returncode == 0


def _build_python(host_python: str, scratch: Path) -> str:
    """Pick an interpreter that can run the PEP 517 backend offline."""
    candidates = [host_python]
    base = _base_python(host_python, scratch)
    if base is not None and base != host_python:
        candidates.append(base)
    for candidate in candidates:
        if _has_build_backend(candidate, scratch):
            return candidate
    return host_python


def _build_wheel(scratch: Path, build_python: str) -> tuple[Path, str]:
    dist = scratch / "dist"
    dist.mkdir()
    source = scratch / "source"
    candidates = [
        (
            [
                build_python,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                str(dist),
                str(source),
            ],
            f"{build_python} -m build --wheel --no-isolation",
        ),
        (
            [
                build_python,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--no-build-isolation",
                "-w",
                str(dist),
                str(source),
            ],
            f"{build_python} -m pip wheel --no-deps --no-build-isolation",
        ),
    ]
    errors: list[str] = []
    for command, label in candidates:
        for stale in dist.glob("*.whl"):
            stale.unlink()
        result = _run(command, cwd=source, env=_clean_env())
        if result.returncode != 0:
            errors.append(f"{label}: exit {result.returncode}: {result.stderr.strip()[-400:]}")
            continue
        wheels = sorted(dist.glob("*.whl"))
        if len(wheels) != 1:
            errors.append(f"{label}: expected exactly one wheel, found {len(wheels)}")
            continue
        return wheels[0], label
    raise RuntimeError("wheel build failed:\n" + "\n".join(errors))


def _create_venv(scratch: Path, python: str) -> Path:
    venv_dir = scratch / "venv"
    result = _run(
        [python, "-m", "venv", str(venv_dir)],
        cwd=scratch,
        env=_clean_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"venv creation failed: {result.stderr.strip()[-400:]}")
    return venv_dir


def _venv_python(venv_dir: Path) -> str:
    if os.name == "nt":
        candidate = venv_dir / "Scripts" / "python.exe"
    else:
        candidate = venv_dir / "bin" / "python"
    if not candidate.exists():
        raise RuntimeError(f"venv interpreter not found: {candidate}")
    return str(candidate)


def _site_packages(python: str, scratch: Path) -> Path | None:
    result = _run(
        [python, "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        cwd=scratch,
        env=_clean_env(),
    )
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip().splitlines()[-1])
    return path if path.is_dir() else None


def _link_host_packages(scratch: Path, venv_python: str, host_python: str) -> Path | None:
    """Expose the project interpreter's test dependencies to the venv.

    A ``.pth`` file appends the host's site-packages after the venv's own
    site-packages, so ``bynat`` and its distribution metadata still resolve
    from the venv while numpy/pandas/pytest are reused offline.
    """
    host_site = _site_packages(host_python, scratch)
    if host_site is None:
        return None
    venv_site = _site_packages(venv_python, scratch)
    if venv_site is None or venv_site.resolve() == host_site.resolve():
        return None
    marker = venv_site / "bynat_verify_host.pth"
    marker.write_text(str(host_site) + "\n", encoding="utf-8")
    return host_site


def _install_wheel(scratch: Path, venv_python: str, wheel: Path) -> None:
    result = _run(
        [
            venv_python,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--ignore-installed",
            str(wheel),
        ],
        cwd=scratch,
        env=_clean_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"wheel installation failed: {result.stderr.strip()[-400:]}")


def _probe(scratch: Path, venv_python: str) -> dict[str, object]:
    probe_path = scratch / "probe_installed.py"
    probe_path.write_text(PROBE, encoding="utf-8")
    result = _run([venv_python, str(probe_path)], cwd=scratch, env=_clean_env())
    if result.returncode != 0:
        raise RuntimeError(f"installed-distribution probe failed: {result.stderr.strip()[-400:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


def _verify_installed(
    wheel: Path,
    expected_version: str,
    probe: dict[str, object],
    source_root: Path,
) -> dict[str, object]:
    site_packages = Path(str(probe["site_packages"])).resolve()
    bynat_file = Path(str(probe["bynat_file"])).resolve()
    dist_path = Path(str(probe["dist_path"])).resolve()
    source_files = _source_package_files(source_root)
    wheel_files = _wheel_record_files(wheel)
    installed_files = {str(item) for item in probe["installed_files"]}

    failures: list[str] = []
    if not bynat_file.is_relative_to(site_packages):
        failures.append(f"bynat resolved outside the venv site-packages: {bynat_file}")
    checkout_file = (ROOT / PACKAGE / "__init__.py").resolve()
    if bynat_file == checkout_file:
        failures.append(f"bynat resolved to the checkout: {bynat_file}")
    if not dist_path.is_relative_to(site_packages):
        failures.append(f"distribution metadata resolved outside the venv site-packages: {dist_path}")
    if str(probe["dist_version"]) != expected_version:
        failures.append(f"installed version {probe['dist_version']} != pyproject version {expected_version}")
    if not source_files <= wheel_files:
        failures.append(f"source package files missing from the wheel: {sorted(source_files - wheel_files)}")
    if not set(PACKAGE_DATA) <= wheel_files:
        failures.append(f"package data missing from the wheel: {sorted(set(PACKAGE_DATA) - wheel_files)}")
    if source_files != installed_files:
        failures.append(
            "installed package files differ from the source package files: "
            f"missing={sorted(source_files - installed_files)} "
            f"extra={sorted(installed_files - source_files)}"
        )
    requires = _wheel_requires(wheel)
    if not {"numpy", "pandas"} <= requires:
        failures.append(f"wheel metadata does not declare numpy and pandas: {sorted(requires)}")
    if set(probe["top_level_exports"]) != TOP_LEVEL_EXPORTS:
        failures.append(f"top-level exports differ: {probe['top_level_exports']}")
    if set(probe["cleaning_exports"]) != CLEANING_EXPORTS:
        failures.append(f"bynat.cleaning exports differ: {probe['cleaning_exports']}")
    if probe["smoke"] != {"rows": 3, "default_nulls": 1, "fallback_nulls": 0}:
        failures.append(f"installed-package smoke check failed: {probe['smoke']}")
    sys_path = [str(Path(entry).resolve()) for entry in probe["sys_path"] if entry]
    if str(ROOT.resolve()) in sys_path:
        failures.append(f"checkout root is on sys.path: {ROOT}")
    if str(source_root.resolve()) in sys_path:
        failures.append(f"scratch source root is on sys.path: {source_root}")

    if failures:
        raise RuntimeError("installed-distribution verification failed:\n" + "\n".join(failures))
    return {
        "site_packages": str(site_packages),
        "bynat_file": str(bynat_file),
        "dist_path": str(dist_path),
        "version": str(probe["dist_version"]),
        "public_files": len(source_files),
    }


def _prepare_test_root(scratch: Path, source_root: Path) -> Path:
    """Copy the complete suite and its non-package tooling into the scratch."""
    testroot = scratch / "testroot"
    shutil.copytree(
        source_root / "tests",
        testroot / "tests",
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"),
    )
    tools_dir = testroot / "tools"
    tools_dir.mkdir()
    for relative in TEST_TOOLING:
        destination = tools_dir / Path(relative).name
        shutil.copyfile(source_root / relative, destination)
        if Path(relative).parent != Path("."):
            (testroot / Path(relative).parent).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root / relative, testroot / relative)
    for relative in DOC_DRIFT_SOURCE_FILES:
        destination = testroot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, destination)
    smoke_dir = testroot / "smoke"
    smoke_dir.mkdir()
    (smoke_dir / "test_installed_distribution_smoke.py").write_text(SMOKE_TEST, encoding="utf-8")
    (testroot / "conftest.py").write_text(GUARD_CONFTEST, encoding="utf-8")
    return testroot


def _run_pytest(
    scratch: Path,
    venv_python: str,
    targets: list[Path],
    env: dict[str, str],
    label: str,
) -> dict[str, object]:
    report = scratch / f"junit_{label}.xml"
    result = _run(
        [
            venv_python,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junitxml={report}",
            *[str(target) for target in targets],
        ],
        cwd=scratch,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{label} pytest run failed (exit {result.returncode}):\n{result.stdout[-2000:]}"
        )
    suite = xml.etree.ElementTree.parse(report).getroot()
    if suite.tag != "testsuite":
        suite = suite.find("testsuite")
    cases = list(suite.iter("testcase"))
    skipped = sum(1 for case in cases if case.find("skipped") is not None)
    xfailed = sum(
        1
        for case in cases
        if case.find("skipped") is not None and case.find("skipped").get("type") == "pytest.xfail"
    )
    return {
        "tests": int(suite.get("tests", len(cases))),
        "failures": int(suite.get("failures", 0)),
        "errors": int(suite.get("errors", 0)),
        "skipped": skipped,
        "xfailed": xfailed,
        "passed": int(suite.get("tests", len(cases))) - int(suite.get("failures", 0)) - int(suite.get("errors", 0)) - skipped,
        "summary": result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "",
    }


def _snapshot_build_artifacts() -> dict[str, float]:
    """Record checkout build artifacts so side effects are detectable."""
    snapshot: dict[str, float] = {}
    for pattern in ("build", "*.egg-info"):
        for path in ROOT.glob(pattern):
            if path.is_dir():
                for item in path.rglob("*"):
                    if item.is_file():
                        snapshot[str(item)] = item.stat().st_mtime
    return snapshot


def _assert_no_checkout_side_effects(before: dict[str, float]) -> None:
    after = _snapshot_build_artifacts()
    if after == before:
        return
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(key for key in set(before) & set(after) if before[key] != after[key])
    raise RuntimeError(
        "checkout build artifacts changed during verification: "
        f"added={added} removed={removed} changed={changed}"
    )


def _report(
    *,
    python: str,
    build_python: str,
    scratch: Path,
    source_root: Path,
    wheel: Path,
    build_method: str,
    venv_dir: Path,
    venv_python: str,
    host_site: Path | None,
    installed: dict[str, object],
    full: dict[str, object],
    phase3: dict[str, object],
    smoke: dict[str, object],
) -> None:
    print("=== bynat installed-wheel verification ===")
    print(f"source checkout: {ROOT}")
    print(f"host python: {python}")
    print(f"build python: {build_python}")
    print(f"scratch: {scratch}")
    print(f"scratch source: {source_root}")
    print(f"build method: {build_method}")
    print(f"wheel: {wheel}")
    print(f"venv: {venv_dir}")
    print(f"venv python: {venv_python}")
    print(f"host site-packages: {host_site}")
    print(f"installed bynat: {installed['bynat_file']}")
    print(f"installed dist-info: {installed['dist_path']}")
    print(f"installed version: {installed['version']}")
    print(f"public package files verified: {installed['public_files']}")
    for label, counts in (("full", full), ("phase3", phase3), ("smoke", smoke)):
        print(
            f"{label} tests: "
            f"{counts['tests']} tests, {counts['passed']} passed, {counts['xfailed']} xfailed, "
            f"{counts['skipped'] - counts['xfailed']} skipped, {counts['failures']} failed, "
            f"{counts['errors']} errors"
        )
        print(f"{label} summary: {counts['summary']}")
    print("checkout build artifacts: unchanged")
    print("RESULT: PASS")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the wheel from a scratch copy, install it in a clean virtualenv, and run "
        "the full copied test suite against the installed distribution."
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="project interpreter with numpy/pandas/pytest; also used to create the virtualenv "
        "(default: the interpreter running this script)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep the scratch directory instead of removing it",
    )
    args = parser.parse_args()

    missing = [relative for relative in PHASE3_TESTS if not (ROOT / relative).exists()]
    if missing:
        print(f"FAILED: missing Phase 3 test files: {missing}", file=sys.stderr)
        return 1

    scratch = Path(tempfile.mkdtemp(prefix="bynat-wheel-verify-"))
    print(f"scratch: {scratch}")
    failure: Exception | None = None
    try:
        expected_version = _project_version()
        before = _snapshot_build_artifacts()
        source_root = _copy_source(scratch)
        build_python = _build_python(args.python, scratch)
        wheel, build_method = _build_wheel(scratch, build_python)
        venv_dir = _create_venv(scratch, args.python)
        venv_python = _venv_python(venv_dir)
        host_site = _link_host_packages(scratch, venv_python, args.python)
        _install_wheel(scratch, venv_python, wheel)
        probe = _probe(scratch, venv_python)
        installed = _verify_installed(wheel, expected_version, probe, source_root)

        testroot = _prepare_test_root(scratch, source_root)
        env = _clean_env()
        env["BYNAT_VERIFY_REPO_ROOT"] = str(ROOT)
        env["BYNAT_VERIFY_SOURCE_ROOT"] = str(source_root)
        env["BYNAT_VERIFY_SITE_PACKAGES"] = str(installed["site_packages"])
        env["BYNAT_VERIFY_VERSION"] = str(installed["version"])

        tests_dir = testroot / "tests"
        phase3_targets = [testroot / relative for relative in PHASE3_TESTS]
        full = _run_pytest(scratch, venv_python, [tests_dir], env, "full")
        phase3 = _run_pytest(scratch, venv_python, phase3_targets, env, "phase3")
        smoke = _run_pytest(scratch, venv_python, [testroot / "smoke"], env, "smoke")

        _assert_no_checkout_side_effects(before)
        _report(
            python=args.python,
            build_python=build_python,
            scratch=scratch,
            source_root=source_root,
            wheel=wheel,
            build_method=build_method,
            venv_dir=venv_dir,
            venv_python=venv_python,
            host_site=host_site,
            installed=installed,
            full=full,
            phase3=phase3,
            smoke=smoke,
        )
    except Exception as error:
        failure = error
        print(f"FAILED: {error}", file=sys.stderr)
    finally:
        if args.keep:
            print(f"scratch kept for inspection: {scratch}")
        else:
            shutil.rmtree(scratch, ignore_errors=True)
            if scratch.exists():
                print(f"scratch could not be fully removed: {scratch}", file=sys.stderr)
            else:
                print(f"scratch removed: {scratch}")
    return 1 if failure is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
