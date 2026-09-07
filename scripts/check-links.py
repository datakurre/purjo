#!/usr/bin/env python3
"""Cross-reference checker for the purjo agent documentation system.

Validates bidirectional links between tests, user stories, ADRs,
and documentation files.  Ensures the agent guidance system stays
connected and navigable.

Checks performed:
 1. Test files → US/ADR references exist and use valid 3-digit IDs
 2. User stories → test file references resolve to real paths
 3. User stories → ADR references use valid 3-digit IDs and exist
 4. ADR files  → ADR cross-references use valid 3-digit IDs
 5. Markdown relative links resolve to existing files
 6. agents/index.md lists every ADR
 7. agents/stories/README.md lists every story
 8. Detects 4-digit ADR references (ADR-0001 → ADR-001)
 9. Unreferenced stories/ADRs (informational)

Exit codes:
 0 — no errors  (warnings are non-blocking)
 1 — one or more errors found
"""

from pathlib import Path
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Set
from typing import Tuple
import re
import sys

# ── data types ────────────────────────────────────────────────────────────


class Issue(NamedTuple):
    file: Path
    severity: str  # "error" | "warning"
    message: str


# ── helpers ───────────────────────────────────────────────────────────────


def rel(path: Path, root: Path) -> str:
    """Short relative path for display."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


# ── discovery ─────────────────────────────────────────────────────────────


def get_existing_stories(stories_dir: Path) -> Dict[str, Path]:
    """Map US-XXX → file path (uppercase, 3-digit)."""
    out: Dict[str, Path] = {}
    if stories_dir.exists():
        for f in stories_dir.glob("US-*.md"):
            m = re.match(r"(US-\d{3})", f.name, re.IGNORECASE)
            if m:
                out[m.group(1).upper()] = f
    return out


def get_existing_adrs(adrs_dir: Path) -> Dict[str, Path]:
    """Map ADR-XXX → file path (uppercase, 3-digit)."""
    out: Dict[str, Path] = {}
    if adrs_dir.exists():
        for f in adrs_dir.glob("ADR-*.md"):
            m = re.match(r"(ADR-\d{3})", f.name, re.IGNORECASE)
            if m:
                out[m.group(1).upper()] = f
    return out


def find_test_files(tests_dir: Path) -> List[Path]:
    files: List[Path] = []
    for pat in ("test_*.py", "*_test.py"):
        files.extend(tests_dir.rglob(pat))
    return sorted(files)


def find_markdown_files(root: Path, paths: List[str]) -> List[Path]:
    """Collect markdown files from directories *and* single files."""
    files: List[Path] = []
    for p in paths:
        target = root / p
        if target.is_file() and target.suffix == ".md":
            files.append(target)
        elif target.is_dir():
            files.extend(target.rglob("*.md"))
    return sorted(set(files))


# ── reference extraction ──────────────────────────────────────────────────


def find_us_refs(text: str) -> Set[str]:
    return {m.upper() for m in re.findall(r"\bUS-\d{3}\b", text, re.IGNORECASE)}


def find_adr3_refs(text: str) -> Set[str]:
    """3-digit ADR references (the correct format)."""
    return {m.upper() for m in re.findall(r"\bADR-\d{3}\b", text, re.IGNORECASE)}


def find_adr4_refs(text: str) -> List[str]:
    """4-digit ADR references (the wrong format)."""
    return re.findall(r"\bADR-\d{4}\b", text, re.IGNORECASE)


def find_md_links(text: str) -> List[Tuple[str, str]]:
    """[text](./relative/path) links."""
    return [
        (t, target) for t, target in re.findall(r"\[([^\]]*)\]\((\.[^\)]+)\)", text)
    ]


def find_test_path_refs(text: str) -> List[str]:
    """Paths on 'Related Tests:' lines."""
    paths: List[str] = []
    for line in text.splitlines():
        if "related tests:" not in line.lower():
            continue
        _, _, value = line.partition(":")
        # Strip markdown bold markers and whitespace
        value = value.replace("*", " ")
        for part in value.split(","):
            part = part.strip()
            if part.startswith("tests/"):
                paths.append(part)
    return paths


# ── checks ────────────────────────────────────────────────────────────────


def check_test_references(
    test_files: List[Path],
    stories: Dict[str, Path],
    adrs: Dict[str, Path],
    root: Path,
) -> Tuple[List[Issue], Set[str], Set[str]]:
    issues: List[Issue] = []
    all_us: Set[str] = set()
    all_adr: Set[str] = set()

    for tf in test_files:
        content = tf.read_text()
        us = find_us_refs(content)
        adr = find_adr3_refs(content)
        all_us.update(us)
        all_adr.update(adr)

        if not us and not adr:
            issues.append(
                Issue(tf, "warning", "No US-xxx or ADR-xxx references in docstring")
            )
            continue

        for r in sorted(us - set(stories)):
            issues.append(
                Issue(tf, "error", f"References {r} — story file does not exist")
            )
        for r in sorted(adr - set(adrs)):
            issues.append(
                Issue(tf, "error", f"References {r} — ADR file does not exist")
            )
        for bad in find_adr4_refs(content):
            issues.append(
                Issue(
                    tf,
                    "error",
                    f"4-digit ADR reference '{bad}' — use 'ADR-{bad[-3:]}' instead",
                )
            )

    return issues, all_us, all_adr


def check_story_references(
    stories: Dict[str, Path],
    adrs: Dict[str, Path],
    root: Path,
) -> List[Issue]:
    issues: List[Issue] = []

    for sid, spath in sorted(stories.items()):
        content = spath.read_text()

        # 4-digit ADR refs
        for bad in find_adr4_refs(content):
            issues.append(
                Issue(
                    spath,
                    "error",
                    f"4-digit ADR reference '{bad}' — use 'ADR-{bad[-3:]}' instead",
                )
            )

        # 3-digit ADR refs to non-existent ADRs
        for r in sorted(find_adr3_refs(content) - set(adrs)):
            issues.append(
                Issue(spath, "error", f"References {r} — ADR file does not exist")
            )

        # Test file / directory paths
        for tpath in find_test_path_refs(content):
            full = root / tpath
            # Accept if file exists, or directory exists (with or without trailing /)
            if not full.exists() and not full.with_suffix("").is_dir():
                issues.append(
                    Issue(
                        spath, "error", f"Related Tests path '{tpath}' does not exist"
                    )
                )

    return issues


def check_adr_cross_references(
    adrs: Dict[str, Path],
    root: Path,
) -> List[Issue]:
    issues: List[Issue] = []

    for aid, apath in sorted(adrs.items()):
        content = apath.read_text()

        for bad in find_adr4_refs(content):
            issues.append(
                Issue(
                    apath,
                    "error",
                    f"4-digit ADR reference '{bad}' — use 'ADR-{bad[-3:]}' instead",
                )
            )

        for r in sorted(find_adr3_refs(content) - set(adrs) - {aid}):
            issues.append(
                Issue(apath, "error", f"References {r} — ADR file does not exist")
            )

    return issues


def check_markdown_links(
    md_files: List[Path],
    root: Path,
) -> List[Issue]:
    issues: List[Issue] = []

    for mf in md_files:
        content = mf.read_text()
        parent = mf.parent

        for text, target in find_md_links(content):
            clean = target.split("#")[0]
            if not clean:
                continue
            resolved = (parent / clean).resolve()
            if not resolved.exists():
                issues.append(
                    Issue(
                        mf, "error", f"Broken link [{text}]({target}) — file not found"
                    )
                )

    return issues


def check_index_completeness(
    index_file: Path,
    adrs: Dict[str, Path],
) -> List[Issue]:
    issues: List[Issue] = []
    if not index_file.exists():
        issues.append(Issue(index_file, "warning", "File does not exist"))
        return issues

    content = index_file.read_text().upper()
    for aid in sorted(adrs):
        if aid not in content:
            issues.append(Issue(index_file, "warning", f"{aid} is not listed"))

    return issues


def check_story_index_completeness(
    readme: Path,
    stories: Dict[str, Path],
) -> List[Issue]:
    issues: List[Issue] = []
    if not readme.exists():
        issues.append(Issue(readme, "warning", "File does not exist"))
        return issues

    content = readme.read_text().upper()
    for sid in sorted(stories):
        if sid not in content:
            issues.append(Issue(readme, "warning", f"{sid} is not listed"))

    return issues


def check_unreferenced(
    stories: Dict[str, Path],
    adrs: Dict[str, Path],
    us_from_tests: Set[str],
    adr_from_tests: Set[str],
) -> List[Issue]:
    issues: List[Issue] = []
    for sid in sorted(set(stories) - us_from_tests):
        issues.append(
            Issue(stories[sid], "warning", f"{sid} not referenced by any test")
        )
    for aid in sorted(set(adrs) - adr_from_tests):
        issues.append(Issue(adrs[aid], "warning", f"{aid} not referenced by any test"))
    return issues


# ── main ──────────────────────────────────────────────────────────────────


def check_links() -> int:
    root = Path(__file__).resolve().parent.parent
    tests_dir = root / "tests"
    stories_dir = root / "agents" / "stories"
    adrs_dir = root / "agents" / "adrs"
    agents_dir = root / "agents"

    stories = get_existing_stories(stories_dir)
    adrs = get_existing_adrs(adrs_dir)
    test_files = find_test_files(tests_dir)
    md_files = find_markdown_files(root, ["agents", "AGENTS.md"])

    print(
        f"Scanning {len(test_files)} test files, {len(stories)} stories, "
        f"{len(adrs)} ADRs, {len(md_files)} markdown files\n"
    )

    all_issues: List[Issue] = []

    # 1  tests → stories / ADRs
    test_issues, all_us, all_adr = check_test_references(
        test_files, stories, adrs, root
    )
    all_issues.extend(test_issues)

    # 2  stories → test paths + ADR refs
    all_issues.extend(check_story_references(stories, adrs, root))

    # 3  ADR → ADR cross-refs
    all_issues.extend(check_adr_cross_references(adrs, root))

    # 4  markdown relative links
    all_issues.extend(check_markdown_links(md_files, root))

    # 5  index completeness
    all_issues.extend(check_index_completeness(agents_dir / "index.md", adrs))
    all_issues.extend(
        check_story_index_completeness(stories_dir / "README.md", stories)
    )

    # 6  unreferenced artifacts
    all_issues.extend(check_unreferenced(stories, adrs, all_us, all_adr))

    # ── report ────────────────────────────────────────────────────────

    errors = [i for i in all_issues if i.severity == "error"]
    warnings = [i for i in all_issues if i.severity == "warning"]

    if errors:
        print(f"❌ {len(errors)} error(s):\n")
        for i in errors:
            print(f"  {rel(i.file, root)}: {i.message}")
        print()

    if warnings:
        print(f"⚠️  {len(warnings)} warning(s):\n")
        for i in warnings:
            print(f"  {rel(i.file, root)}: {i.message}")
        print()

    if errors:
        print(f"❌ {len(errors)} error(s), {len(warnings)} warning(s)")
    elif warnings:
        print(f"✅ No errors — {len(warnings)} warning(s)")
    else:
        print("✅ All cross-reference checks passed!")

    print(
        f"   checked {len(test_files)} tests, {len(stories)} stories, "
        f"{len(adrs)} ADRs, {len(md_files)} markdown files"
    )

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(check_links())
