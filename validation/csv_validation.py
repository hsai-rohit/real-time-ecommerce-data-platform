"""Contract checks for the raw customer and product CSV datasets."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


CUSTOMER_COLUMNS = (
    "customer_id",
    "first_name",
    "last_name",
    "email",
    "country",
    "signup_date",
)
PRODUCT_COLUMNS = (
    "product_id",
    "product_name",
    "category",
    "price",
    "currency",
    "stock_quantity",
)
INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")


@dataclass
class ValidationResult:
    """Validation outcome and actionable errors for one CSV file."""

    path: Path
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def _error(path: Path, row: int | None, column: str | None, message: str) -> str:
    location = str(path)
    if row is not None:
        location += f": row {row}"
    if column is not None:
        location += f", column '{column}'"
    return f"{location}: {message}"


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


def validate_customers(path: Path | str) -> ValidationResult:
    """Validate a customers CSV against the current source data contract."""
    file_path = Path(path)
    result = ValidationResult(file_path)
    rows = _read_rows(file_path, CUSTOMER_COLUMNS, result)
    if rows is None:
        return result

    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        for column in CUSTOMER_COLUMNS:
            if row.get(column) is None or not row[column].strip():
                result.errors.append(_error(file_path, row_number, column, "required value is missing"))

        customer_id = (row.get("customer_id") or "").strip()
        if customer_id:
            if customer_id in seen_ids:
                result.errors.append(_error(file_path, row_number, "customer_id", f"duplicate ID '{customer_id}'"))
            seen_ids.add(customer_id)

        signup_date = (row.get("signup_date") or "").strip()
        if signup_date:
            try:
                datetime.strptime(signup_date, "%Y-%m-%d")
            except ValueError:
                result.errors.append(
                    _error(file_path, row_number, "signup_date", "must be a valid YYYY-MM-DD date")
                )
    return result


def validate_products(path: Path | str) -> ValidationResult:
    """Validate a products CSV against the current source data contract."""
    file_path = Path(path)
    result = ValidationResult(file_path)
    rows = _read_rows(file_path, PRODUCT_COLUMNS, result)
    if rows is None:
        return result

    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        for column in PRODUCT_COLUMNS:
            if row.get(column) is None or not row[column].strip():
                result.errors.append(_error(file_path, row_number, column, "required value is missing"))

        product_id = (row.get("product_id") or "").strip()
        if product_id:
            if product_id in seen_ids:
                result.errors.append(_error(file_path, row_number, "product_id", f"duplicate ID '{product_id}'"))
            seen_ids.add(product_id)

        price = (row.get("price") or "").strip()
        if price:
            try:
                parsed_price = Decimal(price)
                if not parsed_price.is_finite() or parsed_price < 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                result.errors.append(_error(file_path, row_number, "price", "must be numeric and >= 0"))

        stock = (row.get("stock_quantity") or "").strip()
        if stock:
            if not INTEGER_PATTERN.fullmatch(stock) or int(stock) < 0:
                result.errors.append(
                    _error(file_path, row_number, "stock_quantity", "must be an integer and >= 0")
                )

    return result
