"""Validate raw customer and product CSV files."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from validation.csv_validation import validate_customers, validate_products


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raw_csv = PROJECT_ROOT / "data" / "raw" / "csv"
    results = (
        ("customers.csv", validate_customers(raw_csv / "customers.csv")),
        ("products.csv", validate_products(raw_csv / "products.csv")),
    )
    failed = False
    for filename, result in results:
        if result.passed:
            logging.info("PASS %s", filename)
        else:
            failed = True
            logging.error("FAIL %s", filename)
            for error in result.errors:
                logging.error("  %s", error)

    if failed:
        logging.error("CSV validation failed")
        return 1
    logging.info("CSV validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
