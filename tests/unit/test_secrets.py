"""Unit tests for secrets.py module.

Related User Stories:
- US-004: Configure secrets

Related ADRs:
- ADR-003: Architecture overview
"""

from pathlib import Path
from purjo.secrets import _merge_dicts
from purjo.secrets import FileProviderConfig
from purjo.secrets import FileSecretsAdapter
from purjo.secrets import get_secrets_provider
from purjo.secrets import rebase_provider_config
from purjo.secrets import SecretsConfigurationError
from purjo.secrets import SecretsProvider
from purjo.secrets import SecretsProviderError
from purjo.secrets import VaultProviderConfig
from purjo.secrets import VaultSecretsAdapter
from typing import Any
from unittest.mock import Mock
from unittest.mock import patch
import hvac.exceptions
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
                **dict[str, Any]({"mount-point": "secret"}),
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
            **dict[str, Any]({"mount-point": "secret"}),
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
            **dict[str, Any]({"mount-point": "secret"}),
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
                **dict[str, Any]({"mount-point": "custom_mount"}),
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


class TestRelativeSecretsPaths:
    """Tests for resolving a relative `file` provider path.

    A package declares `path = "secrets.json"` next to its own
    pyproject.toml, but `pur serve <package>` may run from anywhere, so the
    path must be resolved against the package rather than the process
    working directory.

    Related: US-004
    """

    def test_relative_path_is_resolved_against_base_path(
        self, sample_secrets_file: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that a bare filename resolves next to the package."""
        monkeypatch.chdir(tmp_path)
        config = {
            "default": {"provider": "file", "path": sample_secrets_file.name},
        }

        provider = get_secrets_provider(
            config=config, base_path=sample_secrets_file.parent
        )

        assert provider is not None
        assert provider.read()["username"] == "testuser"

    def test_relative_path_is_resolved_for_a_named_profile(
        self, sample_secrets_file: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that the rebase also applies when picking a named profile."""
        monkeypatch.chdir(tmp_path)
        config = {
            "default": {"provider": "file", "path": sample_secrets_file.name},
            "production": {"provider": "file", "path": sample_secrets_file.name},
        }

        provider = get_secrets_provider(
            config=config,
            profile="production",
            base_path=sample_secrets_file.parent,
        )

        assert provider is not None
        assert provider.read()["username"] == "testuser"

    def test_absolute_path_is_left_alone(self, sample_secrets_file: Path) -> None:
        """Test that an absolute configured path ignores the base path."""
        config = {"provider": "file", "path": str(sample_secrets_file)}

        assert rebase_provider_config(config, Path("/nonexistent")) == config

    def test_config_without_base_path_is_unchanged(self) -> None:
        """Test that no base path means no rebasing."""
        config = {"provider": "file", "path": "secrets.json"}

        assert rebase_provider_config(config, None) == config

    def test_non_file_provider_is_unchanged(self) -> None:
        """Test that a Vault path is not a filesystem path and is untouched."""
        config = {"provider": "vault", "path": "myapp/credentials"}

        assert rebase_provider_config(config, Path("/somewhere")) == config

    def test_config_without_a_string_path_is_unchanged(self) -> None:
        """Test that a malformed entry is passed through for pydantic to reject."""
        config: dict[str, object] = {"provider": "file"}

        assert rebase_provider_config(config, Path("/somewhere")) == config


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
                **dict[str, Any]({"mount-point": "secret"}),
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
        file_secrets = file_provider.read()  # type: ignore[union-attr]

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
            vault_secrets = vault_provider.read()  # type: ignore[union-attr]

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
        dev_result = dev_provider.read()  # type: ignore[union-attr]
        assert dev_result["env"] == "dev"

        # Get prod secrets
        prod_provider = get_secrets_provider(config=config, profile="prod")
        prod_result = prod_provider.read()  # type: ignore[union-attr]
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
                **dict[str, Any]({"mount-point": "secret"}),
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
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
            )
            adapter = VaultSecretsAdapter(config)

            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()


class TestSecretsProviderUnknownConfig:
    """Tests for the defensive branch guarding unknown provider configs.

    Related: US-004
    """

    def test_read_raises_on_unknown_config_type(self) -> None:
        """Test that an unrecognised config type is rejected explicitly."""
        provider = SecretsProvider.model_construct(config="not-a-provider-config")

        with pytest.raises(SecretsConfigurationError, match="Unknown secrets"):
            provider.read()


