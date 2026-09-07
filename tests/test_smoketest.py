"""Test project successful import.

Related ADRs:
- ADR-003: Architecture overview
"""


def test_import() -> None:
    """Test project successful import."""
    from purjo import main

    assert main
