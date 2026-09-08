"""Run raw ingestion for the local synthetic website-events API."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.api_ingestion import APIIngestionError, ingest_api


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    url = "http://127.0.0.1:8000/events"
    destination = PROJECT_ROOT / "data" / "raw" / "api" / "events.json"

    try:
        ingest_api(url, destination)
    except APIIngestionError as error:
        logging.error("API ingestion failed: %s", error)
        return 1

    logging.info("API raw ingestion completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
