"""Unit tests for config.py module.

Related User Stories:
- US-002: Configure engine URL
- US-005: Configure polling timeout
- US-006: Set lock TTL
- US-007: Control max jobs
- US-008: Set worker ID
- US-009: Control failure behavior

Related ADRs:
- ADR-003: Architecture overview
"""

from purjo.config import OnFail
from purjo.config import Settings
from purjo.config import settings
from unittest.mock import patch
import os
import pytest


class TestOnFail:
    """Tests for OnFail enum.

    Related: US-009
    """

    def test_enum_values(self) -> None:
        """Test OnFail enum values."""
        assert OnFail.FAIL == "FAIL"
        assert OnFail.COMPLETE == "COMPLETE"
        assert OnFail.ERROR == "ERROR"

    def test_enum_members(self) -> None:
        """Test enum members."""
        assert len(OnFail) == 3
        assert OnFail.FAIL in OnFail
        assert OnFail.COMPLETE in OnFail
        assert OnFail.ERROR in OnFail

    def test_string_comparison(self) -> None:
        """Test string comparison."""
        assert OnFail.FAIL == "FAIL"
        assert OnFail.COMPLETE.value == "COMPLETE"


class TestSettings:
    """Tests for Settings class.

    Related: US-005, US-006, US-007, US-008
    """

    def test_default_values(self) -> None:
        """Test default values."""
        test_settings = Settings()

        assert test_settings.TASKS_TOPIC == "robotframework"
        assert test_settings.TASKS_MAX_JOBS == 1
        assert test_settings.BUSINESS_KEY == "businessKey"
        assert test_settings.UV_EXECUTABLE == "uv"
        assert test_settings.ROBOT_EXECUTABLE == "robot"

    def test_environment_variable_override_tasks_topic(self) -> None:
        """Test TASKS_TOPIC environment variable override."""
        with patch.dict(os.environ, {"TASKS_TOPIC": "custom-topic"}):
            test_settings = Settings()
            assert test_settings.TASKS_TOPIC == "custom-topic"

    def test_environment_variable_override_tasks_max_jobs(self) -> None:
        """Test TASKS_MAX_JOBS environment variable override."""
        with patch.dict(os.environ, {"TASKS_MAX_JOBS": "5"}):
            test_settings = Settings()
            assert test_settings.TASKS_MAX_JOBS == 5

    def test_environment_variable_override_business_key(self) -> None:
        """Test BUSINESS_KEY environment variable override."""
        with patch.dict(os.environ, {"BUSINESS_KEY": "customKey"}):
            test_settings = Settings()
            assert test_settings.BUSINESS_KEY == "customKey"

    def test_environment_variable_override_uv_executable(self) -> None:
        """Test UV_EXECUTABLE environment variable override."""
        with patch.dict(os.environ, {"UV_EXECUTABLE": "/usr/local/bin/uv"}):
            test_settings = Settings()
            assert test_settings.UV_EXECUTABLE == "/usr/local/bin/uv"

    def test_environment_variable_override_robot_executable(self) -> None:
        """Test ROBOT_EXECUTABLE environment variable override."""
        with patch.dict(os.environ, {"ROBOT_EXECUTABLE": "/usr/local/bin/robot"}):
            test_settings = Settings()
            assert test_settings.ROBOT_EXECUTABLE == "/usr/local/bin/robot"

    def test_multiple_environment_overrides(self) -> None:
        """Test multiple environment variable overrides."""
        env_overrides = {
            "TASKS_TOPIC": "custom-topic",
            "TASKS_MAX_JOBS": "10",
            "BUSINESS_KEY": "myBusinessKey",
        }

        with patch.dict(os.environ, env_overrides):
            test_settings = Settings()
            assert test_settings.TASKS_TOPIC == "custom-topic"
            assert test_settings.TASKS_MAX_JOBS == 10
            assert test_settings.BUSINESS_KEY == "myBusinessKey"

    def test_invalid_max_jobs_type(self) -> None:
        """Test invalid TASKS_MAX_JOBS type."""
        with patch.dict(os.environ, {"TASKS_MAX_JOBS": "not_a_number"}):
            with pytest.raises(Exception):  # Pydantic ValidationError
                Settings()


class TestGlobalSettings:
    """Tests for global settings instance."""

    def test_global_settings_instance(self) -> None:
        """Test global settings instance."""
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_global_settings_defaults(self) -> None:
        """Test global settings has default values."""
        # Note: This depends on current environment variables
        assert hasattr(settings, "TASKS_TOPIC")
        assert hasattr(settings, "TASKS_MAX_JOBS")
        assert hasattr(settings, "BUSINESS_KEY")
        assert hasattr(settings, "UV_EXECUTABLE")
        assert hasattr(settings, "ROBOT_EXECUTABLE")

    def test_settings_is_basemodel(self) -> None:
        """Test Settings inherits from BaseSettings."""
        from pydantic_settings import BaseSettings

        assert isinstance(settings, BaseSettings)


class TestSettingsImmutability:
    """Tests for settings immutability and behavior."""

    def test_settings_can_be_modified(self) -> None:
        """Test that settings instance can be modified (not frozen by default)."""
        test_settings = Settings()
        original_topic = test_settings.TASKS_TOPIC

        # Pydantic models are mutable by default
        test_settings.TASKS_TOPIC = "new-topic"
        assert test_settings.TASKS_TOPIC == "new-topic"

        # Restore original
        test_settings.TASKS_TOPIC = original_topic

    def test_settings_dict_export(self) -> None:
        """Test exporting settings as dict."""
        test_settings = Settings()
        settings_dict = test_settings.model_dump()

        assert isinstance(settings_dict, dict)
        assert "TASKS_TOPIC" in settings_dict
        assert "TASKS_MAX_JOBS" in settings_dict
        assert settings_dict["TASKS_TOPIC"] == test_settings.TASKS_TOPIC


class TestSettingsEdgeCases:
    """Tests for edge cases in settings."""

    def test_empty_string_environment_variable(self) -> None:
        """Test empty string environment variable."""
        from pydantic import ValidationError

        with patch.dict(os.environ, {"TASKS_TOPIC": ""}):
            with pytest.raises(ValidationError):
                Settings()

    def test_zero_max_jobs(self) -> None:
        """Test zero TASKS_MAX_JOBS."""
        from pydantic import ValidationError

        with patch.dict(os.environ, {"TASKS_MAX_JOBS": "0"}):
            with pytest.raises(ValidationError):
                Settings()

    def test_negative_max_jobs(self) -> None:
        """Test negative TASKS_MAX_JOBS."""
        from pydantic import ValidationError

        with patch.dict(os.environ, {"TASKS_MAX_JOBS": "-1"}):
            with pytest.raises(ValidationError):
                Settings()

    def test_very_large_max_jobs(self) -> None:
        """Test very large TASKS_MAX_JOBS."""
        with patch.dict(os.environ, {"TASKS_MAX_JOBS": "1000000"}):
            test_settings = Settings()
            assert test_settings.TASKS_MAX_JOBS == 1000000
