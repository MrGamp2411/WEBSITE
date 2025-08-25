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

A sample bar is automatically created on startup if the database is empty so the
listing endpoint immediately returns data.
