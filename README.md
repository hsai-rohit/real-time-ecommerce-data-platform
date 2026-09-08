# Real-Time E-Commerce Data Platform

This is an end-to-end, production-oriented e-commerce DataOps project.

- E-commerce data is synthetic.
- Initial real-time behavior is simulated and batch-based.
- We will only claim real-time functionality when it is actually implemented.
- Cloud resources are kept intentionally small to minimize cost.

## Status

v0.4.0 — Azure ADLS Gen2 integration in progress.

## Data Sources

The project includes fictional, deterministic local source data:

- Customer and product CSV files
- SQLite operational data for orders and payments
- A small local mock REST API for website events

Real-time behavior remains simulated and batch-oriented.

## ADLS Gen2

The repository includes a local-development ADLS Gen2 upload component at
`scripts/run_adls_upload.py`.

It uses Azure Entra ID authentication through `InteractiveBrowserCredential`
and uploads validated raw data to the configured ADLS Gen2 filesystem.

Default configuration:

- Storage account: `hsrecommercedata01`
- Filesystem: `ecommerce`
- Tenant: configured through `AZURE_TENANT_ID`

These values can be overridden with:

- `ADLS_ACCOUNT_NAME`
- `ADLS_FILESYSTEM`
- `AZURE_TENANT_ID`

The uploader uses idempotent overwrite behavior so rerunning the upload
writes to the same destination paths rather than creating duplicate files.

The local-to-Azure upload has been verified against the real ADLS Gen2
environment. A complete raw dataset consisting of customers, products,
orders, payments, and website events is currently stored under the
`ecommerce/raw/` path.

A real Azure upload is not triggered automatically by the repository.
