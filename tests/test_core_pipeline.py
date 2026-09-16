from __future__ import annotations

import os
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

import scripts.run_core_pipeline as pipeline
from ingestion.adls_upload import AdlsUploadError
from ingestion.api_ingestion import APIIngestionError
from ingestion.csv_ingestion import CsvIngestionError
from ingestion.databricks_volume_upload import DatabricksVolumeUploadError
from ingestion.sqlite_ingestion import SQLiteIngestionError


class CorePipelineTests(unittest.TestCase):
    @contextmanager
    def mocked_pipeline(self):
        with (
            patch.object(pipeline, "ingest_csv") as ingest_csv,
            patch.object(pipeline, "ingest_table") as ingest_table,
            patch.object(pipeline, "ingest_api") as ingest_api,
            patch.object(pipeline, "validate_customers") as validate_customers,
            patch.object(pipeline, "validate_products") as validate_products,
            patch.object(pipeline, "validate_orders") as validate_orders,
            patch.object(pipeline, "validate_payments") as validate_payments,
            patch.object(pipeline, "validate_events") as validate_events,
            patch.object(pipeline, "AdlsUploadConfig") as upload_config_class,
            patch.object(pipeline, "create_service_client") as create_upload_client,
            patch.object(pipeline, "AdlsUploader") as uploader_class,
            patch.object(pipeline, "AdlsDownloadConfig") as download_config_class,
            patch.object(pipeline, "create_download_service_client") as create_download_client,
            patch.object(pipeline, "AdlsDownloader") as downloader_class,
            patch.object(pipeline, "DatabricksVolumeUploadConfig") as volume_config_class,
            patch.object(pipeline, "DatabricksVolumeUploader") as volume_uploader_class,
        ):
            for validator in (
                validate_customers,
                validate_products,
                validate_orders,
                validate_payments,
                validate_events,
            ):
                validator.return_value = SimpleNamespace(passed=True, errors=[])
            upload_config = upload_config_class.from_env.return_value
            download_config = download_config_class.from_env.return_value
            upload_client = create_upload_client.return_value
            download_client = create_download_client.return_value
            uploader = uploader_class.return_value
            downloader = downloader_class.return_value
            volume_uploader = volume_uploader_class.return_value
            yield locals()

    def test_successful_pipeline_runs_in_dependency_order(self) -> None:
        order: list[str] = []
        with self.mocked_pipeline() as mocks:
            mocks["ingest_csv"].side_effect = lambda *args: order.append("csv ingestion")
            mocks["ingest_table"].side_effect = lambda *args: order.append("sqlite ingestion")
            mocks["ingest_api"].side_effect = lambda *args, **kwargs: order.append("api ingestion")
            for validator in (
                mocks["validate_customers"],
                mocks["validate_products"],
                mocks["validate_orders"],
                mocks["validate_payments"],
                mocks["validate_events"],
            ):
                validator.side_effect = lambda *args, _order=order, **kwargs: _order.append("validation") or SimpleNamespace(passed=True, errors=[])
            mocks["uploader"].upload_file.side_effect = lambda *args: order.append("adls upload")
            mocks["downloader"].download_prefix.side_effect = lambda *args: order.append("adls download")
            mocks["volume_uploader"].upload_tree.side_effect = lambda *args: order.append("volume upload")

            result = pipeline.main()

        self.assertEqual(result, 0)
        self.assertEqual(
            order,
            [
                "csv ingestion",
                "csv ingestion",
                "sqlite ingestion",
                "sqlite ingestion",
                "api ingestion",
                "validation",
                "validation",
                "validation",
                "validation",
                "validation",
                "adls upload",
                "adls upload",
                "adls upload",
                "adls upload",
                "adls upload",
                "adls download",
                "volume upload",
            ],
        )

    def test_validation_failure_stops_before_cloud_stages(self) -> None:
        with self.mocked_pipeline() as mocks:
            mocks["validate_products"].return_value = SimpleNamespace(
                passed=False, errors=["invalid product"]
            )
            result = pipeline.main()

        self.assertEqual(result, 1)
        mocks["uploader"].upload_file.assert_not_called()
        mocks["downloader"].download_prefix.assert_not_called()
        mocks["volume_uploader"].upload_tree.assert_not_called()

    def test_ingestion_failure_stops_before_validation_and_cloud(self) -> None:
        with self.mocked_pipeline() as mocks:
            mocks["ingest_table"].side_effect = SQLiteIngestionError("ingestion failed")
            result = pipeline.main()

        self.assertEqual(result, 1)
        for validator in (
            mocks["validate_customers"],
            mocks["validate_products"],
            mocks["validate_orders"],
            mocks["validate_payments"],
            mocks["validate_events"],
        ):
            validator.assert_not_called()
        mocks["uploader"].upload_file.assert_not_called()
        mocks["downloader"].download_prefix.assert_not_called()
        mocks["volume_uploader"].upload_tree.assert_not_called()

    def test_adls_upload_failure_stops_later_stages(self) -> None:
        with self.mocked_pipeline() as mocks:
            mocks["uploader"].upload_file.side_effect = AdlsUploadError("upload failed")
            result = pipeline.main()

        self.assertEqual(result, 1)
        mocks["downloader"].download_prefix.assert_not_called()
        mocks["volume_uploader"].upload_tree.assert_not_called()

    def test_databricks_upload_failure_returns_one(self) -> None:
        with self.mocked_pipeline() as mocks:
            mocks["volume_uploader"].upload_tree.side_effect = DatabricksVolumeUploadError("volume failed")
            result = pipeline.main()

        self.assertEqual(result, 1)
        mocks["downloader"].download_prefix.assert_called_once()

    def test_api_url_is_propagated(self) -> None:
        with self.mocked_pipeline() as mocks, patch.dict(
            os.environ, {"API_URL": "http://example.test/events"}
        ):
            result = pipeline.main()

        self.assertEqual(result, 0)
        self.assertEqual(mocks["ingest_api"].call_args.args[0], "http://example.test/events")


if __name__ == "__main__":
    unittest.main()
