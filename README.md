# SiplyGo Prototype

This project is a FastAPI prototype. This update adds initial database scaffolding
using SQLAlchemy and a Docker Compose setup with PostgreSQL.

## Running with Docker Compose

1. Ensure the environment variables `POSTGRES_USER`,
   `POSTGRES_PASSWORD`, and `POSTGRES_DB` are set. `DATABASE_URL` will be
   automatically constructed from these values (override it to use an
   external database). Optionally set `POSTGRES_HOST` if the database is
   not reachable via the default `postgres` hostname.
2. Start the containers:

```
docker compose up --build
```

The app will then be available at http://localhost:8000.

## Database

- Models are defined in `models.py`.
- Database engine and session helpers live in `database.py`.
- Tables are created on startup if they do not yet exist.

This is a starting point for adding persistent storage and role-based features.

## Timezone

Opening hours are evaluated in the timezone specified by the
`BAR_TIMEZONE` environment variable (or `TZ` if set). Ensure this variable
matches your local timezone (e.g. `Europe/Rome`) so the "open now" status
reflects your local time.

## API

The application exposes minimal database-backed endpoints to illustrate
integration:

- `GET /api/bars` – list bars stored in the PostgreSQL database.
- `POST /api/bars` – create a new bar by providing `name` and `slug`.
- `POST /api/orders` – create an order and automatically compute VAT,
  the 5% platform fee and the payout due to the bar.
- `POST /api/payouts/run` – aggregate completed orders for a bar within a
  date range and create a payout entry. Each invocation is recorded in the
  `audit_logs` table for traceability.
  - `GET /admin/analytics` – analytics dashboard with multi-tab layout
    exposing KPIs for orders, revenue breakdowns, top products, client
    metrics, payouts and refunds.

## Environment Variables

The application reads its configuration from environment variables:

- `DATABASE_URL` – SQLAlchemy connection URL. Example:
  `postgresql://USER:PASSWORD@HOST:5432/DBNAME`. If omitted, it will be
  built automatically from the `POSTGRES_USER`, `POSTGRES_PASSWORD`,
  `POSTGRES_DB`, and optional `POSTGRES_HOST`/`POSTGRES_PORT` variables.
- `ADMIN_EMAIL` – email for the SuperAdmin account (defaults to
  `admin@example.com`).
- `ADMIN_PASSWORD` – password for the SuperAdmin account (defaults to
  `ChangeMe!123`).

When running via Docker Compose with the bundled Postgres service, also set:

- `POSTGRES_USER` – database user name.
- `POSTGRES_PASSWORD` – database user password.
- `POSTGRES_DB` – database name.
- `POSTGRES_HOST` – database host (defaults to `postgres`).
- `POSTGRES_PORT` – database port (defaults to `5432`).

If `DATABASE_URL` is not provided, the application combines the variables
above to form it. When deploying to an external provider, simply set
`DATABASE_URL` to the provider's connection string instead.

Optional variables:

- `FRONTEND_ORIGINS` – comma-separated list of allowed frontend URLs for CORS
  (defaults to `http://localhost:5173`).
- `WALLEE_SPACE_ID`, `WALLEE_USER_ID`, `WALLEE_API_SECRET` – credentials for
  Wallee transactions.
- `BASE_URL` – public base URL of the app used for payment callbacks.
- `CURRENCY` – currency code for payments (defaults to `CHF`).

### Disposable email controls

- `DISPOSABLE_EMAIL_ENFORCE` – set to `true` to block disposable email addresses.
- `DISPOSABLE_DOMAIN_URLS` – comma-separated HTTPS URLs pointing to disposable domain lists.
- `DISPOSABLE_CACHE_TTL_MIN` – cache TTL in minutes for the domain list (default `360`).
- `ENV` – environment name (`dev`, `staging`, or `prod`).

## Frontend redesign

The home page and shared layout were refreshed with a mobile‑first design.
Images now load from the `photo_url` field with lazy loading and an inline SVG
placeholder fallback. Spacing and grid breakpoints follow an
8px rhythm.

Design tokens such as colors, radii and typography live in
`static/css/tokens.css`.

## New Bar fields

Bars now support additional optional metadata:

- `rating` – float 0–5 displayed with a star icon.
- `is_open_now` – flag shown as an "OPEN NOW" badge.
These fields are editable in **Admin → BarEdit Info**. Image URLs must be
absolute HTTPS links.
