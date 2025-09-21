"""
Secrets module supporting file and Vault adapters.
Assumes 'hvac' library for Vault integration.
"""

from typing import Any
from typing import Dict
from typing import Optional
from typing import TypedDict
from typing import Union
import hvac
import json
import os


# File adapter config type
class FileAdapterConfig(TypedDict):
    type: str
    path: str


# Vault adapter config type
class VaultAdapterConfig(TypedDict, total=False):
    type: str
    address: str
    path: str
    token: str


# Secrets config type: string (file path), file adapter dict, or vault adapter dict
SecretsConfig = Union[
    str,
    FileAdapterConfig,
    VaultAdapterConfig,
]


def file_secrets_adapter(path: str) -> Dict[str, Any]:
    path = os.path.expandvars(path)
    with open(path, "r") as f:
        return dict(json.load(f))


def vault_secrets_adapter(
    address: str, path: str, token: Optional[str] = None
) -> Dict[str, Any]:
    token_str: str | None = str(token) if token is not None else None
    client = hvac.Client(
        url=os.path.expandvars(address),
        token=token_str or os.environ.get("VAULT_TOKEN"),
    )
    secret = client.secrets.kv.v2.read_secret_version(path=path)
    return dict(secret["data"]["data"])


def get_secrets(config: SecretsConfig) -> Dict[str, Any]:
    # If config is a string, treat as file path
    if isinstance(config, str):
        return file_secrets_adapter(config)
    # If config is a dict, use adapter logic
    adapter = config.get("type")
    if adapter == "file":
        path = config.get("path")
        if not isinstance(path, str):
            raise ValueError("File config must have a string 'path' key")
        return file_secrets_adapter(path)
    elif adapter == "vault":
        address = config.get("address")
        path = config.get("path")
        token = config.get("token")
        token_str: str | None = str(token) if token is not None else None
        if not isinstance(address, str) or not isinstance(path, str):
            raise ValueError(
                "Vault adapter config must have string 'address' and 'path' keys"
            )
        return vault_secrets_adapter(address=address, path=path, token=token_str)
    else:
        raise ValueError(f"Unknown secrets adapter: {adapter}")
