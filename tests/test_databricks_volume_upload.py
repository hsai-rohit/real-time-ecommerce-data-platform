from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ingestion.databricks_volume_upload import (
    DatabricksConfigurationError,
    DatabricksLocalStagingError,
    DatabricksVolumeUploadConfig,
    DatabricksVolumeUploadError,
    DatabricksVolumeUploader,
)


class DatabricksVolumeUploadTests(unittest.TestCase):
    def test_configuration_defaults_and_environment(self) -> None:
        config = DatabricksVolumeUploadConfig.from_env()

        self.assertEqual(
            config.volume_root,
            "dbfs:/Volumes/workspace/default/ecommerce_raw",
        )

        with patch.dict(
            os.environ,
            {
                "DATABRICKS_CLI": "dbx",
                "DATABRICKS_PROFILE": "test-profile",
                "DATABRICKS_VOLUME_ROOT": "dbfs:/Volumes/a/b/volume",
            },
        ):
            config = DatabricksVolumeUploadConfig.from_env()

        self.assertEqual(config.cli_executable, "dbx")
        self.assertEqual(config.profile, "test-profile")
        self.assertEqual(
            config.volume_root,
            "dbfs:/Volumes/a/b/volume",
        )

    def test_invalid_volume_root_configuration_fails(self) -> None:
        with patch.dict(
            os.environ,
            {"DATABRICKS_VOLUME_ROOT": "/tmp/not-a-volume"},
        ):
            with self.assertRaises(DatabricksConfigurationError):
                DatabricksVolumeUploadConfig.from_env()

    @patch("ingestion.databricks_volume_upload.subprocess.run")
    def test_preserves_structure_and_file_count(self, run: Mock) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "staging"
            products_dir = root / "csv/products"

            products_dir.mkdir(parents=True)
            (products_dir / "products.csv").write_bytes(b"products")
            (root / "events.json").write_bytes(b"events")

            count = DatabricksVolumeUploader(
                DatabricksVolumeUploadConfig()
            ).upload_tree(root)

        self.assertEqual(count, 2)

        commands = [call.args[0] for call in run.call_args_list]

        expected_mkdir_command = [
            "databricks",
            "fs",
            "mkdirs",
            (
                "dbfs:/Volumes/workspace/default/ecommerce_raw/"
                "csv/products"
            ),
            "--profile",
            "hsai-rohit",
        ]

        expected_upload_command = [
            "databricks",
            "fs",
            "cp",
            str(products_dir / "products.csv"),
            (
                "dbfs:/Volumes/workspace/default/ecommerce_raw/"
                "csv/products/products.csv"
            ),
            "--overwrite",
            "--profile",
            "hsai-rohit",
        ]

        self.assertIn(expected_mkdir_command, commands)
        self.assertIn(expected_upload_command, commands)

    @patch("ingestion.databricks_volume_upload.subprocess.run")
    def test_mkdirs_and_upload_commands_use_overwrite(
        self,
        run: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "file.csv").write_bytes(b"data")

            DatabricksVolumeUploader(
                DatabricksVolumeUploadConfig()
            ).upload_tree(root)

        self.assertEqual(
            run.call_args_list[0].args[0][1:3],
            ["fs", "mkdirs"],
        )

        upload_command = run.call_args_list[1].args[0]

        self.assertIn("--overwrite", upload_command)
        self.assertIn("--profile", upload_command)
        self.assertTrue(
            all(
                call.kwargs["check"]
                for call in run.call_args_list
            )
        )

    def test_missing_local_root_fails(self) -> None:
        with self.assertRaises(DatabricksLocalStagingError):
            DatabricksVolumeUploader(
                DatabricksVolumeUploadConfig()
            ).upload_tree("does-not-exist")

    def test_file_local_root_fails(self) -> None:
        with tempfile.NamedTemporaryFile() as source:
            with self.assertRaises(DatabricksLocalStagingError):
                DatabricksVolumeUploader(
                    DatabricksVolumeUploadConfig()
                ).upload_tree(source.name)

    @patch("ingestion.databricks_volume_upload.subprocess.run")
    def test_subprocess_failure_is_wrapped(self, run: Mock) -> None:
        run.side_effect = subprocess.CalledProcessError(
            1,
            ["databricks", "fs"],
            stderr="failed",
        )

        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "file.csv").write_bytes(b"data")

            with self.assertRaises(DatabricksVolumeUploadError):
                DatabricksVolumeUploader(
                    DatabricksVolumeUploadConfig()
                ).upload_tree(directory)

    @patch("ingestion.databricks_volume_upload.subprocess.run")
    def test_symlink_is_rejected(self, run: Mock) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            tempfile.TemporaryDirectory() as outside,
        ):
            root = Path(directory)

            outside_file = Path(outside) / "secret.csv"
            outside_file.write_bytes(b"secret")

            link = root / "escape.csv"

            try:
                link.symlink_to(outside_file)
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with self.assertRaises(DatabricksVolumeUploadError):
                DatabricksVolumeUploader(
                    DatabricksVolumeUploadConfig()
                ).upload_tree(root)

        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
