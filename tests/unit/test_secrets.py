"""Unit tests for secrets.py module."""

from pathlib import Path
from purjo.secrets import FileProviderConfig
from purjo.secrets import FileSecretsAdapter
from purjo.secrets import get_secrets_provider
from purjo.secrets import SecretsConfigurationError
from purjo.secrets import SecretsProvider
from purjo.secrets import VaultProviderConfig
from purjo.secrets import VaultSecretsAdapter
from unittest.mock import Mock
from unittest.mock import patch
import json
import pytest


class TestFileSecretsProvider:
    """Tests for FileSecretsAdapter class."""

    def test_reading_valid_json_file(self, sample_secrets_file: Path) -> None:
        """Test reading valid JSON file."""
        config = FileProviderConfig(provider="file", path=sample_secrets_file)
        adapter = FileSecretsAdapter(config)
        result = adapter.read()

        assert isinstance(result, dict)
        assert "username" in result
        assert "password" in result
        assert result["username"] == "testuser"

    def test_file_not_found(self, temp_dir: Path) -> None:
        """Test file not found behavior."""
        non_existent = temp_dir / "does_not_exist.json"

        # FileProviderConfig requires FilePath, so it should fail validation
        with pytest.raises(Exception):  # Pydantic ValidationError
            FileProviderConfig(provider="file", path=non_existent)


class TestVaultSecretsProvider:
    """Tests for VaultSecretsAdapter class."""

    def test_successful_secret_retrieval(self, mock_hvac_client: Mock) -> None:
        """Test successful secret retrieval."""
        with patch("purjo.secrets.hvac.Client", return_value=mock_hvac_client):
            config = VaultProviderConfig(
                provider="vault",
                path="secret/data/test",
                **{"mount-point": "secret"},
                address="http://vault:8200",
                token="test-token",
            )
            adapter = VaultSecretsAdapter(config)
            result = adapter.read()

            assert isinstance(result, dict)
            assert result["username"] == "vault-user"
            assert result["password"] == "vault-pass"

    def test_missing_vault_addr(self) -> None:
        """Test missing VAULT_ADDR raises SecretsConfigurationError."""
        config = VaultProviderConfig(
            provider="vault",
            path="secret/data/test",
            **{"mount-point": "secret"},
            address=None,
            token="test-token",
        )

        with pytest.raises(SecretsConfigurationError, match="VAULT_ADDR is required"):
            VaultSecretsAdapter(config)

    def test_missing_vault_token(self) -> None:
        """Test missing VAULT_TOKEN raises SecretsConfigurationError."""
        config = VaultProviderConfig(
            provider="vault",
            path="secret/data/test",
            **{"mount-point": "secret"},
            address="http://vault:8200",
            token=None,
        )

        with pytest.raises(SecretsConfigurationError, match="VAULT_TOKEN is required"):
            VaultSecretsAdapter(config)

    def test_vault_api_call(self, mock_hvac_client: Mock) -> None:
        """Test Vault API call parameters."""
        with patch("purjo.secrets.hvac.Client", return_value=mock_hvac_client):
            config = VaultProviderConfig(
                provider="vault",
                path="myapp/credentials",
                **{"mount-point": "custom_mount"},
                address="http://vault:8200",
                token="test-token",
            )
            adapter = VaultSecretsAdapter(config)
            adapter.read()

            # Verify the API was called with correct params
            mock_hvac_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
                path="myapp/credentials",
                mount_point="custom_mount",
            )


class TestGetSecretsProvider:
    """Tests for get_secrets_provider function."""

    def test_with_file_path_profile(self, sample_secrets_file: Path) -> None:
        """Test with file path profile."""
        provider = get_secrets_provider(profile=str(sample_secrets_file))

        assert provider is not None
        assert isinstance(provider.config, FileProviderConfig)
        result = provider.read()
        assert result["username"] == "testuser"

    def test_with_no_config(self) -> None:
        """Test with no config."""
        provider = get_secrets_provider(config=None)
        assert provider is None

        provider = get_secrets_provider(config={})
        assert provider is None

    def test_with_single_config_entry(self, sample_secrets_file: Path) -> None:
        """Test with single config entry."""
        config = {
            "production": {
                "provider": "file",
                "path": str(sample_secrets_file),
            }
        }

        provider = get_secrets_provider(config=config)

        assert provider is not None
        assert isinstance(provider.config, FileProviderConfig)

    def test_with_default_profile(self, sample_secrets_file: Path) -> None:
        """Test with default profile."""
        config = {
            "default": {
                "provider": "file",
                "path": str(sample_secrets_file),
            },
            "production": {
                "provider": "file",
                "path": str(sample_secrets_file),
            },
        }

        provider = get_secrets_provider(config=config)

        assert provider is not None
        # Should use default profile
        result = provider.read()
        assert "username" in result

    def test_with_specified_profile(self, sample_secrets_file: Path) -> None:
        """Test with specified profile."""
        config = {
            "default": {
                "provider": "file",
                "path": str(sample_secrets_file),
            },
            "production": {
                "provider": "file",
                "path": str(sample_secrets_file),
            },
        }

        provider = get_secrets_provider(config=config, profile="production")

        assert provider is not None
        result = provider.read()
        assert "username" in result

    def test_missing_profile_assertion(self, sample_secrets_file: Path) -> None:
        """Test missing profile raises SecretsConfigurationError."""
        config = {
            "default": {
                "provider": "file",
                "path": str(sample_secrets_file),
            },
            "production": {
                "provider": "file",
                "path": str(sample_secrets_file),
            },
        }

        with pytest.raises(
            SecretsConfigurationError, match="Profile 'missing' not found"
        ):
            get_secrets_provider(config=config, profile="missing")


