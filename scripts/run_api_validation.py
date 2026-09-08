"""Validate the raw website-events API response."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from validation.api_validation import validate_events


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = validate_events(
        PROJECT_ROOT / "data" / "raw" / "api" / "events.json",
        PROJECT_ROOT / "data" / "raw" / "csv" / "customers.csv",
    )
    if result.passed:
        logging.info("PASS events.json")
        logging.info("REST API raw-data validation passed")
        return 0
    logging.error("FAIL events.json")
    for error in result.errors:
        logging.error("  %s", error)
    logging.error("REST API raw-data validation failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
