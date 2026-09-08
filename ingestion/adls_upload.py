"""Upload validated local files to Azure Data Lake Storage Gen2."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.identity import InteractiveBrowserCredential
from azure.storage.filedatalake import DataLakeServiceClient


logger = logging.getLogger(__name__)

DEFAULT_ACCOUNT_NAME = "hsrecommercedata01"
DEFAULT_FILESYSTEM = "ecommerce"
DEFAULT_TENANT_ID = "e9203e7b-4203-4872-9aac-93d655003a11"


class AdlsUploadError(RuntimeError):
    """Base error for ADLS upload failures."""


class AdlsConfigurationError(AdlsUploadError):
    """Raised when ADLS configuration is missing or invalid."""


class AdlsLocalFileError(AdlsUploadError):
    """Raised when a local upload input cannot be read."""


@dataclass(frozen=True)
class AdlsUploadConfig:
    account_name: str = DEFAULT_ACCOUNT_NAME
    filesystem: str = DEFAULT_FILESYSTEM
    tenant_id: str = DEFAULT_TENANT_ID

    @property
    def account_url(self) -> str:
        return f"https://{self.account_name}.dfs.core.windows.net"

    @classmethod
    def from_env(cls) -> "AdlsUploadConfig":
        config = cls(
            account_name=os.getenv("ADLS_ACCOUNT_NAME", DEFAULT_ACCOUNT_NAME),
            filesystem=os.getenv("ADLS_FILESYSTEM", DEFAULT_FILESYSTEM),
            tenant_id=os.getenv("AZURE_TENANT_ID", DEFAULT_TENANT_ID),
        )
        if not config.account_name or not config.filesystem or not config.tenant_id:
            raise AdlsConfigurationError(
                "ADLS_ACCOUNT_NAME, ADLS_FILESYSTEM, and AZURE_TENANT_ID must be non-empty"
            )
        return config


def create_service_client(config: AdlsUploadConfig) -> DataLakeServiceClient:
    """Create an authenticated Data Lake client using interactive browser login."""
    try:
        credential = InteractiveBrowserCredential(tenant_id=config.tenant_id)
        return DataLakeServiceClient(
            account_url=config.account_url,
            credential=credential,
        )
    except Exception as error:
        raise AdlsConfigurationError("Unable to create the ADLS client") from error


class AdlsUploader:
    """Upload local files to one ADLS Gen2 filesystem."""

    def __init__(self, service_client: DataLakeServiceClient, config: AdlsUploadConfig) -> None:
        self._filesystem = service_client.get_file_system_client(config.filesystem)
        self._config = config

    def _ensure_parent_directories(self, destination: str) -> None:
        parent_parts = destination.strip("/").split("/")[:-1]
        current_parts: list[str] = []
        for part in parent_parts:
            current_parts.append(part)
            directory_path = "/".join(current_parts)
            try:
                self._filesystem.get_directory_client(directory_path).create_directory()
            except ResourceExistsError:
                continue

    def upload_file(self, local_path: Path | str, destination: str) -> None:
        """Upload bytes from a local file, replacing any existing destination."""
        source_path = Path(local_path)
        if not source_path.is_file():
            raise AdlsLocalFileError(f"Local upload input does not exist: {source_path}")
        try:
            content = source_path.read_bytes()
        except OSError as error:
            raise AdlsLocalFileError(f"Unable to read local upload input: {source_path}") from error

        try:
            self._ensure_parent_directories(destination)
            self._filesystem.get_file_client(destination).upload_data(content, overwrite=True)
        except Exception as error:
            if isinstance(error, AdlsUploadError):
                raise
            raise AdlsUploadError(
                f"Failed to upload {source_path} to ADLS destination {destination}"
            ) from error
        logger.info("Uploaded %s to %s (%d bytes)", source_path, destination, len(content))
