"""Raw, idempotent extraction of SQLite tables into CSV landing files."""

from __future__ import annotations

import csv
import logging
import os
import sqlite3
import tempfile
from pathlib import Path


logger = logging.getLogger(__name__)


class SQLiteIngestionError(RuntimeError):
    """Raised when a SQLite table cannot be extracted into the raw layer."""


def _quoted_identifier(identifier: str) -> str:
    """Quote a caller-supplied SQLite identifier safely for a SQL statement."""
    if not identifier:
        raise SQLiteIngestionError("SQLite table name must not be empty")
    return '"' + identifier.replace('"', '""') + '"'


def ingest_table(
    database: Path | str, table: str, destination: Path | str
) -> int:
    """Extract every row from *table* into an atomically replaced CSV file.

    The database is opened with SQLite's read-only URI mode. Values are passed
    directly from the query cursor to ``csv.writer`` without application-level
    cleaning, validation, or transformation.
    """
    database_path = Path(database)
    destination_path = Path(destination)
    if not database_path.is_file():
        message = f"SQLite source does not exist or is not a file: {database_path}"
        logger.error(message)
        raise SQLiteIngestionError(message)

    temporary_path: Path | None = None
    try:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Extracting SQLite source %s table %s to %s",
            database_path,
            table,
            destination_path,
        )

        database_uri = database_path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(database_uri, uri=True) as connection:
            cursor = connection.execute(f"SELECT * FROM {_quoted_identifier(table)}")
            headers = [column[0] for column in cursor.description]
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=destination_path.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                writer = csv.writer(temporary_file)
                writer.writerow(headers)
                row_count = 0
                for row in cursor:
                    writer.writerow(row)
                    row_count += 1

        os.replace(temporary_path, destination_path)
    except (OSError, sqlite3.Error, SQLiteIngestionError) as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        message = (
            f"Failed to extract SQLite source {database_path} table {table} "
            f"to {destination_path}: {error}"
        )
        logger.exception(message)
        if isinstance(error, SQLiteIngestionError):
            raise
        raise SQLiteIngestionError(message) from error

    logger.info(
        "SQLite ingestion succeeded: source=%s table=%s destination=%s rows=%d",
        database_path,
        table,
        destination_path,
        row_count,
    )
    return row_count
