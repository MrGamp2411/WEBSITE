# SiplyGo Prototype

This project is a FastAPI prototype. This update adds initial database scaffolding
using SQLAlchemy and a Docker Compose setup with PostgreSQL.

## Running with Docker Compose

```
docker compose up --build
```

The app will be available at http://localhost:8000 and connects to a PostgreSQL
instance automatically.

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

A sample bar is automatically created on startup if the database is empty so the
listing endpoint immediately returns data.

## Environment Variables

- `API_BASE_URL` – base URL for API requests (defaults to `http://localhost:8000`).
- `ADMIN_EMAIL` – email for the SuperAdmin account.
- `ADMIN_PASSWORD` – password for the SuperAdmin account.

On startup the application ensures a SuperAdmin user exists using these
credentials. If the user is missing, it is created with the provided values. For
local development the defaults `admin@example.com` / `ChangeMe!123` are used.
