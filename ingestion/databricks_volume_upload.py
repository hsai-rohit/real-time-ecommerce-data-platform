"""Upload local staging files into a Databricks Unity Catalog volume."""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


logger = logging.getLogger(__name__)

DEFAULT_STAGING_ROOT = Path("data/staging/adls")
DEFAULT_VOLUME_ROOT = "dbfs:/Volumes/workspace/default/ecommerce_raw"
DEFAULT_CLI = "databricks"
DEFAULT_PROFILE = "hsai-rohit"


class DatabricksVolumeUploadError(RuntimeError):
    """Base error for Databricks volume upload failures."""


class DatabricksConfigurationError(DatabricksVolumeUploadError):
    """Raised when Databricks CLI upload configuration is invalid."""


class DatabricksLocalStagingError(DatabricksVolumeUploadError):
    """Raised when the local staging root cannot be used."""


@dataclass(frozen=True)
class DatabricksVolumeUploadConfig:
    cli_executable: str = DEFAULT_CLI
    profile: str = DEFAULT_PROFILE
    volume_root: str = DEFAULT_VOLUME_ROOT

    @classmethod
    def from_env(cls) -> "DatabricksVolumeUploadConfig":
        config = cls(
            cli_executable=os.getenv("DATABRICKS_CLI", DEFAULT_CLI),
            profile=os.getenv("DATABRICKS_PROFILE", DEFAULT_PROFILE),
            volume_root=os.getenv(
                "DATABRICKS_VOLUME_ROOT",
                DEFAULT_VOLUME_ROOT,
            ),
        )

        if (
            not config.cli_executable
            or not config.profile
            or not config.volume_root
        ):
            raise DatabricksConfigurationError(
                "DATABRICKS_CLI, DATABRICKS_PROFILE, and "
                "DATABRICKS_VOLUME_ROOT must be non-empty"
            )

        if not config.volume_root.startswith("dbfs:/Volumes/"):
            raise DatabricksConfigurationError(
                "DATABRICKS_VOLUME_ROOT must be a dbfs:/Volumes/ path"
            )

        return config


class DatabricksVolumeUploader:
    """Upload every local file below a staging root into a volume."""

    def __init__(self, config: DatabricksVolumeUploadConfig) -> None:
        self._config = config

    def _run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                arguments,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as error:
            raise DatabricksVolumeUploadError(
                f"Databricks CLI executable not found: {arguments[0]}"
            ) from error
        except subprocess.CalledProcessError as error:
            details = (error.stderr or error.stdout or "").strip()
            raise DatabricksVolumeUploadError(
                f"Databricks CLI command failed ({arguments[1]}): {details}"
            ) from error

        logger.debug(
            "Databricks CLI output: %s",
            (result.stdout or "").strip(),
        )
        return result

    def _destination_for(self, root: Path, local_path: Path) -> str:
        root_resolved = root.resolve()
        local_resolved = local_path.resolve()

        try:
            relative = local_resolved.relative_to(root_resolved)
        except ValueError as error:
            raise DatabricksVolumeUploadError(
                f"Local path escapes staging root: {local_path}"
            ) from error

        relative_posix = PurePosixPath(relative.as_posix())

        if relative_posix.is_absolute() or ".." in relative_posix.parts:
            raise DatabricksVolumeUploadError(
                f"Local path escapes staging root: {local_path}"
            )

        return (
            f"{self._config.volume_root.rstrip('/')}/"
            f"{relative_posix.as_posix()}"
        )

    def _mkdirs(self, destination_directory: str) -> None:
        self._run(
            [
                self._config.cli_executable,
                "fs",
                "mkdirs",
                destination_directory,
                "--profile",
                self._config.profile,
            ]
        )

    def _upload(self, local_path: Path, destination: str) -> None:
        self._run(
            [
                self._config.cli_executable,
                "fs",
                "cp",
                str(local_path),
                destination,
                "--overwrite",
                "--profile",
                self._config.profile,
            ]
        )

    def upload_tree(
        self,
        staging_root: Path | str = DEFAULT_STAGING_ROOT,
    ) -> int:
        """Upload all regular files below *staging_root* and return the count."""

        root = Path(staging_root)

        if not root.exists():
            raise DatabricksLocalStagingError(
                f"Local staging root does not exist: {root}"
            )

        if not root.is_dir():
            raise DatabricksLocalStagingError(
                f"Local staging root is not a directory: {root}"
            )

        try:
            entries = sorted(root.rglob("*"))

            for path in entries:
                if path.is_symlink():
                    raise DatabricksVolumeUploadError(
                        f"Symlinks are not allowed in staging root: {path}"
                    )

            files = [path for path in entries if path.is_file()]

        except DatabricksVolumeUploadError:
            raise
        except OSError as error:
            raise DatabricksLocalStagingError(
                f"Unable to inspect local staging root: {root}"
            ) from error

        uploaded = 0

        for local_path in files:
            destination = self._destination_for(root, local_path)
            destination_directory = destination.rsplit("/", 1)[0]

            logger.info(
                "Creating Databricks destination directory %s",
                destination_directory,
            )
            self._mkdirs(destination_directory)

            logger.info(
                "Uploading %s to %s",
                local_path,
                destination,
            )
            self._upload(local_path, destination)

            uploaded += 1

        return uploaded
