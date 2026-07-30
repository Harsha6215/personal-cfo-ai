# scripts/

Developer utility scripts and automation helpers.

## Scripts

| Script | Purpose |
|--------|---------|
| `setup.sh` | First-time local environment setup |
| `seed.py` | Seed the database with test data |
| `migrate.sh` | Run Alembic database migrations |
| `lint.sh` | Run all linters (ruff, mypy, eslint, prettier) |
| `test.sh` | Run all test suites |

## Usage

```bash
# Seed the database with test user and sample portfolio
python scripts/seed.py

# Run all linters
bash scripts/lint.sh

# Run all tests
bash scripts/test.sh
```
