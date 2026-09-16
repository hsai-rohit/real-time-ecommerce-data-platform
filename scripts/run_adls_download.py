"""Download the ADLS raw prefix into local staging."""

from __future__ import annotations

import logging
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


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        config = AdlsDownloadConfig.from_env()
        downloader = AdlsDownloader(create_download_service_client(config), config)
        count = downloader.download_prefix("raw", PROJECT_ROOT / "data" / "staging" / "adls")
        logging.info("ADLS download completed: %d files", count)
        return 0
    except AdlsDownloadError as error:
        logging.error("ADLS download failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
