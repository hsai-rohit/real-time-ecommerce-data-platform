"""Run raw SQLite ingestion for the local orders and payments tables."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.sqlite_ingestion import SQLiteIngestionError, ingest_table


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    database = PROJECT_ROOT / "data" / "source" / "sqlite" / "ecommerce.db"
    destination_directory = PROJECT_ROOT / "data" / "raw" / "sqlite"

    try:
        for table in ("orders", "payments"):
            ingest_table(database, table, destination_directory / f"{table}.csv")
    except SQLiteIngestionError as error:
        logging.error("SQLite ingestion failed: %s", error)
        return 1

    logging.info("SQLite raw ingestion completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
