# Source Data Contracts

All source data in this project is deterministic and fictional. Identifiers are stable across the CSV, SQLite, and mock REST API sources so future pipeline stages can join records reliably. Website events are authenticated-session events in this initial source model; therefore, `customer_id` is required and anonymous events are not represented.

## Customers

| Field | Type | Required | Key / relationship | Description | Example |
| --- | --- | --- | --- | --- | --- |
| `customer_id` | string | Yes | Primary key | Stable customer identifier. | `CUS-001` |
| `first_name` | string | Yes | — | Fictional given name. | `Avery` |
| `last_name` | string | Yes | — | Fictional family name. | `Stone` |
| `email` | string | Yes | — | Fictional contact address using the reserved `.test` domain. | `avery.stone@example.test` |
| `country` | string | Yes | — | Customer country. | `India` |
| `signup_date` | date (ISO 8601) | Yes | — | Date the customer joined. | `2025-01-01` |

## Products

| Field | Type | Required | Key / relationship | Description | Example |
| --- | --- | --- | --- | --- | --- |
| `product_id` | string | Yes | Primary key | Stable product identifier. | `PRD-001` |
| `product_name` | string | Yes | — | Product display name. | `Wireless Keyboard` |
| `category` | string | Yes | — | Product category. | `Electronics` |
| `price` | decimal(10,2) | Yes | — | Current synthetic unit price. | `49.99` |
| `currency` | string (ISO 4217) | Yes | — | Currency for the price. | `USD` |
| `stock_quantity` | integer | Yes | — | Available synthetic inventory count. | `82` |

## Orders

| Field | Type | Required | Key / relationship | Description | Example |
| --- | --- | --- | --- | --- | --- |
| `order_id` | string | Yes | Primary key | Stable order identifier. | `ORD-0001` |
| `customer_id` | string | Yes | Foreign key to `customers.customer_id` | Customer who placed the order. | `CUS-001` |
| `product_id` | string | Yes | Foreign key to `products.product_id` | Product in this single-line order model. | `PRD-001` |
| `order_timestamp` | timestamp (ISO 8601 UTC) | Yes | — | Time the order was created. | `2026-01-05T16:14:00Z` |
| `quantity` | integer | Yes | — | Units ordered; always positive. | `2` |
| `unit_price` | decimal(10,2) | Yes | — | Price per unit at order time. | `49.99` |
| `order_status` | string | Yes | — | Current operational status. | `completed` |

## Payments

| Field | Type | Required | Key / relationship | Description | Example |
| --- | --- | --- | --- | --- | --- |
| `payment_id` | string | Yes | Primary key | Stable payment identifier. | `PAY-0001` |
| `order_id` | string | Yes | Foreign key to `orders.order_id` | Order being paid for. | `ORD-0001` |
| `payment_timestamp` | timestamp (ISO 8601 UTC) | Yes | — | Time the payment record was created. | `2026-01-05T16:16:00Z` |
| `payment_method` | string | Yes | — | Fictional payment channel. | `card` |
| `payment_status` | string | Yes | — | Operational payment status. | `completed` |
| `amount` | decimal(10,2) | Yes | — | Total payment amount. | `99.98` |
| `currency` | string (ISO 4217) | Yes | — | Currency for the payment. | `USD` |

## Website Events

| Field | Type | Required | Key / relationship | Description | Example |
| --- | --- | --- | --- | --- | --- |
| `event_id` | string | Yes | Primary key | Stable event identifier. | `EVT-00001` |
| `customer_id` | string | Yes | Foreign key to `customers.customer_id` | Customer associated with the session. | `CUS-001` |
| `session_id` | string | Yes | — | Stable identifier for a browsing session. | `SES-0001` |
| `event_timestamp` | timestamp (ISO 8601 UTC) | Yes | — | Time the website event occurred. | `2026-01-20T08:09:00Z` |
| `event_type` | string | Yes | — | User interaction classification. | `product_view` |
| `page` | string | Yes | — | Site path associated with the event. | `/products` |
| `device_type` | string | Yes | — | Client device category. | `mobile` |