class TestVaultSubtreeSecretsProvider:
    """Tests for Vault subtree secrets retrieval and auto-detection."""

    def test_backwards_compatibility_single_record(self) -> None:
        """Test single record retrieval when subtree is omitted / None."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"api_key": "secret123", "env": "prod"}}
        }

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="myapp/config",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
            )
            assert config.subtree is None
            adapter = VaultSecretsAdapter(config)
            result = adapter.read()

            assert result == {"api_key": "secret123", "env": "prod"}
            mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
                path="myapp/config", mount_point="secret"
            )
            mock_client.secrets.kv.v2.list_secrets.assert_not_called()

    def test_autodetect_fallback_to_subtree_when_root_is_directory(self) -> None:
        """Test fallback to subtree when path is a directory (raises InvalidPath on read)."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.read_secret_version.side_effect = [
            hvac.exceptions.InvalidPath("Not a secret"),
            {"data": {"data": {"password": "pass123"}}},
        ]
        mock_client.secrets.kv.v2.list_secrets.return_value = {"data": {"keys": ["db"]}}

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="myapp",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=None,
            )
            adapter = VaultSecretsAdapter(config)
            result = adapter.read()

            assert result == {"db": {"password": "pass123"}}
            mock_client.secrets.kv.v2.read_secret_version.assert_any_call(
                path="myapp", mount_point="secret"
            )
            mock_client.secrets.kv.v2.list_secrets.assert_called_once_with(
                path="myapp", mount_point="secret"
            )
            mock_client.secrets.kv.v2.read_secret_version.assert_any_call(
                path="myapp/db", mount_point="secret"
            )

    def test_explicit_subtree_true_directly_calls_list_secrets(self) -> None:
        """Test explicit subtree=True directly calls list_secrets without reading root."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.list_secrets.return_value = {"data": {"keys": ["db"]}}
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"password": "pass123"}}
        }

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="myapp",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=True,
            )
            adapter = VaultSecretsAdapter(config)
            result = adapter.read()

            assert result == {"db": {"password": "pass123"}}
            mock_client.secrets.kv.v2.list_secrets.assert_called_once_with(
                path="myapp", mount_point="secret"
            )
            mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
                path="myapp/db", mount_point="secret"
            )

    def test_explicit_subtree_false_disallows_fallback(self) -> None:
        """Test explicit subtree=False disallows fallback and raises SecretsProviderError."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.read_secret_version.side_effect = (
            hvac.exceptions.InvalidPath("Not a secret")
        )

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="myapp",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=False,
            )
            adapter = VaultSecretsAdapter(config)

            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()

            mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
                path="myapp", mount_point="secret"
            )
            mock_client.secrets.kv.v2.list_secrets.assert_not_called()

    def test_trailing_slash_path_triggers_subtree_directly(self) -> None:
        """Test trailing slash in path triggers subtree traversal directly."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.list_secrets.return_value = {"data": {"keys": ["db"]}}
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"password": "pass123"}}
        }

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="myapp/",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=None,
            )
            adapter = VaultSecretsAdapter(config)
            result = adapter.read()

            assert result == {"db": {"password": "pass123"}}
            mock_client.secrets.kv.v2.list_secrets.assert_called_once_with(
                path="myapp", mount_point="secret"
            )
            mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
                path="myapp/db", mount_point="secret"
            )

    def test_multilevel_nested_subtree(self) -> None:
        """Test multi-level nested subtree with files and subfolders."""
        mock_client = Mock()

        def mock_list_secrets(path: str, mount_point: str) -> dict[str, Any]:
            if path == "app":
                return {"data": {"keys": ["config", "projects/"]}}
            elif path == "app/projects":
                return {"data": {"keys": ["alpha", "beta"]}}
            raise hvac.exceptions.InvalidPath(f"Path not found: {path}")

        def mock_read_secret(path: str, mount_point: str) -> dict[str, Any]:
            if path == "app/config":
                return {"data": {"data": {"env": "prod", "version": "1.0"}}}
            elif path == "app/projects/alpha":
                return {"data": {"data": {"name": "alpha_project"}}}
            elif path == "app/projects/beta":
                return {"data": {"data": {"name": "beta_project"}}}
            raise hvac.exceptions.InvalidPath(f"Secret not found: {path}")

        mock_client.secrets.kv.v2.list_secrets.side_effect = mock_list_secrets
        mock_client.secrets.kv.v2.read_secret_version.side_effect = mock_read_secret

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="app",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=True,
            )
            adapter = VaultSecretsAdapter(config)
            result = adapter.read()

            assert result == {
                "config": {"env": "prod", "version": "1.0"},
                "projects": {
                    "alpha": {"name": "alpha_project"},
                    "beta": {"name": "beta_project"},
                },
            }

    def test_empty_subtree_returns_empty_dict(self) -> None:
        """Test empty subtree returns an empty dictionary."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.list_secrets.return_value = {"data": {"keys": []}}

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="empty_folder",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=True,
            )
            adapter = VaultSecretsAdapter(config)
            result = adapter.read()

            assert result == {}

    def test_nonexistent_path_raises_secrets_provider_error(self) -> None:
        """Test non-existent path raises SecretsProviderError."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.read_secret_version.side_effect = (
            hvac.exceptions.InvalidPath("No such secret")
        )
        mock_client.secrets.kv.v2.list_secrets.side_effect = (
            hvac.exceptions.InvalidPath("No such path")
        )

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="nonexistent",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=None,
            )
            adapter = VaultSecretsAdapter(config)

            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config_subtree = VaultProviderConfig(
                provider="vault",
                path="nonexistent",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=True,
            )
            adapter_subtree = VaultSecretsAdapter(config_subtree)

            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter_subtree.read()

    def test_permission_error_on_list_secrets(self) -> None:
        """Test Forbidden error on list_secrets raises SecretsProviderError."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.list_secrets.side_effect = hvac.exceptions.Forbidden(
            "Access denied"
        )

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="forbidden_dir",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=True,
            )
            adapter = VaultSecretsAdapter(config)

            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()

    def test_permission_error_on_child_read(self) -> None:
        """Test Forbidden error on reading child secret raises SecretsProviderError."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.list_secrets.return_value = {
            "data": {"keys": ["restricted"]}
        }
        mock_client.secrets.kv.v2.read_secret_version.side_effect = (
            hvac.exceptions.Forbidden("Access denied to child")
        )

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="myapp",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=True,
            )
            adapter = VaultSecretsAdapter(config)

            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()

    def test_malformed_responses_raise_secrets_provider_error(self) -> None:
        """Test malformed responses from Vault raise SecretsProviderError."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.list_secrets.return_value = {"data": {}}

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="myapp",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=True,
            )
            adapter = VaultSecretsAdapter(config)
            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()

        mock_client.secrets.kv.v2.list_secrets.return_value = {
            "data": {"keys": "invalid"}
        }
        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            adapter = VaultSecretsAdapter(config)
            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()

        mock_client.secrets.kv.v2.list_secrets.return_value = {"data": None}
        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            adapter = VaultSecretsAdapter(config)
            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()

        mock_client.secrets.kv.v2.list_secrets.return_value = {
            "data": {"keys": ["child"]}
        }
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": "not a dict"}
        }
        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            adapter = VaultSecretsAdapter(config)
            with pytest.raises(SecretsProviderError, match="Failed to read secrets"):
                adapter.read()

    def test_name_collision_merges_dictionaries(self) -> None:
        """Test name collision between record and folder merges dictionaries."""
        mock_client = Mock()

        def mock_list_1(path: str, mount_point: str) -> dict[str, Any]:
            if path == "app":
                return {"data": {"keys": ["service", "service/"]}}
            elif path == "app/service":
                return {"data": {"keys": ["db"]}}
            raise hvac.exceptions.InvalidPath(path)

        def mock_read_1(path: str, mount_point: str) -> dict[str, Any]:
            if path == "app/service":
                return {"data": {"data": {"port": 8080, "host": "localhost"}}}
            elif path == "app/service/db":
                return {"data": {"data": {"user": "admin"}}}
            raise hvac.exceptions.InvalidPath(path)

        mock_client.secrets.kv.v2.list_secrets.side_effect = mock_list_1
        mock_client.secrets.kv.v2.read_secret_version.side_effect = mock_read_1

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="app",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=True,
            )
            adapter = VaultSecretsAdapter(config)
            result = adapter.read()

            assert result == {
                "service": {
                    "port": 8080,
                    "host": "localhost",
                    "db": {"user": "admin"},
                }
            }

        def mock_list_2(path: str, mount_point: str) -> dict[str, Any]:
            if path == "app":
                return {"data": {"keys": ["service/", "service"]}}
            elif path == "app/service":
                return {"data": {"keys": ["db"]}}
            raise hvac.exceptions.InvalidPath(path)

        mock_client.secrets.kv.v2.list_secrets.side_effect = mock_list_2

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            adapter = VaultSecretsAdapter(config)
            result2 = adapter.read()

            assert result2 == {
                "service": {
                    "db": {"user": "admin"},
                    "port": 8080,
                    "host": "localhost",
                }
            }

    def test_root_path_subtree(self) -> None:
        """Test subtree traversal starting at the root mount path."""
        mock_client = Mock()

        def mock_list(path: str, mount_point: str) -> dict[str, Any]:
            if path == "":
                return {"data": {"keys": ["app/"]}}
            elif path == "app":
                return {"data": {"keys": ["token"]}}
            raise hvac.exceptions.InvalidPath(path)

        mock_client.secrets.kv.v2.list_secrets.side_effect = mock_list
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"val": 123}}
        }

        with patch("purjo.secrets.hvac.Client", return_value=mock_client):
            config = VaultProviderConfig(
                provider="vault",
                path="/",
                **dict[str, Any]({"mount-point": "secret"}),
                address="http://vault:8200",
                token="test-token",
                subtree=True,
            )
            adapter = VaultSecretsAdapter(config)
            result = adapter.read()

            assert result == {"app": {"token": {"val": 123}}}

    def test_merge_dicts_helper(self) -> None:
        """Test _merge_dicts utility function directly."""
        d1 = {"a": 1, "nested": {"x": 10, "y": 20}}
        d2 = {"b": 2, "nested": {"y": 99, "z": 30}}
        merged = _merge_dicts(d1, d2)

        assert merged == {"a": 1, "b": 2, "nested": {"x": 10, "y": 99, "z": 30}}
