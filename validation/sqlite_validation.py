"""Contract and relationship checks for raw orders and payments CSV files."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from validation.csv_validation import ValidationResult, _error


ORDERS_COLUMNS = (
    "order_id",
    "customer_id",
    "product_id",
    "order_timestamp",
    "quantity",
    "unit_price",
    "order_status",
)
PAYMENTS_COLUMNS = (
    "payment_id",
    "order_id",
    "payment_timestamp",
    "payment_method",
    "payment_status",
    "amount",
    "currency",
)
INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _read_rows(path: Path, expected_columns: tuple[str, ...], result: ValidationResult):
    try:
        handle = path.open("r", encoding="utf-8", newline="")
    except OSError as error:
        result.errors.append(_error(path, None, None, f"cannot read file: {error}"))
        return None

    try:
        reader = csv.DictReader(handle)
        actual_columns = tuple(reader.fieldnames or ())
        if actual_columns != expected_columns:
            result.errors.append(
                _error(
                    path,
                    1,
                    None,
                    f"expected columns in order {list(expected_columns)}, "
                    f"found {list(actual_columns)}",
                )
            )
            return None
        return list(reader)
    except (csv.Error, UnicodeError) as error:
        result.errors.append(_error(path, None, None, f"cannot parse CSV: {error}"))
        return None
    finally:
        handle.close()


def _load_ids(path: Path, column: str, errors: list[str]) -> set[str]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if column not in (reader.fieldnames or ()):
                errors.append(_error(path, 1, column, "reference column is missing"))
                return set()
            return {
                (row.get(column) or "").strip()
                for row in reader
                if (row.get(column) or "").strip()
            }
    except (OSError, csv.Error, UnicodeError) as error:
        errors.append(_error(path, None, None, f"cannot read reference data: {error}"))
        return set()


def _required(row: dict[str, str | None], columns: tuple[str, ...], path: Path, row_number: int, errors: list[str]) -> None:
    for column in columns:
        if row.get(column) is None or not row[column].strip():
            errors.append(_error(path, row_number, column, "required value is missing"))


def _validate_timestamp(value: str, path: Path, row_number: int, column: str, errors: list[str]) -> None:
    try:
        datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError:
        errors.append(_error(path, row_number, column, "must be a valid UTC timestamp in YYYY-MM-DDTHH:MM:SSZ format"))


def _validate_decimal(value: str, path: Path, row_number: int, column: str, errors: list[str]) -> None:
    try:
        parsed = Decimal(value)
        if not parsed.is_finite() or parsed < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        errors.append(_error(path, row_number, column, "must be numeric and >= 0"))


def _validate_positive_integer(value: str, path: Path, row_number: int, column: str, errors: list[str]) -> None:
    if not INTEGER_PATTERN.fullmatch(value) or int(value) <= 0:
        errors.append(_error(path, row_number, column, "must be an integer > 0"))


def validate_orders(
    path: Path | str,
    customers_path: Path | str,
    products_path: Path | str,
) -> ValidationResult:
    """Validate orders and customer/product relationships."""
    file_path = Path(path)
    result = ValidationResult(file_path)
    customer_ids = _load_ids(Path(customers_path), "customer_id", result.errors)
    product_ids = _load_ids(Path(products_path), "product_id", result.errors)
    rows = _read_rows(file_path, ORDERS_COLUMNS, result)
    if rows is None:
        return result

    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        _required(row, ORDERS_COLUMNS, file_path, row_number, result.errors)
        order_id = (row.get("order_id") or "").strip()
        customer_id = (row.get("customer_id") or "").strip()
        product_id = (row.get("product_id") or "").strip()
        if order_id:
            if order_id in seen_ids:
                result.errors.append(_error(file_path, row_number, "order_id", f"duplicate ID '{order_id}'"))
            seen_ids.add(order_id)
        if customer_id and customer_id not in customer_ids:
            result.errors.append(_error(file_path, row_number, "customer_id", f"reference '{customer_id}' not found in customers.csv"))
        if product_id and product_id not in product_ids:
            result.errors.append(_error(file_path, row_number, "product_id", f"reference '{product_id}' not found in products.csv"))
        timestamp = (row.get("order_timestamp") or "").strip()
        if timestamp:
            _validate_timestamp(timestamp, file_path, row_number, "order_timestamp", result.errors)
        quantity = (row.get("quantity") or "").strip()
        if quantity:
            _validate_positive_integer(quantity, file_path, row_number, "quantity", result.errors)
        unit_price = (row.get("unit_price") or "").strip()
        if unit_price:
            _validate_decimal(unit_price, file_path, row_number, "unit_price", result.errors)
    return result


def validate_payments(path: Path | str, orders_path: Path | str) -> ValidationResult:
    """Validate payments and payment-to-order relationships."""
    file_path = Path(path)
    result = ValidationResult(file_path)
    order_ids = _load_ids(Path(orders_path), "order_id", result.errors)
    rows = _read_rows(file_path, PAYMENTS_COLUMNS, result)
    if rows is None:
        return result

    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        _required(row, PAYMENTS_COLUMNS, file_path, row_number, result.errors)
        payment_id = (row.get("payment_id") or "").strip()
        order_id = (row.get("order_id") or "").strip()
        if payment_id:
            if payment_id in seen_ids:
                result.errors.append(_error(file_path, row_number, "payment_id", f"duplicate ID '{payment_id}'"))
            seen_ids.add(payment_id)
        if order_id and order_id not in order_ids:
            result.errors.append(_error(file_path, row_number, "order_id", f"reference '{order_id}' not found in orders.csv"))
        timestamp = (row.get("payment_timestamp") or "").strip()
        if timestamp:
            _validate_timestamp(timestamp, file_path, row_number, "payment_timestamp", result.errors)
        amount = (row.get("amount") or "").strip()
        if amount:
            _validate_decimal(amount, file_path, row_number, "amount", result.errors)
    return result
