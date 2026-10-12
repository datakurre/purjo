#!/usr/bin/env python3
"""Check that built distributions contain only the files meant to be released.

Usage: python scripts/check-dist.py [DIST_DIR]

Fails when the sdist or the wheel in DIST_DIR (default: dist) carries anything
outside the package itself and its metadata -- fixtures, examples, CI config --
or when the two disagree about what the package contains.
"""

from pathlib import Path
from pathlib import PurePosixPath
import sys
import tarfile
import zipfile

PACKAGE = "purjo"

# Top-level sdist files besides the package: project metadata, and .gitignore
# which hatchling adds so that building a wheel from the sdist ignores the
# same files as building it from the repository.
SDIST_FILES = {
    ".gitignore",
    "CHANGELOG.md",
    "LICENSE",
    "PKG-INFO",
    "README.md",
    "pyproject.toml",
}

# Package files that must be present: the entry point module and a template
# from the data directory `pur init` reads.
REQUIRED_PACKAGE_FILES = {
    f"{PACKAGE}/__init__.py",
    f"{PACKAGE}/main.py",
    f"{PACKAGE}/data/hello.robot",
}


def sdist_names(path: Path) -> set[str]:
    """Return sdist member paths without the leading ``name-version/``.

    Links and other special members are reported as ``<path> (not a regular
    file)`` so that they fail the check instead of slipping past it.
    """
    root = path.name.removesuffix(".tar.gz")
    names = set()
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            parts = PurePosixPath(member.name).parts
            if parts[0] != root or len(parts) < 2:
                names.add(f"{member.name} (outside {root}/)")
                continue
            name = str(PurePosixPath(*parts[1:]))
            names.add(name if member.isfile() else f"{name} (not a regular file)")
    return names


def wheel_names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return {name for name in archive.namelist() if not name.endswith("/")}


def main(dist_dir: Path) -> int:
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    wheels = sorted(dist_dir.glob("*.whl"))
    if len(sdists) != 1 or len(wheels) != 1:
        print(
            f"ERROR: expected one sdist and one wheel in {dist_dir}, "
            f"found {len(sdists)} and {len(wheels)}"
        )
        return 1

    errors: list[str] = []

    sdist = sdist_names(sdists[0])
    sdist_package = {
        name.removeprefix("src/")
        for name in sdist
        if name.startswith(f"src/{PACKAGE}/")
    }
    for name in sorted(sdist):
        if name not in SDIST_FILES and not name.startswith(f"src/{PACKAGE}/"):
            errors.append(f"{sdists[0].name}: unexpected file {name}")
    for name in sorted(SDIST_FILES - sdist):
        errors.append(f"{sdists[0].name}: missing file {name}")

    wheel = wheel_names(wheels[0])
    wheel_package = {name for name in wheel if name.startswith(f"{PACKAGE}/")}
    for name in sorted(wheel - wheel_package):
        if not name.split("/")[0].endswith(".dist-info"):
            errors.append(f"{wheels[0].name}: unexpected file {name}")

    # Two empty packages would otherwise agree with each other and pass.
    for name in REQUIRED_PACKAGE_FILES - wheel_package:
        errors.append(f"{wheels[0].name}: missing file {name}")

    for name in sorted(sdist_package ^ wheel_package):
        only_in = sdists[0].name if name in sdist_package else wheels[0].name
        errors.append(f"{name} is only in {only_in}")

    for error in errors:
        print(f"ERROR: {error}")
    if not errors:
        print(
            f"OK: {sdists[0].name} ({len(sdist)} files), "
            f"{wheels[0].name} ({len(wheel)} files)"
        )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "dist")))
