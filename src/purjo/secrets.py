"""
Secrets module supporting file and Vault adapters.
Assumes 'hvac' library for Vault integration.
"""

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


class SecretsProvider(BaseModel):
    config: Union[FileProviderConfig, VaultProviderConfig]

    def read(self) -> Dict[str, Any]:
        if isinstance(self.config, FileProviderConfig):
            return file_secrets_provider(self.config)
        elif isinstance(self.config, VaultProviderConfig):
            return vault_secrets_provider(self.config)
        else:
            raise ValueError(f"Unknown secrets configuration: {self.config}")


def file_secrets_provider(config: FileProviderConfig) -> Dict[str, Any]:
    return dict(json.loads(config.path.read_text()))


def vault_secrets_provider(
    config: VaultProviderConfig,
) -> Dict[str, Any]:  # noqa: F821
    assert config.address, "VAULT_ADDR is required for Vault secrets"
    assert config.token, "VAULT_TOKEN is required for Vault secrets"
    client = hvac.Client(url=config.address, token=config.token)
    secret = client.secrets.kv.v2.read_secret_version(
        path=config.path, mount_point=config.mount_point
    )
    return dict(secret["data"]["data"])


def get_secrets_provider(
    config: Optional[Dict[str, Any]] = None,
    profile: Optional[str] = None,
) -> Optional[SecretsProvider]:
    """Get secrets provider based on the config and profile."""

    # If profile is a file path, use it directly
    if profile and Path(profile).is_file():
        return SecretsProvider(
            config=FileProviderConfig(
                provider="file",
                path=Path(profile),
            )
        )

    # If no config, return None
    if config is None or len(config) == 0:
        return None

    # If only one config, return it
    if len(config) == 1:
        for name in config:
            return SecretsProvider(**dict(config=config[name]))

    # If default profile, use it
    if not profile and "default" in config:
        profile = "default"

    # Ensure the specified profile exists
    assert (
        profile in config
    ), f"Profile '{profile}' not found in secrets config: {config}"

    # Return the specified profile
    return SecretsProvider(**dict(config=config[profile]))
