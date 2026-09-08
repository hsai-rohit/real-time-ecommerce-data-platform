"""Generate deterministic, fictional source data for local development."""

from __future__ import annotations

import csv
import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


SEED = 20260908
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "data" / "source"
CSV_ROOT = SOURCE_ROOT / "csv"
SQLITE_ROOT = SOURCE_ROOT / "sqlite"
API_ROOT = SOURCE_ROOT / "api"


CUSTOMER_NAMES = [
    ("Avery", "Stone"), ("Jordan", "Reed"), ("Casey", "Mills"),
    ("Riley", "Hart"), ("Morgan", "Blake"), ("Taylor", "Quinn"),
    ("Cameron", "Vale"), ("Parker", "Sloan"), ("Drew", "Lane"),
    ("Hayden", "Brooks"), ("Rowan", "Cole"), ("Skyler", "Nash"),
    ("Reese", "Ford"), ("Emerson", "Wells"), ("Logan", "Pierce"),
    ("Sydney", "Rowe"), ("Bailey", "Cruz"), ("Kendall", "Shaw"),
    ("Marley", "Voss"), ("Alex", "Winter"),
]
COUNTRIES = ["India", "United States", "United Kingdom", "Canada", "Australia"]
PRODUCTS = [
    ("Wireless Keyboard", "Electronics", "49.99", "USD", 82),
    ("Ceramic Travel Mug", "Home", "18.50", "USD", 120),
    ("Linen Notebook", "Stationery", "12.75", "USD", 200),
    ("USB-C Hub", "Electronics", "34.00", "USD", 65),
    ("Cotton Throw", "Home", "42.25", "USD", 47),
    ("Desk Lamp", "Home", "39.95", "USD", 58),
    ("Canvas Tote", "Accessories", "16.00", "USD", 150),
    ("Insulated Bottle", "Outdoors", "27.50", "USD", 93),
    ("Mechanical Pencil", "Stationery", "9.99", "USD", 300),
    ("Laptop Stand", "Electronics", "44.75", "USD", 72),
    ("Yoga Mat", "Fitness", "31.20", "USD", 84),
    ("Packing Cubes", "Travel", "24.60", "USD", 110),
    ("Bluetooth Speaker", "Electronics", "55.00", "USD", 39),
    ("Apron", "Home", "22.40", "USD", 95),
    ("Resistance Bands", "Fitness", "14.80", "USD", 180),
]


def iso_timestamp(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_customers() -> list[dict[str, str]]:
    signup_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "customer_id": f"CUS-{index:03d}",
            "first_name": first_name,
            "last_name": last_name,
            "email": f"{first_name.lower()}.{last_name.lower()}@example.test",
            "country": COUNTRIES[index % len(COUNTRIES)],
            "signup_date": (signup_start + timedelta(days=index * 11)).date().isoformat(),
        }
        for index, (first_name, last_name) in enumerate(CUSTOMER_NAMES, start=1)
    ]


def build_products() -> list[dict[str, object]]:
    return [
        {
            "product_id": f"PRD-{index:03d}",
            "product_name": name,
            "category": category,
            "price": price,
            "currency": currency,
            "stock_quantity": stock,
        }
        for index, (name, category, price, currency, stock) in enumerate(PRODUCTS, start=1)
    ]


def build_orders_and_payments(
    customers: list[dict[str, str]], products: list[dict[str, object]], rng: random.Random
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    order_start = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    orders: list[dict[str, object]] = []
    payments: list[dict[str, object]] = []
    for index in range(1, 41):
        customer = rng.choice(customers)
        product = rng.choice(products)
        quantity = rng.randint(1, 3)
        timestamp = order_start + timedelta(hours=index * 7, minutes=rng.randint(0, 45))
        status = "completed" if index <= 36 else "pending"
        unit_price = float(str(product["price"]))
        order_id = f"ORD-{index:04d}"
        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "product_id": product["product_id"],
                "order_timestamp": iso_timestamp(timestamp),
                "quantity": quantity,
                "unit_price": f"{unit_price:.2f}",
                "order_status": status,
            }
        )
        payments.append(
            {
                "payment_id": f"PAY-{index:04d}",
                "order_id": order_id,
                "payment_timestamp": iso_timestamp(timestamp + timedelta(minutes=2)),
                "payment_method": rng.choice(["card", "wallet", "bank_transfer"]),
                "payment_status": "completed" if status == "completed" else "pending",
                "amount": f"{quantity * unit_price:.2f}",
                "currency": product["currency"],
            }
        )
    return orders, payments


def build_events(customers: list[dict[str, str]], rng: random.Random) -> list[dict[str, str]]:
    event_start = datetime(2026, 1, 20, 8, 0, tzinfo=timezone.utc)
    event_types = ["page_view", "product_view", "add_to_cart", "checkout_started"]
    pages = ["/", "/products", "/cart", "/checkout", "/account"]
    devices = ["desktop", "mobile", "tablet"]
    events: list[dict[str, str]] = []
    for index in range(1, 101):
        customer = rng.choice(customers)
        events.append(
            {
                "event_id": f"EVT-{index:05d}",
                "customer_id": customer["customer_id"],
                "session_id": f"SES-{rng.randint(1, 35):04d}",
                "event_timestamp": iso_timestamp(event_start + timedelta(minutes=index * 9)),
                "event_type": rng.choice(event_types),
                "page": rng.choice(pages),
                "device_type": rng.choice(devices),
            }
        )
    return events


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_sqlite(path: Path, orders: list[dict[str, object]], payments: list[dict[str, object]]) -> None:
    if path.exists():
        path.unlink()
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                order_timestamp TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                unit_price NUMERIC NOT NULL CHECK (unit_price >= 0),
                order_status TEXT NOT NULL
            );
            CREATE TABLE payments (
                payment_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                payment_timestamp TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                payment_status TEXT NOT NULL,
                amount NUMERIC NOT NULL CHECK (amount >= 0),
                currency TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );
            """
        )
        connection.executemany(
            """
            INSERT INTO orders VALUES (
                :order_id, :customer_id, :product_id, :order_timestamp,
                :quantity, :unit_price, :order_status
            )
            """,
            orders,
        )
        connection.executemany(
            """
            INSERT INTO payments VALUES (
                :payment_id, :order_id, :payment_timestamp, :payment_method,
                :payment_status, :amount, :currency
            )
            """,
            payments,
        )


def main() -> None:
    for directory in (CSV_ROOT, SQLITE_ROOT, API_ROOT):
        directory.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    customers = build_customers()
    products = build_products()
    orders, payments = build_orders_and_payments(customers, products, rng)
    events = build_events(customers, rng)

    write_csv(CSV_ROOT / "customers.csv", customers)
    write_csv(CSV_ROOT / "products.csv", products)
    write_sqlite(SQLITE_ROOT / "ecommerce.db", orders, payments)
    with (API_ROOT / "events.json").open("w", encoding="utf-8") as handle:
        json.dump(events, handle, indent=2)
        handle.write("\n")

    print(f"Generated {len(customers)} customers and {len(products)} products in {CSV_ROOT}")
    print(f"Generated {len(orders)} orders and {len(payments)} payments in {SQLITE_ROOT}")
    print(f"Generated {len(events)} website events in {API_ROOT}")


if __name__ == "__main__":
    main()
