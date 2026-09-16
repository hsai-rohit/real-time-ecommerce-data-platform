from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ingestion.adls_download import (
    AdlsDownloadConfig,
    AdlsDownloadConfigurationError,
    AdlsDownloadError,
    AdlsDownloader,
    AdlsLocalStagingError,
    create_download_service_client,
)


def test_configuration_defaults_and_environment(monkeypatch):
    monkeypatch.setenv("ADLS_ACCOUNT_NAME", "testaccount")
    monkeypatch.setenv("ADLS_FILESYSTEM", "testfilesystem")
    monkeypatch.setenv("AZURE_TENANT_ID", "test-tenant")

    config = AdlsDownloadConfig.from_env()

    assert config.account_name == "testaccount"
    assert config.filesystem == "testfilesystem"
    assert config.tenant_id == "test-tenant"
    assert config.account_url == "https://testaccount.dfs.core.windows.net"


def test_client_uses_explicit_tenant():
    config = AdlsDownloadConfig(
        account_name="testaccount",
        filesystem="testfilesystem",
        tenant_id="test-tenant",
    )

    with patch(
        "ingestion.adls_download.InteractiveBrowserCredential"
    ) as credential_cls, patch(
        "ingestion.adls_download.DataLakeServiceClient"
    ) as service_client_cls:
        create_download_service_client(config)

    credential_cls.assert_called_once_with(tenant_id="test-tenant")
    service_client_cls.assert_called_once_with(
        account_url="https://testaccount.dfs.core.windows.net",
        credential=credential_cls.return_value,
    )


def test_preserves_directory_structure_and_bytes(tmp_path):
    filesystem = Mock()

    files = {
        "raw/csv/customers/customers.csv": b"customer,data\n",
        "raw/sqlite/orders/orders.csv": b"order,data\n",
    }

    def get_paths(*, path, recursive):
        assert path == "raw"
        assert recursive is True

        return [
            type(
                "PathInfo",
                (),
                {
                    "name": remote_name,
                    "is_directory": False,
                },
            )()
            for remote_name in files
        ]

    filesystem.get_paths.side_effect = get_paths

    def get_file_client(remote_name):
        client = Mock()
        client.download_file.return_value.readall.return_value = files[
            remote_name
        ]
        return client

    filesystem.get_file_client.side_effect = get_file_client

    service_client = Mock()
    service_client.get_file_system_client.return_value = filesystem

    config = AdlsDownloadConfig(
        account_name="testaccount",
        filesystem="testfilesystem",
        tenant_id="test-tenant",
    )

    downloader = AdlsDownloader(service_client, config)

    downloaded = downloader.download_prefix(
        prefix="raw",
        staging_root=tmp_path / "staging",
    )

    assert downloaded == 2

    assert (
        tmp_path / "staging/csv/customers/customers.csv"
    ).read_bytes() == b"customer,data\n"

    assert (
        tmp_path / "staging/sqlite/orders/orders.csv"
    ).read_bytes() == b"order,data\n"


def test_dictionary_path_metadata_is_supported(tmp_path):
    filesystem = Mock()

    filesystem.get_paths.return_value = [
        {
            "name": "raw/file.csv",
            "is_directory": False,
        }
    ]

    file_client = Mock()
    file_client.download_file.return_value.readall.return_value = b"data"
    filesystem.get_file_client.return_value = file_client

    service_client = Mock()
    service_client.get_file_system_client.return_value = filesystem

    config = AdlsDownloadConfig(
        account_name="testaccount",
        filesystem="testfilesystem",
        tenant_id="test-tenant",
    )

    downloader = AdlsDownloader(service_client, config)

    downloaded = downloader.download_prefix(
        prefix="raw",
        staging_root=tmp_path / "staging",
    )

    assert downloaded == 1
    assert (tmp_path / "staging/file.csv").read_bytes() == b"data"


def test_path_traversal_is_rejected(tmp_path):
    filesystem = Mock()

    filesystem.get_paths.return_value = [
        type(
            "PathInfo",
            (),
            {
                "name": "raw/../outside.txt",
                "is_directory": False,
            },
        )()
    ]

    service_client = Mock()
    service_client.get_file_system_client.return_value = filesystem

    config = AdlsDownloadConfig(
        account_name="testaccount",
        filesystem="testfilesystem",
        tenant_id="test-tenant",
    )

    downloader = AdlsDownloader(service_client, config)

    with pytest.raises(AdlsDownloadError):
        downloader.download_prefix(
            prefix="raw",
            staging_root=tmp_path / "staging",
        )

    filesystem.get_file_client.assert_not_called()


def test_file_destination_fails(tmp_path):
    staging_file = tmp_path / "staging"
    staging_file.write_text("not a directory")

    service_client = Mock()

    config = AdlsDownloadConfig(
        account_name="testaccount",
        filesystem="testfilesystem",
        tenant_id="test-tenant",
    )

    downloader = AdlsDownloader(service_client, config)

    with pytest.raises(AdlsLocalStagingError):
        downloader.download_prefix(
            prefix="raw",
            staging_root=staging_file,
        )


def test_azure_failure_is_wrapped(tmp_path):
    filesystem = Mock()
    filesystem.get_paths.side_effect = RuntimeError("Azure failure")

    service_client = Mock()
    service_client.get_file_system_client.return_value = filesystem

    config = AdlsDownloadConfig(
        account_name="testaccount",
        filesystem="testfilesystem",
        tenant_id="test-tenant",
    )

    downloader = AdlsDownloader(service_client, config)

    with pytest.raises(AdlsDownloadError):
        downloader.download_prefix(
            prefix="raw",
            staging_root=tmp_path / "staging",
        )


def test_empty_prefix_is_rejected(tmp_path):
    service_client = Mock()

    config = AdlsDownloadConfig(
        account_name="testaccount",
        filesystem="testfilesystem",
        tenant_id="test-tenant",
    )

    downloader = AdlsDownloader(service_client, config)

    with pytest.raises(AdlsDownloadConfigurationError):
        downloader.download_prefix(
            prefix="/",
            staging_root=tmp_path / "staging",
        )
