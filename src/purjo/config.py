"""Configuration and settings for purjo.

This module defines application-wide configuration including:
- OnFail enum for task failure handling
- Default values for engine connection and worker settings
- Magic strings used across the application
- Settings class for runtime configuration
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings
import enum


class OnFail(str, enum.Enum):
    """Enum defining how to handle task failures.

    FAIL: Mark the external task as failed with a BPMN error.
    COMPLETE: Complete the external task despite failure.
    ERROR: Mark the external task as having a technical error.
    """

    FAIL = "FAIL"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


# Default engine and worker configuration
DEFAULT_ENGINE_BASE_URL = "http://localhost:8080/engine-rest"
DEFAULT_WORKER_ID = "operaton-robot-runner"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_POLL_TTL_SECONDS = 10
DEFAULT_LOCK_TTL_SECONDS = 30
DEFAULT_DEPLOYMENT_NAME = "pur(jo) deployment"

# Magic strings used across the application
DEPLOYMENT_SOURCE = "pur(jo)"
FIELD_DEPLOYMENT_NAME = "deployment-name"
FIELD_DEPLOYMENT_SOURCE = "deployment-source"
FIELD_DEPLOY_CHANGED_ONLY = "deploy-changed-only"
CONTENT_TYPE_OCTET_STREAM = "application/octet-stream"


class Settings(BaseSettings):
    TASKS_TOPIC: str = "robotframework"
    TASKS_MAX_JOBS: int = 1
    BUSINESS_KEY: str = "businessKey"
    UV_EXECUTABLE: str = "uv"
    ROBOT_EXECUTABLE: str = "robot"

    @field_validator("TASKS_MAX_JOBS")
    @classmethod
    def validate_max_jobs(cls, v: int) -> int:
        """Validate that TASKS_MAX_JOBS is at least 1."""
        if v < 1:
            raise ValueError("TASKS_MAX_JOBS must be at least 1")
        return v

    @field_validator("TASKS_TOPIC", "BUSINESS_KEY", "UV_EXECUTABLE", "ROBOT_EXECUTABLE")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        """Validate that string settings are not empty."""
        if not v or not v.strip():
            raise ValueError("Setting must not be empty")
        return v


settings = Settings()


__all__ = ["settings", "OnFail"]
