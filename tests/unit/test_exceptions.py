"""Unit tests for exceptions.py module."""

from purjo.exceptions import ConfigurationError
from purjo.exceptions import DeploymentError
from purjo.exceptions import EnvironmentError
from purjo.exceptions import PurjoError
from purjo.exceptions import RobotExecutionError
from purjo.exceptions import SerializationError
import pytest


class TestPurjoError:
    """Tests for PurjoError base exception."""

    def test_purjo_error_is_exception(self) -> None:
        """Test that PurjoError inherits from Exception."""
        assert issubclass(PurjoError, Exception)

    def test_purjo_error_can_be_raised(self) -> None:
        """Test that PurjoError can be raised and caught."""
        with pytest.raises(PurjoError):
            raise PurjoError("Test error")

    def test_purjo_error_message(self) -> None:
        """Test that PurjoError preserves error message."""
        error = PurjoError("Custom error message")
        assert str(error) == "Custom error message"


class TestEnvironmentError:
    """Tests for EnvironmentError exception."""

    def test_environment_error_inherits_from_purjo_error(self) -> None:
        """Test that EnvironmentError inherits from PurjoError."""
        assert issubclass(EnvironmentError, PurjoError)

    def test_environment_error_can_be_raised(self) -> None:
        """Test that EnvironmentError can be raised and caught."""
        with pytest.raises(EnvironmentError):
            raise EnvironmentError("Missing executable")

    def test_environment_error_caught_as_purjo_error(self) -> None:
        """Test that EnvironmentError can be caught as PurjoError."""
        with pytest.raises(PurjoError):
            raise EnvironmentError("Missing executable")


class TestRobotExecutionError:
    """Tests for RobotExecutionError exception."""

    def test_robot_execution_error_inherits_from_purjo_error(self) -> None:
        """Test that RobotExecutionError inherits from PurjoError."""
        assert issubclass(RobotExecutionError, PurjoError)

    def test_robot_execution_error_can_be_raised(self) -> None:
        """Test that RobotExecutionError can be raised and caught."""
        with pytest.raises(RobotExecutionError):
            raise RobotExecutionError("Test failed")

    def test_robot_execution_error_caught_as_purjo_error(self) -> None:
        """Test that RobotExecutionError can be caught as PurjoError."""
        with pytest.raises(PurjoError):
            raise RobotExecutionError("Test failed")


class TestDeploymentError:
    """Tests for DeploymentError exception."""

    def test_deployment_error_inherits_from_purjo_error(self) -> None:
        """Test that DeploymentError inherits from PurjoError."""
        assert issubclass(DeploymentError, PurjoError)

    def test_deployment_error_can_be_raised(self) -> None:
        """Test that DeploymentError can be raised and caught."""
        with pytest.raises(DeploymentError):
            raise DeploymentError("Deployment failed")

    def test_deployment_error_caught_as_purjo_error(self) -> None:
        """Test that DeploymentError can be caught as PurjoError."""
        with pytest.raises(PurjoError):
            raise DeploymentError("Deployment failed")


class TestSerializationError:
    """Tests for SerializationError exception."""

    def test_serialization_error_inherits_from_purjo_error(self) -> None:
        """Test that SerializationError inherits from PurjoError."""
        assert issubclass(SerializationError, PurjoError)

    def test_serialization_error_can_be_raised(self) -> None:
        """Test that SerializationError can be raised and caught."""
        with pytest.raises(SerializationError):
            raise SerializationError("Invalid type")

    def test_serialization_error_caught_as_purjo_error(self) -> None:
        """Test that SerializationError can be caught as PurjoError."""
        with pytest.raises(PurjoError):
            raise SerializationError("Invalid type")


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_configuration_error_inherits_from_purjo_error(self) -> None:
        """Test that ConfigurationError inherits from PurjoError."""
        assert issubclass(ConfigurationError, PurjoError)

    def test_configuration_error_can_be_raised(self) -> None:
        """Test that ConfigurationError can be raised and caught."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Invalid config")

    def test_configuration_error_caught_as_purjo_error(self) -> None:
        """Test that ConfigurationError can be caught as PurjoError."""
        with pytest.raises(PurjoError):
            raise ConfigurationError("Invalid config")


class TestExceptionHierarchy:
    """Tests for the exception hierarchy."""

    def test_all_exceptions_are_purjo_errors(self) -> None:
        """Test that all custom exceptions inherit from PurjoError."""
        exceptions = [
            EnvironmentError,
            RobotExecutionError,
            DeploymentError,
            SerializationError,
            ConfigurationError,
        ]
        for exc in exceptions:
            assert issubclass(exc, PurjoError)

    def test_purjo_error_is_base_exception(self) -> None:
        """Test that PurjoError is the base for all custom exceptions."""
        assert issubclass(PurjoError, Exception)
        assert not issubclass(PurjoError, BaseException) or issubclass(
            PurjoError, Exception
        )
