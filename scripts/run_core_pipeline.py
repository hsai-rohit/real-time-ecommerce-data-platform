"""Run the complete local, ADLS, and Databricks volume pipeline."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.adls_download import (
    AdlsDownloadConfig,
    AdlsDownloadError,
    AdlsDownloader,
    create_download_service_client,
)
from ingestion.adls_upload import (
    AdlsUploadConfig,
    AdlsUploadError,
    AdlsUploader,
    create_service_client,
)
from ingestion.api_ingestion import APIIngestionError, ingest_api
from ingestion.csv_ingestion import CsvIngestionError, ingest_csv
from ingestion.databricks_volume_upload import (
    DatabricksVolumeUploadError,
    DatabricksVolumeUploadConfig,
    DatabricksVolumeUploader,
)
from ingestion.sqlite_ingestion import SQLiteIngestionError, ingest_table
from validation.api_validation import validate_events
from validation.csv_validation import validate_customers, validate_products
from validation.sqlite_validation import validate_orders, validate_payments


logger = logging.getLogger(__name__)

UPLOADS = (
    ("data/raw/csv/customers.csv", "raw/csv/customers/customers.csv"),
    ("data/raw/csv/products.csv", "raw/csv/products/products.csv"),
    ("data/raw/sqlite/orders.csv", "raw/sqlite/orders/orders.csv"),
    ("data/raw/sqlite/payments.csv", "raw/sqlite/payments/payments.csv"),
    ("data/raw/api/events.json", "raw/api/events/events.json"),
)


def _require_validation(label: str, result: object) -> None:
    if getattr(result, "passed", False):
        return
    errors = getattr(result, "errors", [])
    for error in errors:
        logger.error("%s: %s", label, error)
    raise RuntimeError(f"{label} validation failed")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raw_root = PROJECT_ROOT / "data" / "raw"
    source_csv = PROJECT_ROOT / "data" / "source" / "csv"
    source_database = PROJECT_ROOT / "data" / "source" / "sqlite" / "ecommerce.db"
    customers = raw_root / "csv" / "customers.csv"
    products = raw_root / "csv" / "products.csv"
    orders = raw_root / "sqlite" / "orders.csv"
    payments = raw_root / "sqlite" / "payments.csv"
    events = raw_root / "api" / "events.json"

    try:
        logger.info("START CSV INGESTION")
        ingest_csv(source_csv / "customers.csv", customers)
        ingest_csv(source_csv / "products.csv", products)
        logger.info("COMPLETE CSV INGESTION")

        logger.info("START SQLITE INGESTION")
        ingest_table(source_database, "orders", orders)
        ingest_table(source_database, "payments", payments)
        logger.info("COMPLETE SQLITE INGESTION")

        logger.info("START API INGESTION")
        ingest_api(
            os.getenv("API_URL", "http://127.0.0.1:8000/events"),
            events,
        )
        logger.info("COMPLETE API INGESTION")

        logger.info("START CSV VALIDATION")
        _require_validation("customers.csv", validate_customers(customers))
        _require_validation("products.csv", validate_products(products))
        logger.info("COMPLETE CSV VALIDATION")

        logger.info("START SQLITE VALIDATION")
        _require_validation(
            "orders.csv",
            validate_orders(orders, customers, products),
        )
        _require_validation(
            "payments.csv",
            validate_payments(payments, orders),
        )
        logger.info("COMPLETE SQLITE VALIDATION")

        logger.info("START API VALIDATION")
        _require_validation("events.json", validate_events(events, customers))
        logger.info("COMPLETE API VALIDATION")

        logger.info("START ADLS UPLOAD")
        upload_config = AdlsUploadConfig.from_env()
        uploader = AdlsUploader(create_service_client(upload_config), upload_config)
        for source, destination in UPLOADS:
            uploader.upload_file(PROJECT_ROOT / source, destination)
        logger.info("COMPLETE ADLS UPLOAD")

        logger.info("START ADLS DOWNLOAD")
        download_config = AdlsDownloadConfig.from_env()
        downloader = AdlsDownloader(
            create_download_service_client(download_config),
            download_config,
        )
        downloader.download_prefix("raw", PROJECT_ROOT / "data" / "staging" / "adls")
        logger.info("COMPLETE ADLS DOWNLOAD")

        logger.info("START DATABRICKS VOLUME UPLOAD")
        databricks_config = DatabricksVolumeUploadConfig.from_env()
        DatabricksVolumeUploader(databricks_config).upload_tree(
            PROJECT_ROOT / "data" / "staging" / "adls"
        )
        logger.info("COMPLETE DATABRICKS VOLUME UPLOAD")
    except (
        CsvIngestionError,
        SQLiteIngestionError,
        APIIngestionError,
        AdlsUploadError,
        AdlsDownloadError,
        DatabricksVolumeUploadError,
        RuntimeError,
    ) as error:
        logger.error("CORE PIPELINE FAILED: %s", error)
        return 1

    logger.info("COMPLETE CORE PIPELINE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
