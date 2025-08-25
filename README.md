# SiplyGo Prototype

This project is a FastAPI prototype. This update adds initial database scaffolding
using SQLAlchemy and a Docker Compose setup with PostgreSQL.

## Running with Docker Compose

1. Copy `.env.example` to `.env` and set the values for `DATABASE_URL` and, if
   using the bundled Postgres service, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and
   `POSTGRES_DB`.
2. Start the containers:

```
docker compose up --build
```

Docker Compose automatically reads variables from `.env`. The app will then be
available at http://localhost:8000.

## Database

- Models are defined in `models.py`.
- Database engine and session helpers live in `database.py`.
- Tables are created on startup if they do not yet exist.

This is a starting point for adding persistent storage and role-based features.

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
- `GET /healthz` – returns `{"status": "ok"}` when the database connection is
  healthy.

## Environment Variables
Copy `.env.example` to `.env` for local development or define these variables in
your hosting provider's settings (for example, on Render). The application
requires a database connection string provided via environment variables.

- `DATABASE_URL` – SQLAlchemy connection URL. Example:
  `postgresql://USER:PASSWORD@HOST:5432/DBNAME`.

When running via Docker Compose, the bundled Postgres service also honours:

- `POSTGRES_USER` – database user name.
- `POSTGRES_PASSWORD` – database user password.
- `POSTGRES_DB` – database name.

These three variables must match the credentials used in `DATABASE_URL` when
connecting to the internal Postgres instance. When deploying to an external
provider, only `DATABASE_URL` needs to be set to the provider's connection
string; no `.env` file is required.

Optional variables:

- `FRONTEND_ORIGINS` – comma-separated list of allowed frontend URLs for CORS
  (defaults to `http://localhost:5173`).
- `GOOGLE_MAPS_API_KEY` – required if map widgets are used.
