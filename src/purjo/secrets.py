"""
Secrets module supporting file and Vault adapters.
Assumes 'hvac' library for Vault integration.
"""

from abc import ABC
from abc import abstractmethod
from pathlib import Path
from pydantic import BaseModel
from pydantic import Field
from pydantic import FilePath
from typing import Any
from typing import Dict
from typing import Literal
from typing import Optional
from typing import Union
import hvac
import hvac.exceptions
import json
import os

PROVIDER = Literal["file", "vault"]


# Custom exception classes
class SecretsConfigurationError(ValueError):
    """Raised when secrets configuration is invalid."""

    pass


class SecretsProviderError(RuntimeError):
    """Raised when secrets provider fails to read secrets."""

    pass


# Abstract base class for secrets adapters
class SecretsAdapter(ABC):
    """Abstract base class for secrets adapters."""

    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """Read secrets from the provider."""
        pass


# File adapter config type
class FileProviderConfig(BaseModel):
    provider: Literal["file"]
    path: FilePath


# Vault adapter config type
class VaultProviderConfig(BaseModel):
    provider: Literal["vault"]
    path: str
    mount_point: str = Field(alias="mount-point")
    address: Optional[str] = Field(default_factory=lambda: os.getenv("VAULT_ADDR"))
    token: Optional[str] = Field(default_factory=lambda: os.getenv("VAULT_TOKEN"))
    subtree: Optional[bool] = Field(
        default=None,
        description="Whether to fetch secrets as a subtree hierarchy. If None, auto-detected.",
    )


