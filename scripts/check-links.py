#!/usr/bin/env python3
"""Link checker for US-xxx and ADR-xxx references in test files.

This script validates that:
1. All test files reference at least one US-xxx or ADR-xxx
2. All referenced user stories exist in ./agents/stories/
3. All referenced ADRs exist in ./agents/adrs/
4. Reports orphaned tests (no US/ADR reference)
5. Reports missing user stories (referenced but not defined)
6. Reports missing ADRs (referenced but not defined)

Exit codes:
- 0: All checks passed
- 1: Conformance issues found
"""

from pathlib import Path
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple
import re
import sys


def find_references_in_file(file_path: Path) -> Tuple[Set[str], Set[str]]:
    """Find all US-xxx and ADR-xxx references in a file.

    Returns:
        Tuple of (user_story_refs, adr_refs)
    """
    content = file_path.read_text()

    # Match US-XXX patterns (case-insensitive)
    us_pattern = re.compile(r"\bUS-\d{3}\b", re.IGNORECASE)
    us_refs = set(us_pattern.findall(content))

    # Match ADR-XXX patterns (case-insensitive)
    adr_pattern = re.compile(r"\bADR-\d{3}\b", re.IGNORECASE)
    adr_refs = set(adr_pattern.findall(content))

    return us_refs, adr_refs


def get_existing_stories(stories_dir: Path) -> Set[str]:
    """Get all existing user story IDs from filenames."""
    stories = set()
    if not stories_dir.exists():
        return stories

    for story_file in stories_dir.glob("US-*.md"):
        # Extract US-XXX from filename
        match = re.match(r"(US-\d{3})", story_file.name, re.IGNORECASE)
        if match:
            stories.add(match.group(1).upper())

    return stories


def get_existing_adrs(adrs_dir: Path) -> Set[str]:
    """Get all existing ADR IDs from filenames."""
    adrs = set()
    if not adrs_dir.exists():
        return adrs

    for adr_file in adrs_dir.glob("ADR-*.md"):
        # Extract ADR-XXX from filename
        match = re.match(r"(ADR-\d{3})", adr_file.name, re.IGNORECASE)
        if match:
            adrs.add(match.group(1).upper())

    return adrs


def find_test_files(tests_dir: Path) -> List[Path]:
    """Find all test files in the tests directory."""
    test_files = []

    # Find all Python test files
    for pattern in ["test_*.py", "*_test.py"]:
        test_files.extend(tests_dir.rglob(pattern))

    return sorted(test_files)


def check_links() -> int:
    """Run the link checker and return exit code."""
    # Determine project root (parent of script directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    tests_dir = project_root / "tests"
    stories_dir = project_root / "agents" / "stories"
    adrs_dir = project_root / "agents" / "adrs"

    # Get existing stories and ADRs
    existing_stories = get_existing_stories(stories_dir)
    existing_adrs = get_existing_adrs(adrs_dir)

    print(f"Found {len(existing_stories)} user stories")
    print(f"Found {len(existing_adrs)} ADRs")
    print()

    # Track all referenced items
    all_referenced_stories: Set[str] = set()
    all_referenced_adrs: Set[str] = set()

    # Track issues
    orphaned_tests: List[Path] = []
    files_with_issues: Dict[Path, Dict[str, List[str]]] = {}

    # Process each test file
    test_files = find_test_files(tests_dir)
    print(f"Checking {len(test_files)} test files...")
    print()

    for test_file in test_files:
        us_refs, adr_refs = find_references_in_file(test_file)

        # Normalize to uppercase
        us_refs = {ref.upper() for ref in us_refs}
        adr_refs = {ref.upper() for ref in adr_refs}

        # Track all references
        all_referenced_stories.update(us_refs)
        all_referenced_adrs.update(adr_refs)

        # Check if file has any references
        if not us_refs and not adr_refs:
            orphaned_tests.append(test_file)
            continue

        # Check for missing stories/ADRs
        missing_stories = us_refs - existing_stories
        missing_adrs = adr_refs - existing_adrs

        if missing_stories or missing_adrs:
            issues = {}
            if missing_stories:
                issues["missing_stories"] = sorted(missing_stories)
            if missing_adrs:
                issues["missing_adrs"] = sorted(missing_adrs)
            files_with_issues[test_file] = issues

    # Report findings
    has_issues = False

    if orphaned_tests:
        has_issues = True
        print("❌ Orphaned tests (no US/ADR references):")
        for test_file in orphaned_tests:
            rel_path = test_file.relative_to(project_root)
            print(f"  - {rel_path}")
        print()

    if files_with_issues:
        has_issues = True
        print("❌ Tests with missing references:")
        for test_file, issues in files_with_issues.items():
            rel_path = test_file.relative_to(project_root)
            print(f"  {rel_path}:")
            if "missing_stories" in issues:
                print(f"    Missing stories: {', '.join(issues['missing_stories'])}")
            if "missing_adrs" in issues:
                print(f"    Missing ADRs: {', '.join(issues['missing_adrs'])}")
        print()

    # Check for unreferenced stories/ADRs (informational, not an error)
    unreferenced_stories = existing_stories - all_referenced_stories
    unreferenced_adrs = existing_adrs - all_referenced_adrs

    if unreferenced_stories:
        print("ℹ️  Unreferenced user stories (no tests reference these):")
        for story in sorted(unreferenced_stories):
            print(f"  - {story}")
        print()

    if unreferenced_adrs:
        print("ℹ️  Unreferenced ADRs (no tests reference these):")
        for adr in sorted(unreferenced_adrs):
            print(f"  - {adr}")
        print()

    # Summary
    if not has_issues:
        print("✅ All link checks passed!")
        print(f"  - {len(test_files)} test files checked")
        print(f"  - {len(test_files) - len(orphaned_tests)} files with references")
        print(f"  - {len(all_referenced_stories)} unique user stories referenced")
        print(f"  - {len(all_referenced_adrs)} unique ADRs referenced")
        return 0
    else:
        print("❌ Link check failed!")
        print(f"  - {len(orphaned_tests)} orphaned test files")
        print(f"  - {len(files_with_issues)} files with missing references")
        return 1


if __name__ == "__main__":
    sys.exit(check_links())
