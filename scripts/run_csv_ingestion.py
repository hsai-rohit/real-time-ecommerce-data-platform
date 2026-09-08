"""Run raw CSV ingestion for the local customer and product sources."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.csv_ingestion import CsvIngestionError, ingest_csv


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    source_directory = PROJECT_ROOT / "data" / "source" / "csv"
    destination_directory = PROJECT_ROOT / "data" / "raw" / "csv"

    try:
        for filename in ("customers.csv", "products.csv"):
            ingest_csv(source_directory / filename, destination_directory / filename)
    except CsvIngestionError as error:
        logging.error("CSV ingestion failed: %s", error)
        return 1

    logging.info("CSV raw ingestion completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
