"""Upload local ADLS staging files into the Databricks managed volume."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.databricks_volume_upload import (
    DatabricksVolumeUploadConfig,
    DatabricksVolumeUploadError,
    DatabricksVolumeUploader,
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        config = DatabricksVolumeUploadConfig.from_env()
        count = DatabricksVolumeUploader(config).upload_tree(
            PROJECT_ROOT / "data" / "staging" / "adls"
        )
        logging.info("Databricks volume upload completed: %d files", count)
        return 0
    except DatabricksVolumeUploadError as error:
        logging.error("Databricks volume upload failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
