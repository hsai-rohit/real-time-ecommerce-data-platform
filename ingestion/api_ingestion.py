"""Raw ingestion of a local HTTP API response into the landing layer."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)


class APIIngestionError(RuntimeError):
    """Raised when an API response cannot be landed as raw JSON."""


def ingest_api(
    url: str, destination: Path | str, *, timeout: float = 10.0
) -> int | None:
    """Fetch *url* over HTTP and atomically write its complete JSON response.

    The response is parsed only to confirm that it is readable JSON and to
    report an optional ``events`` count. The original response bytes are what
    get written to the raw landing file.
    """
    destination_path = Path(destination)
    temporary_path: Path | None = None
    logger.info("Ingesting API URL %s to %s", url, destination_path)

    try:
        request = Request(url, method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:
                status = response.status
                response_body = response.read()
        except HTTPError as error:
            message = f"API returned HTTP {error.code} for {url}"
            logger.error(message)
            raise APIIngestionError(message) from error
        except URLError as error:
            message = f"API unavailable at {url}: {error.reason}"
            logger.error(message)
            raise APIIngestionError(message) from error

        logger.info("API response received: url=%s status=%s", url, status)
        if not 200 <= status < 300:
            message = f"API returned non-success HTTP status {status} for {url}"
            logger.error(message)
            raise APIIngestionError(message)

        try:
            response_text = response_body.decode("utf-8")
            response_payload = json.loads(response_text)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            message = f"API returned invalid or unreadable JSON from {url}: {error}"
            logger.error(message)
            raise APIIngestionError(message) from error

        event_count = None
        if isinstance(response_payload, dict) and isinstance(
            response_payload.get("events"), list
        ):
            event_count = len(response_payload["events"])
        logger.info("API event count if available: %s", event_count)

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination_path.parent, delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(response_body)
        os.replace(temporary_path, destination_path)
    except (OSError, APIIngestionError) as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if isinstance(error, APIIngestionError):
            logger.error("API ingestion failed: %s", error)
            raise
        message = f"Failed to write API response to {destination_path}: {error}"
        logger.exception(message)
        raise APIIngestionError(message) from error

    logger.info(
        "API ingestion succeeded: url=%s destination=%s status=%s event_count=%s",
        url,
        destination_path,
        status,
        event_count,
    )
    return event_count
