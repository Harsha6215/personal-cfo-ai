# database/

Database schema, migrations, seeds, and documentation.

## Structure

```
database/
├── migrations/      ← Alembic migration files
│   └── versions/
├── seeds/           ← seed data scripts
└── schema.md        ← ERD and table documentation
```

## Core Schema (Epic 1)

```
Users
  ↓
Portfolios
  ↓
Holdings
  ↓
Transactions

Watchlist (linked to Users)
```

## Running Migrations

```bash
# From repo root — migrations run automatically on startup
docker compose up

# Or manually
cd backend
alembic upgrade head
```

## Seeding

```bash
python scripts/seed.py
```

Creates:
- 1 test user (test@personal-cfo.ai / password: Test@1234)
- 1 sample portfolio
- 3 sample holdings
