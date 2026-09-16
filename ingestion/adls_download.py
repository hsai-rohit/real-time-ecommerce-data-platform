"""Download an ADLS Gen2 prefix into a local staging directory."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from azure.identity import InteractiveBrowserCredential
from azure.storage.filedatalake import DataLakeServiceClient


logger = logging.getLogger(__name__)

DEFAULT_ACCOUNT_NAME = "hsrecommercedata01"
DEFAULT_FILESYSTEM = "ecommerce"
DEFAULT_TENANT_ID = "e9203e7b-4203-4872-9aac-93d655003a11"
DEFAULT_STAGING_ROOT = Path("data/staging/adls")


class AdlsDownloadError(RuntimeError):
    """Base error for ADLS download failures."""


class AdlsDownloadConfigurationError(AdlsDownloadError):
    """Raised when ADLS download configuration is invalid."""


class AdlsLocalStagingError(AdlsDownloadError):
    """Raised when the local staging destination cannot be used."""


@dataclass(frozen=True)
class AdlsDownloadConfig:
    account_name: str = DEFAULT_ACCOUNT_NAME
    filesystem: str = DEFAULT_FILESYSTEM
    tenant_id: str = DEFAULT_TENANT_ID

    @property
    def account_url(self) -> str:
        return f"https://{self.account_name}.dfs.core.windows.net"

    @classmethod
    def from_env(cls) -> "AdlsDownloadConfig":
        config = cls(
            account_name=os.getenv(
                "ADLS_ACCOUNT_NAME",
                DEFAULT_ACCOUNT_NAME,
            ),
            filesystem=os.getenv(
                "ADLS_FILESYSTEM",
                DEFAULT_FILESYSTEM,
            ),
            tenant_id=os.getenv(
                "AZURE_TENANT_ID",
                DEFAULT_TENANT_ID,
            ),
        )

        if not config.account_name or not config.filesystem or not config.tenant_id:
            raise AdlsDownloadConfigurationError(
                "ADLS_ACCOUNT_NAME, ADLS_FILESYSTEM, and "
                "AZURE_TENANT_ID must be non-empty"
            )

        return config


def create_download_service_client(
    config: AdlsDownloadConfig,
) -> DataLakeServiceClient:
    """Create a Data Lake client with explicit-tenant browser authentication."""
    try:
        credential = InteractiveBrowserCredential(
            tenant_id=config.tenant_id
        )
        return DataLakeServiceClient(
            account_url=config.account_url,
            credential=credential,
        )
    except Exception as error:
        raise AdlsDownloadConfigurationError(
            "Unable to create the ADLS download client"
        ) from error


def _path_name(path: object) -> str:
    if isinstance(path, dict):
        return str(path["name"])
    return str(path.name)


def _is_directory(path: object) -> bool:
    if isinstance(path, dict):
        value = path.get("is_directory", False)
    else:
        value = getattr(path, "is_directory", False)

    return bool(value)


class AdlsDownloader:
    """Download files below one ADLS prefix into a local staging root."""

    def __init__(
        self,
        service_client: DataLakeServiceClient,
        config: AdlsDownloadConfig,
    ) -> None:
        self._filesystem = service_client.get_file_system_client(
            config.filesystem
        )

    def download_prefix(
        self,
        prefix: str = "raw",
        staging_root: Path | str = DEFAULT_STAGING_ROOT,
    ) -> int:
        """Download all files below prefix, preserving relative paths."""
        root = Path(staging_root)

        if root.exists() and not root.is_dir():
            raise AdlsLocalStagingError(
                f"Local staging path is not a directory: {root}"
            )

        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise AdlsLocalStagingError(
                f"Unable to create local staging path: {root}"
            ) from error

        normalized_prefix = prefix.strip("/")

        if not normalized_prefix:
            raise AdlsDownloadConfigurationError(
                "ADLS download prefix must be non-empty"
            )

        downloaded = 0
        root_resolved = root.resolve()

        try:
            paths = self._filesystem.get_paths(
                path=normalized_prefix,
                recursive=True,
            )

            prefix_marker = normalized_prefix + "/"

            for path in paths:
                if _is_directory(path):
                    continue

                remote_name = _path_name(path)

                if not remote_name.startswith(prefix_marker):
                    continue

                relative_name = remote_name[len(prefix_marker):]
                relative_path = PurePosixPath(relative_name)

                if (
                    not relative_name
                    or relative_path.is_absolute()
                    or ".." in relative_path.parts
                ):
                    raise AdlsDownloadError(
                        f"ADLS path escapes requested prefix: {remote_name}"
                    )

                local_path = (
                    root / Path(*relative_path.parts)
                ).resolve()

                try:
                    local_path.relative_to(root_resolved)
                except ValueError as error:
                    raise AdlsDownloadError(
                        f"ADLS path escapes local staging root: {remote_name}"
                    ) from error

                local_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                content = (
                    self._filesystem
                    .get_file_client(remote_name)
                    .download_file()
                    .readall()
                )

                local_path.write_bytes(content)

                downloaded += 1

                logger.info(
                    "Downloaded %s to %s (%d bytes)",
                    remote_name,
                    local_path,
                    len(content),
                )

        except AdlsDownloadError:
            raise
        except OSError as error:
            raise AdlsLocalStagingError(
                "Unable to write the local ADLS staging files"
            ) from error
        except Exception as error:
            raise AdlsDownloadError(
                f"Failed to download ADLS prefix '{normalized_prefix}'"
            ) from error

        return downloaded
