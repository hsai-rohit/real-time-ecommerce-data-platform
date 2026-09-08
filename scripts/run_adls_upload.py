"""Upload validated raw files to ADLS Gen2."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.adls_upload import (
    AdlsUploadConfig,
    AdlsUploadError,
    AdlsUploader,
    create_service_client,
)


UPLOADS = (
    ("data/raw/csv/customers.csv", "raw/csv/customers/customers.csv"),
    ("data/raw/csv/products.csv", "raw/csv/products/products.csv"),
    ("data/raw/sqlite/orders.csv", "raw/sqlite/orders/orders.csv"),
    ("data/raw/sqlite/payments.csv", "raw/sqlite/payments/payments.csv"),
    ("data/raw/api/events.json", "raw/api/events/events.json"),
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    missing = [PROJECT_ROOT / source for source, _ in UPLOADS if not (PROJECT_ROOT / source).is_file()]
    if missing:
        for path in missing:
            logging.error("Missing local upload input: %s", path)
        return 1

    try:
        config = AdlsUploadConfig.from_env()
        uploader = AdlsUploader(create_service_client(config), config)
        for source, destination in UPLOADS:
            uploader.upload_file(PROJECT_ROOT / source, destination)
    except AdlsUploadError as error:
        logging.error("ADLS upload failed: %s", error)
        return 1

    logging.info("ADLS upload completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
