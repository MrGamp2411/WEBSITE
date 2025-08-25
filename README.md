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
