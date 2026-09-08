"""Run the local raw-ingestion stages in dependency order."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.api_ingestion import APIIngestionError, ingest_api
from ingestion.csv_ingestion import CsvIngestionError, ingest_csv
from ingestion.sqlite_ingestion import SQLiteIngestionError, ingest_table


logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    csv_source = PROJECT_ROOT / "data" / "source" / "csv"
    sqlite_source = PROJECT_ROOT / "data" / "source" / "sqlite" / "ecommerce.db"
    raw_root = PROJECT_ROOT / "data" / "raw"

    try:
        logger.info("START CSV INGESTION")
        for filename in ("customers.csv", "products.csv"):
            ingest_csv(csv_source / filename, raw_root / "csv" / filename)
        logger.info("COMPLETE CSV INGESTION")

        logger.info("START SQLITE INGESTION")
        for table in ("orders", "payments"):
            ingest_table(sqlite_source, table, raw_root / "sqlite" / f"{table}.csv")
        logger.info("COMPLETE SQLITE INGESTION")

        logger.info("START API INGESTION")
        ingest_api(
            "http://127.0.0.1:8000/events",
            raw_root / "api" / "events.json",
        )
        logger.info("COMPLETE API INGESTION")
    except (CsvIngestionError, SQLiteIngestionError, APIIngestionError) as error:
        logger.error("INGESTION FAILED: %s", error)
        return 1

    logger.info("COMPLETE INGESTION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
