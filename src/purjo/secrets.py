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
    def read(self) -> Dict[str, Any]:  # pragma: no cover
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

    def read(self) -> Dict[str, Any]:
        """Read secrets from HashiCorp Vault."""
        try:
            client = hvac.Client(url=self.config.address, token=self.config.token)
            secret = client.secrets.kv.v2.read_secret_version(
                path=self.config.path, mount_point=self.config.mount_point
            )
            return dict(secret["data"]["data"])
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
        else:  # pragma: no cover
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


def resolve_profile(
    config: Dict[str, Any],
    profile: Optional[str],
) -> SecretsProvider:
    """Resolve the profile to use from the config."""
    # If only one config entry, return it
    if len(config) == 1:
        for name in config:
            return SecretsProvider(**dict(config=config[name]))

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
    return SecretsProvider(**dict(config=config[profile]))


def get_secrets_provider(
    config: Optional[Dict[str, Any]] = None,
    profile: Optional[str] = None,
) -> Optional[SecretsProvider]:
    """Get secrets provider based on the config and profile."""
    # If profile is a file path, use it directly
    if profile and Path(profile).is_file():
        return create_file_provider(Path(profile))

    # If no config, return None
    if config is None or len(config) == 0:
        return None

    # Resolve and return the profile
    return resolve_profile(config, profile)