def _merge_dicts(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries, with d2 values taking precedence."""
    merged = dict(d1)
    for k, v in d2.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _merge_dicts(merged[k], v)
        else:
            merged[k] = v
    return merged


# Adapter implementations
class FileSecretsAdapter(SecretsAdapter):
    """File-based secrets adapter."""

    def __init__(self, config: FileProviderConfig):
        self.config = config

    def read(self) -> Dict[str, Any]:
        """Read secrets from a JSON file."""
        try:
            return dict(json.loads(self.config.path.read_text()))
        except Exception as e:
            raise SecretsProviderError(
                f"Failed to read secrets from file {self.config.path}: {e}"
            ) from e


class VaultSecretsAdapter(SecretsAdapter):
    """Vault-based secrets adapter."""

    def __init__(self, config: VaultProviderConfig):
        self.config = config
        if not self.config.address:
            raise SecretsConfigurationError(
                "VAULT_ADDR is required for Vault secrets. "
                "Set it in the environment or configuration."
            )
        if not self.config.token:
            raise SecretsConfigurationError(
                "VAULT_TOKEN is required for Vault secrets. "
                "Set it in the environment or configuration."
            )

    def _read_single_record(self, client: hvac.Client, path: str) -> Dict[str, Any]:
        """Read a single KV v2 secret record and validate response structure."""
        secret = client.secrets.kv.v2.read_secret_version(
            path=path, mount_point=self.config.mount_point
        )
        if (
            not isinstance(secret, dict)
            or not isinstance(secret.get("data"), dict)
            or not isinstance(secret["data"].get("data"), dict)
        ):
            raise ValueError(f"Invalid secret response structure from Vault at {path}")
        return dict(secret["data"]["data"])

    def _fetch_subtree(self, client: hvac.Client, path: str) -> Dict[str, Any]:
        """Recursively fetch secrets from a Vault KV v2 subtree."""
        clean_path = path.strip("/")
        response = client.secrets.kv.v2.list_secrets(
            path=clean_path, mount_point=self.config.mount_point
        )
        if (
            not isinstance(response, dict)
            or not isinstance(response.get("data"), dict)
            or "keys" not in response["data"]
            or not isinstance(response["data"]["keys"], list)
        ):
            raise ValueError(
                f"Invalid list_secrets response structure from Vault at {path}"
            )

        keys = response["data"]["keys"]
        if not keys:
            return {}

        result: Dict[str, Any] = {}
        for key in keys:
            if key.endswith("/"):
                subfolder = key.rstrip("/")
                child_path = f"{clean_path}/{subfolder}" if clean_path else subfolder
                child_data = self._fetch_subtree(client, child_path)
                target_key = subfolder
            else:
                child_path = f"{clean_path}/{key}" if clean_path else key
                child_data = self._read_single_record(client, child_path)
                target_key = key

            if (
                target_key in result
                and isinstance(result[target_key], dict)
                and isinstance(child_data, dict)
            ):
                result[target_key] = _merge_dicts(result[target_key], child_data)
            else:
                result[target_key] = child_data

        return result

    def read(self) -> Dict[str, Any]:
        """Read secrets from HashiCorp Vault."""
        try:
            client = hvac.Client(url=self.config.address, token=self.config.token)
            raw_path = self.config.path
            clean_path = raw_path.strip("/")

            if self.config.subtree is True or (
                self.config.subtree is None and raw_path.endswith("/")
            ):
                return self._fetch_subtree(client, clean_path)

            if self.config.subtree is False:
                return self._read_single_record(client, clean_path)

            try:
                return self._read_single_record(client, clean_path)
            except hvac.exceptions.InvalidPath:
                return self._fetch_subtree(client, clean_path)
        except Exception as e:
            raise SecretsProviderError(
                f"Failed to read secrets from Vault at {self.config.path}: {e}"
            ) from e


class SecretsProvider(BaseModel):
    config: Union[FileProviderConfig, VaultProviderConfig]

    def read(self) -> Dict[str, Any]:
        adapter: SecretsAdapter
        if isinstance(self.config, FileProviderConfig):
            adapter = FileSecretsAdapter(self.config)
        elif isinstance(self.config, VaultProviderConfig):
            adapter = VaultSecretsAdapter(self.config)
        else:
            raise SecretsConfigurationError(
                f"Unknown secrets configuration type: {type(self.config)}"
            )
        return adapter.read()


def create_file_provider(file_path: Path) -> SecretsProvider:
    """Create a file-based secrets provider."""
    return SecretsProvider(
        config=FileProviderConfig(
            provider="file",
            path=file_path,
        )
    )


def rebase_provider_config(
    config: Dict[str, Any],
    base_path: Optional[Path],
) -> Dict[str, Any]:
    """Resolve a `file` provider's relative path against the robot package.

    A package declares its secrets file in its own `pyproject.toml`, next to
    itself, but `pur serve <package>` may be run from any directory. Without
    this the relative path would be resolved against the process working
    directory and `FileProviderConfig.path: FilePath` would reject it.

    An absolute configured path is left untouched (`Path.__truediv__` already
    discards `base_path` for one).
    """
    path = config.get("path")
    if (
        base_path is None
        or config.get("provider") != "file"
        or not isinstance(path, str)
    ):
        return config
    return {**config, "path": str(base_path / path)}


def resolve_profile(
    config: Dict[str, Any],
    profile: Optional[str],
    base_path: Optional[Path] = None,
) -> SecretsProvider:
    """Resolve the profile to use from the config."""
    # If only one config entry, return it
    if len(config) == 1:
        for name in config:
            return SecretsProvider.model_validate(
                {"config": rebase_provider_config(config[name], base_path)}
            )

    # Use default profile if no profile specified
    if not profile:
        profile = "default"

    # Ensure the specified profile exists
    if profile not in config:
        raise SecretsConfigurationError(
            f"Profile '{profile}' not found in secrets config. "
            f"Available profiles: {', '.join(config.keys())}"
        )

    # Return the specified profile
    return SecretsProvider.model_validate(
        {"config": rebase_provider_config(config[profile], base_path)}
    )


def get_secrets_provider(
    config: Optional[Dict[str, Any]] = None,
    profile: Optional[str] = None,
    base_path: Optional[Path] = None,
) -> Optional[SecretsProvider]:
    """Get secrets provider based on the config and profile.

    Args:
        config: The `[tool.purjo.secrets]` table from the package's
            pyproject.toml, if any.
        profile: A profile name, or a path to a secrets file to use directly.
        base_path: The robot package directory, used to resolve a relative
            `file` provider path declared in `config`.
    """
    # If profile is a file path, use it directly
    if profile and Path(profile).is_file():
        return create_file_provider(Path(profile))

    # If no config, return None
    if config is None or len(config) == 0:
        return None

    # Resolve and return the profile
    return resolve_profile(config, profile, base_path)
