# Database Schema

## Epic 1 — Core Tables

```
Users
  id            UUID        PK
  email         VARCHAR     UNIQUE NOT NULL
  hashed_password VARCHAR   NOT NULL
  full_name     VARCHAR
  is_active     BOOLEAN     DEFAULT true
  created_at    TIMESTAMP   DEFAULT now()
  updated_at    TIMESTAMP   DEFAULT now()

Portfolios
  id            UUID        PK
  user_id       UUID        FK → Users.id
  name          VARCHAR     NOT NULL
  currency      VARCHAR(3)  DEFAULT 'INR'
  created_at    TIMESTAMP   DEFAULT now()

Holdings
  id            UUID        PK
  portfolio_id  UUID        FK → Portfolios.id
  symbol        VARCHAR     NOT NULL
  quantity      DECIMAL
  average_cost  DECIMAL
  asset_type    VARCHAR     (STOCK, ETF, MF, CRYPTO, BOND)

Transactions
  id            UUID        PK
  holding_id    UUID        FK → Holdings.id
  type          VARCHAR     (BUY, SELL)
  quantity      DECIMAL     NOT NULL
  price         DECIMAL     NOT NULL
  executed_at   TIMESTAMP   NOT NULL

Watchlist
  id            UUID        PK
  user_id       UUID        FK → Users.id
  symbol        VARCHAR     NOT NULL
  added_at      TIMESTAMP   DEFAULT now()
```

## ERD

```
Users ──< Portfolios ──< Holdings ──< Transactions
  │
  └──< Watchlist
```

## Future Tables (Later Epics)

| Table | Epic |
|-------|------|
| Goals | Epic 7 |
| Loans | Epic 6 |
| Insurance | Epic 6 |
| AIMemory | Epic 4 |
| Recommendations | Epic 5 |
| ResearchReports | Epic 3 |
