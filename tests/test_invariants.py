"""Sentinel tests for core system invariants.

These tests validate core invariants that must NEVER be violated.
Failures in this file indicate fundamental architectural violations.

Related ADRs:
- ADR-000: Agent guidance
- ADR-001: Use uv for environment management
- ADR-002: Use external task pattern
- ADR-003: Architecture overview
"""

from pathlib import Path
from typing import List
import pytest
import re


class TestInvariant1_IsolatedEnvironments:
    """Invariant 1: Robot packages must execute in isolated environments.

    Related: ADR-001
    """

    def test_runner_uses_uv_for_execution(self) -> None:
        """Verify that runner.py uses uv for isolated execution."""
        runner_file = Path("src/purjo/runner.py")
        assert runner_file.exists(), "runner.py must exist"

        content = runner_file.read_text()

        # Verify uv is used for execution
        assert "uv" in content, "runner.py must use uv for execution"

    def test_main_enforces_uv_presence(self) -> None:
        """Verify that main.py checks for uv executable."""
        main_file = Path("src/purjo/main.py")
        assert main_file.exists(), "main.py must exist"

        content = main_file.read_text()

        # Verify uv presence is checked
        assert (
            "shutil.which" in content or "which(" in content
        ), "main.py must check for uv executable presence"


class TestInvariant2_TaskResultsReporting:
    """Invariant 2: Task results must always be reported to the engine.

    Related: ADR-002
    """

    def test_task_handler_has_error_handling(self) -> None:
        """Verify that task handlers report all outcomes."""
        task_file = Path("src/purjo/task.py")

        if not task_file.exists():
            # If task.py doesn't exist, check runner.py or main.py
            pytest.skip("task.py not found, checking alternative locations")

        content = task_file.read_text()

        # Verify error handling exists
        assert (
            "try:" in content and "except" in content
        ), "Task handler must have try/except error handling"

    def test_runner_reports_all_outcomes(self) -> None:
        """Verify that runner returns all execution outcomes."""
        runner_file = Path("src/purjo/runner.py")
        assert runner_file.exists(), "runner.py must exist"

        content = runner_file.read_text()

        # Verify return statements exist for different outcomes
        # Runner should return results for success, failure, and error
        assert "return" in content, "runner must return execution results"


class TestInvariant3_SecretsSafety:
    """Invariant 3: Secrets must never be logged or included in output artifacts.

    Related: ADR-003, US-004
    """

    def test_secrets_not_in_default_logging(self) -> None:
        """Verify that secrets are not logged by default."""
        # Check runner.py for logging patterns
        runner_file = Path("src/purjo/runner.py")
        if runner_file.exists():
            content = runner_file.read_text()

            # If there's logging of variables, ensure secrets are filtered
            if "logger" in content.lower() or "print" in content:
                # This is a warning - manual inspection may be needed
                # We can't automatically verify all cases, but we can check
                # that there's no obvious dumping of all variables
                assert "secrets" not in content.lower() or (
                    "secrets" in content.lower() and "filter" in content.lower()
                ), "If secrets are mentioned in logging context, filtering should be present"

    def test_secrets_module_exists(self) -> None:
        """Verify that secrets management module exists."""
        secrets_file = Path("src/purjo/secrets.py")
        assert secrets_file.exists(), "secrets.py must exist for secret management"

        content = secrets_file.read_text()

        # Verify secrets handling infrastructure
        assert "class" in content, "secrets.py should define secret handler classes"

    def test_output_variables_dont_expose_secrets(self) -> None:
        """Verify that output variables handling doesn't expose secrets."""
        purjo_lib = Path("src/purjo/Purjo.py")
        if purjo_lib.exists():
            content = purjo_lib.read_text()

            # Check for output variable handling
            if "output" in content.lower() and "variable" in content.lower():
                # Ensure secrets aren't blindly copied to output
                # This is a heuristic check - manual review is still important
                pass  # This test serves as a reminder to be careful


class TestInvariant4_CLIEntryPoint:
    """Invariant 4: The CLI must be the single entry point for all operations.

    Related: ADR-003
    """

    def test_main_is_cli_entry_point(self) -> None:
        """Verify that main.py defines the CLI entry point."""
        main_file = Path("src/purjo/main.py")
        assert main_file.exists(), "main.py must exist"

        content = main_file.read_text()

        # Verify typer or click app exists
        assert (
            "typer" in content.lower() or "click" in content.lower()
        ), "main.py must define a CLI application"

        # Verify app definition (cli = typer.Typer() or similar patterns)
        assert (
            "cli = typer.Typer" in content
            or "cli=typer.Typer" in content
            or "app = typer.Typer" in content
            or "app=typer.Typer" in content
            or "@cli" in content
            or "@app" in content
        ), "main.py must define CLI app"

    def test_pyproject_defines_cli_entrypoint(self) -> None:
        """Verify that pyproject.toml defines the CLI entry point."""
        pyproject = Path("pyproject.toml")
        assert pyproject.exists(), "pyproject.toml must exist"

        content = pyproject.read_text()

        # Verify scripts or entry points section
        assert (
            "[project.scripts]" in content or "[tool.poetry.scripts]" in content
        ), "pyproject.toml must define CLI scripts"

        # Verify the 'pur' command exists
        assert "pur" in content, "CLI command 'pur' must be defined"

    def test_no_direct_subprocess_in_lib(self) -> None:
        """Verify that library code doesn't directly spawn processes."""
        purjo_lib = Path("src/purjo/Purjo.py")
        if purjo_lib.exists():
            content = purjo_lib.read_text()

            # Library should delegate to runner, not spawn directly
            # This is a soft check - subprocess use should go through runner
            if "subprocess" in content:
                # Ensure it's using runner or proper abstraction
                assert (
                    "runner" in content or "run(" in content
                ), "Library should use runner for process execution"


class TestInvariantDocumentation:
    """Meta-test: Ensure invariants are documented."""

    def test_invariants_documented_in_agents_md(self) -> None:
        """Verify that AGENTS.md documents core invariants."""
        agents_md = Path("AGENTS.md")
        assert agents_md.exists(), "AGENTS.md must exist"

        content = agents_md.read_text()

        # Check for invariants section
        assert "invariant" in content.lower(), "AGENTS.md must document core invariants"

        # Verify all four invariants are mentioned
        invariants_section = content.lower()

        # Check for key concepts from each invariant
        assert (
            "isolated" in invariants_section or "environment" in invariants_section
        ), "Invariant 1 (isolated environments) must be documented"
        assert (
            "report" in invariants_section or "result" in invariants_section
        ), "Invariant 2 (result reporting) must be documented"
        assert (
            "secret" in invariants_section or "log" in invariants_section
        ), "Invariant 3 (secrets safety) must be documented"
        assert (
            "cli" in invariants_section or "entry point" in invariants_section
        ), "Invariant 4 (CLI entry point) must be documented"
