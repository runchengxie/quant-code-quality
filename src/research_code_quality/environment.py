"""Compare installed distribution metadata with explicit frozen dependency evidence."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_expected(path: Path, requirements: bool = False) -> dict[str, list[dict]]:
    """Read uv package candidates or strict name==version frozen requirements."""
    if requirements:
        packages = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)", line)
            if not match:
                raise ValueError("requirements must contain only name==version entries")
            packages.append({"name": match[1], "version": match[2]})
    else:
        packages = tomllib.loads(path.read_text()).get("package", [])
    if not packages:
        raise ValueError("source contains no package records")
    expected: dict[str, list[dict]] = {}
    for package in packages:
        name = normalize(package["name"])
        version = package["version"]
        source = package.get("source", {})
        if not isinstance(source, dict):
            raise ValueError("package source must be an object")
        for key in ("git", "url", "editable", "directory"):
            if key in source and not isinstance(source[key], str):
                raise ValueError(f"package source {key} must be a string")
        expected.setdefault(name, []).append({"version": version, "source": source})
    return expected


def installed(paths: list[str] | None = None) -> list[dict]:
    """Read dist-info using importlib, without importing installed packages."""
    for path in paths or []:
        if not Path(path).is_dir():
            raise ValueError(f"metadata directory does not exist: {path}")
    distributions = (
        importlib.metadata.distributions(path=paths)
        if paths
        else (importlib.metadata.distributions())
    )
    records = []
    for distribution in distributions:
        # Editable setuptools checkouts may expose egg-info alongside dist-info.
        # Only installed dist-info has METADATA; source-tree PKG-INFO is not proof.
        if distribution.read_text("METADATA") is None:
            continue
        direct = distribution.read_text("direct_url.json")
        records.append(
            {
                "name": normalize(distribution.metadata["Name"]),
                "version": distribution.version,
                "direct_url": json.loads(direct) if direct else None,
            }
        )
    return sorted(records, key=lambda item: (item["name"], item["version"]))


def source_matches(
    source: dict, direct: dict | None, root: Path, no_editable: bool = False
) -> bool:
    if direct is not None:
        if not isinstance(direct, dict):
            raise ValueError("direct_url metadata must be an object")
        if "url" in direct and not isinstance(direct["url"], str):
            raise ValueError("direct_url url must be a string")
        for key in ("vcs_info", "dir_info", "archive_info"):
            if key in direct and not isinstance(direct[key], dict):
                raise ValueError(f"direct_url {key} must be an object")
    if "git" in source:
        url, separator, commit = source["git"].rpartition("#")
        return bool(
            separator
            and direct
            and direct.get("vcs_info", {}).get("commit_id") == commit
            and direct.get("url", "").removeprefix("git+") == url.split("?", 1)[0]
        )
    if "url" in source:
        return bool(direct and direct.get("url") == source["url"])
    for key in ("editable", "directory"):
        if key in source:
            if not direct or not direct.get("url", "").startswith("file://"):
                return False
            actual = Path(unquote(direct["url"][7:])).resolve()
            return actual == (root / source[key]).resolve() and bool(
                direct.get("dir_info", {}).get("editable")
            ) == (key == "editable" and not no_editable)
    # Registry packages must not silently be replaced by local or VCS builds.
    return not direct


def compare(
    expected: dict[str, list[dict]],
    actual: list[dict],
    root: Path,
    require_all: bool = False,
    no_editable: bool = False,
) -> list[dict]:
    drift = []
    seen = set()
    for package in actual:
        name = package["name"]
        if name in seen:
            drift.append({"name": name, "kind": "duplicate_distribution"})
        seen.add(name)
        candidates = expected.get(name)
        if candidates is None:
            drift.append({"name": name, "kind": "unexpected_package", "actual": package["version"]})
            continue
        versions = [item for item in candidates if item["version"] == package["version"]]
        if not versions:
            drift.append(
                {
                    "name": name,
                    "kind": "version_mismatch",
                    "actual": package["version"],
                    "expected": sorted({item["version"] for item in candidates}),
                }
            )
        elif not any(
            source_matches(item["source"], package["direct_url"], root, no_editable)
            for item in versions
        ):
            drift.append({"name": name, "kind": "source_mismatch"})
    if require_all:
        drift.extend(
            {"name": name, "kind": "missing_package"} for name in sorted(expected.keys() - seen)
        )
    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--lock", type=Path)
    source.add_argument("--requirements", type=Path)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--python", help="Interpreter whose distribution metadata to inspect")
    target.add_argument(
        "--site-packages", action="append", help="Explicit metadata search directory"
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Also reject missing records (use only for a single environment freeze)",
    )
    parser.add_argument(
        "--no-editable",
        action="store_true",
        help="Expect local editable lock records to be installed non-editably",
    )
    args = parser.parse_args(argv)
    path = args.lock or args.requirements
    try:
        expected = read_expected(path, bool(args.requirements))
        if args.python:
            # Run a stdlib-only metadata reader in the target interpreter; no installation needed.
            script = (
                "import importlib.metadata as m,json; "
                'print(json.dumps([{ "name":d.metadata["Name"],"version":d.version,'
                '"direct_url":json.loads(d.read_text("direct_url.json") or "null")} '
                'for d in m.distributions() if d.read_text("METADATA") is not None]))'
            )
            result = subprocess.run(
                [args.python, "-I", "-c", script],
                check=True,
                text=True,
                capture_output=True,
                timeout=30,
            )
            actual = json.loads(result.stdout)
            for package in actual:
                package["name"] = normalize(package["name"])
        else:
            actual = installed(args.site_packages)
        drift = compare(expected, actual, path.resolve().parent, args.require_all, args.no_editable)
        print(
            json.dumps(
                {"schema_version": 1, "source": str(path), "checked": len(actual), "drift": drift},
                sort_keys=True,
            )
        )
        return int(bool(drift))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({"schema_version": 1, "error": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
