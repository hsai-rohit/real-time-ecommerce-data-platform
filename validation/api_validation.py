"""Contract and customer-reference checks for the raw events API response."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from validation.csv_validation import ValidationResult, _error


TOP_LEVEL_FIELDS = {"events", "count", "total"}
EVENT_FIELDS = {
    "event_id",
    "customer_id",
    "session_id",
    "event_timestamp",
    "event_type",
    "page",
    "device_type",
}
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _event_error(path: Path, index: int, field: str | None, message: str) -> str:
    location = f"{path}: event index {index}"
    if field is not None:
        location += f", field '{field}'"
    return f"{location}: {message}"


def _load_customer_ids(path: Path, errors: list[str]) -> set[str]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if "customer_id" not in (reader.fieldnames or ()):
                errors.append(_error(path, 1, "customer_id", "reference column is missing"))
                return set()
            return {
                (row.get("customer_id") or "").strip()
                for row in reader
                if (row.get("customer_id") or "").strip()
            }
    except (OSError, csv.Error, UnicodeError) as error:
        errors.append(_error(path, None, None, f"cannot read customer references: {error}"))
        return set()


def validate_events(path: Path | str, customers_path: Path | str) -> ValidationResult:
    """Validate an API response JSON file and customer relationships."""
    file_path = Path(path)
    result = ValidationResult(file_path)
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as error:
        result.errors.append(_error(file_path, None, None, f"cannot read file: {error}"))
        return result
    except (json.JSONDecodeError, UnicodeError) as error:
        result.errors.append(_error(file_path, None, None, f"invalid or unreadable JSON: {error}"))
        return result

    if not isinstance(payload, dict):
        result.errors.append(_error(file_path, None, None, "top level must be an object/dictionary"))
        return result
    if set(payload) != TOP_LEVEL_FIELDS:
        result.errors.append(
            _error(file_path, None, None, f"expected exactly top-level fields {sorted(TOP_LEVEL_FIELDS)}, found {sorted(payload)}")
        )

    events = payload.get("events")
    count = payload.get("count")
    total = payload.get("total")
    if not isinstance(events, list):
        result.errors.append(_error(file_path, None, "events", "must be a list"))
    if type(count) is not int:
        result.errors.append(_error(file_path, None, "count", "must be an integer"))
    if type(total) is not int:
        result.errors.append(_error(file_path, None, "total", "must be an integer"))
    if isinstance(events, list):
        if type(count) is int and count != len(events):
            result.errors.append(_error(file_path, None, "count", f"must equal number of events ({len(events)})"))
        if type(total) is int and total != len(events):
            result.errors.append(_error(file_path, None, "total", f"must equal number of events ({len(events)})"))

    customer_ids = _load_customer_ids(Path(customers_path), result.errors)
    seen_event_ids: set[str] = set()
    if not isinstance(events, list):
        return result

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            result.errors.append(_event_error(file_path, index, None, "must be an object/dictionary"))
            continue
        if set(event) != EVENT_FIELDS:
            result.errors.append(
                _event_error(file_path, index, None, f"expected exactly event fields {sorted(EVENT_FIELDS)}, found {sorted(event)}")
            )
        for field in EVENT_FIELDS:
            value = event.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                result.errors.append(_event_error(file_path, index, field, "required value is missing or empty"))

        event_id = event.get("event_id")
        if isinstance(event_id, str) and event_id.strip():
            event_id = event_id.strip()
            if event_id in seen_event_ids:
                result.errors.append(_event_error(file_path, index, "event_id", f"duplicate ID '{event_id}'"))
            seen_event_ids.add(event_id)
        customer_id = event.get("customer_id")
        if isinstance(customer_id, str) and customer_id.strip() and customer_id.strip() not in customer_ids:
            result.errors.append(_event_error(file_path, index, "customer_id", f"reference '{customer_id.strip()}' not found in customers.csv"))
        timestamp = event.get("event_timestamp")
        if isinstance(timestamp, str) and timestamp.strip():
            try:
                datetime.strptime(timestamp.strip(), TIMESTAMP_FORMAT)
            except ValueError:
                result.errors.append(_event_error(file_path, index, "event_timestamp", "must be a valid UTC timestamp in YYYY-MM-DDTHH:MM:SSZ format"))
    return result