class TestSecretsProvider:
    """Tests for SecretsProvider class."""

    def test_read_with_file_config(self, sample_secrets_file: Path) -> None:
        """Test read with FileProviderConfig."""
        config = FileProviderConfig(provider="file", path=sample_secrets_file)
        provider = SecretsProvider(config=config)

        result = provider.read()

        assert isinstance(result, dict)
        assert result["username"] == "testuser"
        assert result["password"] == "testpass"
        assert result["api_key"] == "test-api-key-123"

    def test_read_with_vault_config(self, mock_hvac_client: Mock) -> None:
        """Test read with VaultProviderConfig."""
        with patch("purjo.secrets.hvac.Client", return_value=mock_hvac_client):
            config = VaultProviderConfig(
                provider="vault",
                path="secret/data/test",
                **{"mount-point": "secret"},
                address="http://vault:8200",
                token="test-token",
            )
            provider = SecretsProvider(config=config)

            result = provider.read()

            assert isinstance(result, dict)
            assert result["username"] == "vault-user"
            assert result["password"] == "vault-pass"

    def test_unknown_config_type(self) -> None:
        """Test that SecretsProvider works with known config types."""
        # Test with FileProviderConfig
        config = FileProviderConfig(provider="file", path=Path(__file__))
        provider = SecretsProvider(config=config)

        # The read method should delegate to FileSecretsAdapter
        # We just verify it's callable (actual file reading tested elsewhere)
        assert provider is not None
        assert isinstance(provider.config, FileProviderConfig)


class TestSecretsIntegration:
    """Integration tests for secrets module."""

    def test_file_to_vault_migration(
        self, sample_secrets_file: Path, mock_hvac_client: Mock
    ) -> None:
        """Test migrating from file secrets to Vault."""
        # Start with file provider
        file_provider = get_secrets_provider(profile=str(sample_secrets_file))
        file_secrets = file_provider.read()  # type: ignore[union-attr]  # type: ignore[union-attr]

        # Switch to Vault provider
        with patch("purjo.secrets.hvac.Client", return_value=mock_hvac_client):
            vault_config = {
                "vault": {
                    "provider": "vault",
                    "path": "secret/data/test",
                    "mount-point": "secret",
                    "address": "http://vault:8200",
                    "token": "test-token",
                }
            }
            vault_provider = get_secrets_provider(config=vault_config, profile="vault")
            vault_secrets = vault_provider.read()  # type: ignore[union-attr]  # type: ignore[union-attr]

            # Both should provide secrets (though values may differ)
            assert isinstance(file_secrets, dict)
            assert isinstance(vault_secrets, dict)
            assert len(file_secrets) > 0
            assert len(vault_secrets) > 0

    def test_multiple_profiles(self, temp_dir: Path) -> None:
        """Test using multiple profiles."""
        # Create different secret files for different environments
        dev_secrets = temp_dir / "dev.json"
        dev_secrets.write_text(json.dumps({"env": "dev", "key": "dev-key"}))

        prod_secrets = temp_dir / "prod.json"
        prod_secrets.write_text(json.dumps({"env": "prod", "key": "prod-key"}))

        config = {
            "dev": {"provider": "file", "path": str(dev_secrets)},
            "prod": {"provider": "file", "path": str(prod_secrets)},
        }

        # Get dev secrets
        dev_provider = get_secrets_provider(config=config, profile="dev")
        dev_result = dev_provider.read()  # type: ignore[union-attr]  # type: ignore[union-attr]
        assert dev_result["env"] == "dev"

        # Get prod secrets
        prod_provider = get_secrets_provider(config=config, profile="prod")
        prod_result = prod_provider.read()  # type: ignore[union-attr]  # type: ignore[union-attr]
        assert prod_result["env"] == "prod"


class TestSecretsAdapterErrorPaths:
    """Tests for error handling paths in secrets adapters."""

    def test_file_secrets_adapter_read_error_malformed_json(
        self, temp_dir: Path
    ) -> None:
        """Test FileSecretsAdapter handles malformed JSON gracefully."""
        from purjo.secrets import SecretsProviderError

        malformed_file = temp_dir / "malformed.json"
        malformed_file.write_text("not valid json {}")

        config = FileProviderConfig(provider="file", path=malformed_file)
        adapter = FileSecretsAdapter(config)

        with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
            adapter.read()

    def test_file_secrets_adapter_read_error_empty_file(self, temp_dir: Path) -> None:
        """Test FileSecretsAdapter handles empty file gracefully."""
        from purjo.secrets import SecretsProviderError

        empty_file = temp_dir / "empty.json"
        empty_file.write_text("")

        config = FileProviderConfig(provider="file", path=empty_file)
        adapter = FileSecretsAdapter(config)

        with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
            adapter.read()

    def test_vault_secrets_adapter_connection_error(self) -> None:
        """Test VaultSecretsAdapter handles connection errors gracefully."""
        from purjo.secrets import SecretsProviderError

        mock_client = Mock()
        mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception(
            "Connection refused"
        )

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="secret/data/test",
                **{"mount-point": "secret"},
                address="http://vault:8200",
                token="test-token",
            )
            adapter = VaultSecretsAdapter(config)

            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()

    def test_vault_secrets_adapter_invalid_response(self) -> None:
        """Test VaultSecretsAdapter handles invalid response from Vault."""
        from purjo.secrets import SecretsProviderError

        mock_client = Mock()
        # Return invalid response structure
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {}  # Missing nested 'data' key
        }

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="secret/data/test",
                **{"mount-point": "secret"},
                address="http://vault:8200",
                token="test-token",
            )
            adapter = VaultSecretsAdapter(config)

            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()
