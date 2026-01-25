"""Custom exception hierarchy for purjo.

This module defines custom exceptions used throughout the purjo package
for better error handling and reporting.
"""


class PurjoError(Exception):
    """Base exception for all purjo-related errors."""

    pass


class EnvironmentError(PurjoError):
    """Exception raised for environment-related errors.

    This includes issues with Python environment setup, missing executables,
    or invalid environment configurations.
    """

    pass


class RobotExecutionError(PurjoError):
    """Exception raised when Robot Framework execution fails.

    This includes test failures, syntax errors in robot files,
    or runtime errors during test execution.
    """

    pass


class DeploymentError(PurjoError):
    """Exception raised when BPMN deployment fails.

    This includes issues with deployment to the Operaton engine,
    invalid BPMN files, or connection errors.
    """

    pass


class SerializationError(PurjoError):
    """Exception raised when serialization/deserialization fails.

    This includes issues converting between Python types and Operaton
    variable types, or JSON serialization problems.
    """

    pass


class ConfigurationError(PurjoError):
    """Exception raised for configuration-related errors.

    This includes invalid settings, missing required configuration,
    or conflicting configuration values.
    """

    pass
