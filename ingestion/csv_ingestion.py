"""Raw, idempotent ingestion of CSV source files into the landing layer."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path


logger = logging.getLogger(__name__)


class CsvIngestionError(RuntimeError):
    """Raised when a CSV source cannot be copied into the raw landing layer."""


def ingest_csv(source: Path | str, destination: Path | str) -> Path:
    """Copy one CSV source to a raw destination without altering its content.

    The destination is atomically replaced, so reruns recreate the same landing
    file instead of appending records.
    """
    source_path = Path(source)
    destination_path = Path(destination)

    if not source_path.is_file():
        message = f"CSV source does not exist or is not a file: {source_path}"
        logger.error(message)
        raise CsvIngestionError(message)

    try:
        if source_path.resolve() == destination_path.resolve():
            message = "Source and destination must be different files"
            logger.error(message)
            raise CsvIngestionError(message)

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Ingesting CSV source %s to %s", source_path, destination_path)

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination_path.parent, delete=False
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                with source_path.open("rb") as source_file:
                    shutil.copyfileobj(source_file, temporary_file)
            os.replace(temporary_path, destination_path)
        except OSError as error:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            message = (
                f"Failed to ingest CSV source {source_path} to {destination_path}: {error}"
            )
            logger.exception(message)
            raise CsvIngestionError(message) from error
    except OSError as error:
        message = f"Failed to prepare raw CSV destination {destination_path}: {error}"
        logger.exception(message)
        raise CsvIngestionError(message) from error

    logger.info("CSV ingestion succeeded: %s", destination_path)
    return destination_path
