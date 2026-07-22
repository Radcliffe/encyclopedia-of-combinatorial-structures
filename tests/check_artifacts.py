#!/usr/bin/env python3
"""Validate release-specific contents of a combstruct wheel and sdist."""

from __future__ import annotations

import argparse
import tarfile
import tomllib
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path

EXPECTED_RECORD_COUNT = 1075
EXPECTED_LICENSE_EXPRESSION = "LGPL-2.1-only AND CC-BY-SA-4.0"


def project_version() -> str:
    """Read the expected artifact version from the project metadata."""

    project_root = Path(__file__).resolve().parents[1]
    with (project_root / "pyproject.toml").open("rb") as metadata_file:
        metadata = tomllib.load(metadata_file)
    return str(metadata["project"]["version"])


def require_members(members: set[str], expected: set[str], artifact: Path) -> None:
    """Raise an assertion with a useful message when members are absent."""

    missing = sorted(expected - members)
    if missing:
        raise AssertionError(f"{artifact} is missing: {', '.join(missing)}")


def check_wheel(path: Path) -> None:
    """Validate package, data, license, and core metadata in a wheel."""

    with zipfile.ZipFile(path) as wheel:
        members = set(wheel.namelist())
        require_members(
            members,
            {
                "combstruct/__init__.py",
                "combstruct/__main__.py",
                "combstruct/catalog.py",
                "combstruct/py.typed",
                "combstruct/specification.py",
                "combstruct/terms.py",
            },
            path,
        )

        records = {
            member
            for member in members
            if member.startswith("combstruct/data/ecs") and member.endswith(".json")
        }
        if len(records) != EXPECTED_RECORD_COUNT:
            raise AssertionError(
                f"{path} contains {len(records)} ECS records; expected {EXPECTED_RECORD_COUNT}"
            )

        license_members = {member for member in members if ".dist-info/licenses/" in member}
        license_names = {member.rsplit("/", 1)[-1] for member in license_members}
        require_members(
            license_names,
            {"CC-BY-SA-4.0.txt", "LICENSE.md", "NOTICE.md"},
            path,
        )

        metadata_members = [member for member in members if member.endswith(".dist-info/METADATA")]
        if len(metadata_members) != 1:
            raise AssertionError(f"{path} must contain exactly one METADATA file")
        metadata = BytesParser(policy=policy.default).parsebytes(wheel.read(metadata_members[0]))
        if metadata["Name"] != "combstruct":
            raise AssertionError(f"Unexpected distribution name: {metadata['Name']}")
        expected_version = project_version()
        if metadata["Version"] != expected_version:
            raise AssertionError(f"Unexpected distribution version: {metadata['Version']}")
        if metadata["License-Expression"] != EXPECTED_LICENSE_EXPRESSION:
            raise AssertionError(f"Unexpected license expression: {metadata['License-Expression']}")


def check_sdist(path: Path) -> None:
    """Validate source, tests, documentation, licenses, and data in an sdist."""

    with tarfile.open(path, mode="r:gz") as archive:
        raw_members = {member.name for member in archive.getmembers()}

    roots = {member.split("/", 1)[0] for member in raw_members}
    if len(roots) != 1:
        raise AssertionError(f"{path} must contain exactly one archive root")
    root = roots.pop()
    members = {member.removeprefix(f"{root}/") for member in raw_members if member != root}

    require_members(
        members,
        {
            "CHANGELOG.md",
            "LICENSE.md",
            "LICENSES/CC-BY-SA-4.0.txt",
            "MANIFEST.in",
            "NOTICE.md",
            "PYTHON_PACKAGE.md",
            "docs/api.md",
            "docs/development.md",
            "docs/release-readiness.md",
            "docs/releasing.md",
            "pyproject.toml",
            "src/combstruct/__init__.py",
            "src/combstruct/catalog.py",
            "src/combstruct/py.typed",
            "src/combstruct/specification.py",
            "src/combstruct/terms.py",
            "tests/check_artifacts.py",
            "tests/test_distribution.py",
        },
        path,
    )

    records = {
        member
        for member in members
        if member.startswith("structures/ecs") and member.endswith(".json")
    }
    if len(records) != EXPECTED_RECORD_COUNT:
        raise AssertionError(
            f"{path} contains {len(records)} ECS records; expected {EXPECTED_RECORD_COUNT}"
        )


def main() -> int:
    """Parse artifact paths and validate the wheel and source distribution."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("sdist", type=Path)
    arguments = parser.parse_args()

    check_wheel(arguments.wheel)
    check_sdist(arguments.sdist)
    print(f"Validated {arguments.wheel} and {arguments.sdist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
