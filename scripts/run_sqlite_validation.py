"""Validate raw orders and payments CSV files and their relationships."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from validation.sqlite_validation import validate_orders, validate_payments


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raw = PROJECT_ROOT / "data" / "raw"
    orders = raw / "sqlite" / "orders.csv"
    payments = raw / "sqlite" / "payments.csv"
    customers = raw / "csv" / "customers.csv"
    products = raw / "csv" / "products.csv"

    results = (
        ("orders.csv", validate_orders(orders, customers, products)),
        ("payments.csv", validate_payments(payments, orders)),
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
        logging.error("SQLite raw-data validation failed")
        return 1
    logging.info("SQLite raw-data validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
