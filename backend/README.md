# backend/

FastAPI REST API — the core business logic layer.

## Responsibility
All business logic, authentication, data access, and REST API endpoints live here. The frontend calls this layer. This layer calls the database and AI services.

## Stack
- **FastAPI** – async Python web framework
- **SQLAlchemy** – ORM
- **Alembic** – database migrations
- **Pydantic** – data validation and settings
- **bcrypt** – password hashing
- **python-jose** – JWT tokens

## Structure

```
backend/
├── api/
│   └── v1/          ← versioned route handlers
├── models/          ← SQLAlchemy ORM models
├── schemas/         ← Pydantic request/response schemas
├── repositories/    ← data access layer (DB queries)
├── services/        ← business logic layer
├── core/
│   ├── config.py    ← environment-based configuration
│   └── logging.py   ← structured JSON logging
├── middleware/      ← CORS, request ID, timing
├── config/          ← environment configs
└── tests/           ← pytest test suite
```

## Getting Started

```bash
# From repo root
docker compose up backend
```

API runs at: http://localhost:8000
Swagger UI: http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
