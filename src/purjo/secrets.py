"""
Secrets module supporting file, Vault and SecretSpec adapters.
Assumes 'hvac' library for Vault integration and the optional 'secretspec'
library (``purjo[secretspec]``) for SecretSpec integration.
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

PROVIDER = Literal["file", "vault", "secretspec"]

SECRETSPEC_MANIFEST = "secretspec.toml"
SECRETSPEC_REASON = "purjo: inject secrets into Robot Framework tasks"


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


# SecretSpec adapter config type
class SecretSpecProviderConfig(BaseModel):
    provider: Literal["secretspec"]
    path: str = SECRETSPEC_MANIFEST
    profile: Optional[str] = None
    secretspec_provider: Optional[str] = Field(
        default=None, alias="secretspec-provider"
    )
    scope: Optional[str] = None
    reason: str = SECRETSPEC_REASON


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


class SecretSpecSecretsAdapter(SecretsAdapter):
    """SecretSpec-based secrets adapter (https://secretspec.dev/)."""

    def __init__(self, config: SecretSpecProviderConfig):
        self.config = config

    def read(self) -> Dict[str, Any]:
        """Resolve the secrets declared in a secretspec.toml manifest."""
        try:
            from secretspec import CallerContext
            from secretspec import SecretSpec
        except ImportError as e:
            raise SecretsConfigurationError(
                "The secretspec secrets provider requires the 'secretspec' "
                "package. Install it with: pip install 'purjo[secretspec]'"
            ) from e
        try:
            resolved = (
                SecretSpec.builder()
                .with_path(self.config.path)
                .with_provider(self.config.secretspec_provider)
                .with_profile(self.config.profile)
                .with_scope(self.config.scope)
                .with_reason(self.config.reason)
                .with_caller(CallerContext(name="purjo"))
                .load()
            )
        except Exception as e:
            raise SecretsProviderError(
                f"Failed to read secrets from SecretSpec manifest "
                f"{self.config.path}: {e}"
            ) from e
        # A secret declared `as_path` is materialized by secretspec into a
        # temporary file. Tasks receive secrets as variables, not files, so
        # pass on its contents and remove the file rather than leave a secret
        # on disk.
        with resolved:
            secrets: Dict[str, Any] = {}
            for name, secret in resolved.secrets.items():
                if secret.as_path and secret.path is not None:
                    secrets[name] = Path(secret.path).read_text()
                elif secret.value is not None:
                    secrets[name] = secret.value
            return secrets


class SecretsProvider(BaseModel):
    config: Union[FileProviderConfig, VaultProviderConfig, SecretSpecProviderConfig]

    def read(self) -> Dict[str, Any]:
        adapter: SecretsAdapter
        if isinstance(self.config, FileProviderConfig):
            adapter = FileSecretsAdapter(self.config)
        elif isinstance(self.config, VaultProviderConfig):
            adapter = VaultSecretsAdapter(self.config)
        elif isinstance(self.config, SecretSpecProviderConfig):
            adapter = SecretSpecSecretsAdapter(self.config)
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
    """Resolve a `file` or `secretspec` provider's relative path against the
    robot package.

    A package declares its secrets file (or secretspec.toml manifest) in its
    own `pyproject.toml`, next to itself, but `pur serve <package>` may be run
    from any directory. Without this the relative path would be resolved
    against the process working directory and `FileProviderConfig.path:
    FilePath` would reject it. A `secretspec` provider without a `path` looks
    for `secretspec.toml` next to the package.

    An absolute configured path is left untouched (`Path.__truediv__` already
    discards `base_path` for one).
    """
    path = config.get("path")
    if config.get("provider") == "secretspec" and "path" not in config:
        path = SECRETSPEC_MANIFEST
    if (
        base_path is None
        or config.get("provider") not in ("file", "secretspec")
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
