from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from ingestion.adls_upload import (
    AdlsConfigurationError,
    AdlsLocalFileError,
    AdlsUploadConfig,
    AdlsUploader,
    create_service_client,
)


class AdlsUploadTests(unittest.TestCase):
    def test_uploads_bytes_and_creates_parent_directories(self) -> None:
        service = Mock()
        filesystem = service.get_file_system_client.return_value
        directory = filesystem.get_directory_client.return_value
        file_client = filesystem.get_file_client.return_value
        with tempfile.TemporaryDirectory() as directory_path:
            source = Path(directory_path) / "input.bin"
            source.write_bytes(b"raw\x00bytes")
            AdlsUploader(service, AdlsUploadConfig()).upload_file(source, "raw/csv/input.bin")

        service.get_file_system_client.assert_called_once_with("ecommerce")
        self.assertEqual(
            filesystem.get_directory_client.call_args_list,
            [call("raw"), call("raw/csv")],
        )
        self.assertEqual(directory.create_directory.call_count, 2)
        filesystem.get_file_client.assert_called_once_with("raw/csv/input.bin")
        file_client.upload_data.assert_called_once_with(b"raw\x00bytes", overwrite=True)

    def test_existing_parent_directory_is_allowed(self) -> None:
        service = Mock()
        filesystem = service.get_file_system_client.return_value
        filesystem.get_directory_client.return_value.create_directory.side_effect = (
            __import__("azure.core.exceptions", fromlist=["ResourceExistsError"]).ResourceExistsError()
        )
        with tempfile.NamedTemporaryFile() as source:
            AdlsUploader(service, AdlsUploadConfig()).upload_file(source.name, "raw/file.txt")
        filesystem.get_file_client.return_value.upload_data.assert_called_once_with(b"", overwrite=True)

    def test_missing_local_file_fails_before_client_upload(self) -> None:
        service = Mock()
        with self.assertRaises(AdlsLocalFileError):
            AdlsUploader(service, AdlsUploadConfig()).upload_file("does-not-exist", "raw/file")
        service.get_file_system_client.assert_called_once_with("ecommerce")

    @patch("ingestion.adls_upload.DataLakeServiceClient")
    @patch("ingestion.adls_upload.InteractiveBrowserCredential")
    def test_client_uses_explicit_tenant(self, credential, service_client) -> None:
        config = AdlsUploadConfig(account_name="account", filesystem="fs", tenant_id="tenant")
        create_service_client(config)
        credential.assert_called_once_with(tenant_id="tenant")
        service_client.assert_called_once_with(
            account_url="https://account.dfs.core.windows.net",
            credential=credential.return_value,
        )

    @patch.dict("os.environ", {"ADLS_ACCOUNT_NAME": "", "ADLS_FILESYSTEM": "fs", "AZURE_TENANT_ID": "tenant"})
    def test_empty_configuration_fails(self) -> None:
        with self.assertRaises(AdlsConfigurationError):
            AdlsUploadConfig.from_env()


if __name__ == "__main__":
    unittest.main()
