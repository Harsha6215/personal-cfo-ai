# Epic 6 — SaaS Platform Foundation: Technical Design

## 1. Multi-Tenant Architecture (Sprint 6.1)

### Approach: Shared Database, Application-Level + RLS Isolation

All tenants share one PostgreSQL database. Isolation enforced at two levels:
1. **Application layer** — every query filtered by `user_id` from JWT
2. **Database layer** — PostgreSQL RLS as defense-in-depth

### Tenant Context Flow

```
Request → JWT decode → extract user_id → set session variable → execute query
                                              ↓
                              SET LOCAL app.current_user_id = 'uuid'
                                              ↓
                              RLS policy: user_id = current_setting('app.current_user_id')
```

### Implementation: Tenant-Scoped Session Dependency

```python
# backend/core/tenant.py
from backend.core.auth import get_current_user
from backend.core.database import get_db

async def get_tenant_db(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsyncSession:
    """Set PostgreSQL session variable for RLS before returning session."""
    await db.execute(text(f"SET LOCAL app.current_user_id = '{user.id}'"))
    return db
```

### RLS Policy Template (per table)

```sql
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON portfolios
    USING (user_id = current_setting('app.current_user_id')::text);
```

Tables requiring RLS:
- `portfolios` (user_id)
- `holdings` (via portfolio_id → user_id, or add direct user_id)
- `financial_events` (via portfolio_id → user_id)
- `import_jobs` (user_id)
- `watchlist` (user_id)
- `decision_history` (user_id)
- `user_profiles` (user_id)
- `feedback` (user_id)

### Rate Limiting Design

```python
# backend/middleware/rate_limit.py
# Sliding window using Redis ZSET per user
# Key: rate_limit:{user_id}
# Score: timestamp
# Limit: 100 requests per 60 seconds
```

---

## 2. Cloud Deployment Architecture (Sprint 6.2)

### Target Infrastructure

```
┌─────────────────────────────────────────────────────────────┐
│                        PRODUCTION                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐     ┌───────────────┐     ┌──────────────┐  │
│  │  Vercel  │────▶│  Railway      │────▶│ Neon         │  │
│  │ Frontend │     │  Backend :8000│     │ PostgreSQL   │  │
│  │          │     │  AI Svc :8001 │     │ (pooled)     │  │
│  └──────────┘     └───────────────┘     └──────────────┘  │
│       │                   │                                 │
│       │                   ▼                                 │
│       │           ┌───────────────┐                         │
│       │           │ Upstash Redis │                         │
│       │           │ (serverless)  │                         │
│       │           └───────────────┘                         │
│       │                                                     │
│       ▼                                                     │
│  app.domain.com          api.domain.com                     │
└─────────────────────────────────────────────────────────────┘
```

### Environment Configuration

| Environment | Frontend | Backend | Database | Branch |
|-------------|----------|---------|----------|--------|
| Development | localhost:3000 | localhost:8000 | Local PostgreSQL | any |
| Staging | staging.vercel.app | staging.railway.app | Neon (staging branch) | `develop` |
| Production | app.domain.com | api.domain.com | Neon (main) | `main` |

### CI/CD Pipeline (GitHub Actions)

```yaml
# Trigger matrix:
# PR opened → lint + typecheck + test + build (no deploy)
# Push to develop → deploy to staging
# Push to main → deploy to production (manual approval)
```

### Environment Variables (Production)

```
# Backend (Railway)
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://...@neon.tech/personal_cfo?sslmode=require
REDIS_URL=redis://...@upstash.io:6379
SECRET_KEY=<256-bit random>
CORS_ORIGINS=["https://app.yourdomain.com"]
SENTRY_DSN=<sentry-project-dsn>
LOG_JSON=true
LOG_LEVEL=INFO

# Frontend (Vercel)
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_APP_ENV=production
VITE_SENTRY_DSN=<frontend-sentry-dsn>
```

---

## 3. Authentication Upgrade (Sprint 6.3)

### Google OAuth Flow

```
Frontend                    Backend                     Google
   │                           │                          │
   │── Click "Sign in with Google" ──▶                    │
   │                           │                          │
   │   ◀── Redirect to Google consent ─────────────────▶  │
   │                           │                          │
   │── Callback with auth code ▶                          │
   │                           │── Exchange code for tokens ▶
   │                           │◀── Google user info ──────│
   │                           │                          │
   │                           │── Find/create User ──▶ DB│
   │                           │── Issue JWT ──▶          │
   │◀── Return access + refresh tokens                    │
```

### Token Blacklisting (Redis)

```
Key: blacklist:{token_jti}
Value: 1
TTL: remaining token lifetime
Check: on every request in get_current_user
```

### RBAC Model

```python
class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

# User model addition:
role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)

# Dependency:
def require_admin(user: User = Depends(get_current_user)):
    if user.role != UserRole.ADMIN:
        raise HTTPException(403, "Admin access required")
    return user
```

---

## 4. User Onboarding (Sprint 6.4)

### Onboarding Flow

```
Sign Up → Email Verification → Onboarding Questionnaire → Portfolio Upload (optional)
                                        ↓
                              AI Portfolio Doctor Analysis
                                        ↓
                              Personalized Dashboard
```

### UserProfile Schema

```python
class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True)

    risk_appetite: Mapped[str]      # CONSERVATIVE, MODERATE, AGGRESSIVE
    investment_horizon: Mapped[str]  # SHORT (< 2y), MEDIUM (2-7y), LONG (7y+)
    monthly_income: Mapped[int | None]  # in INR, optional
    age: Mapped[int | None]
    primary_goals: Mapped[str]       # JSON array: ["RETIREMENT", "WEALTH", "INCOME", "EDUCATION"]
    experience_level: Mapped[str]    # BEGINNER, INTERMEDIATE, ADVANCED

    onboarding_step: Mapped[int] = mapped_column(default=0)  # tracks progress
    onboarding_completed_at: Mapped[datetime | None]
```

### AI Portfolio Doctor — First Analysis

Reuse existing AI pipeline (Epic 4 agents):
1. Trigger `portfolio_analyst` agent on portfolio upload
2. Generate health report: allocation, risk, concerns, opportunities
3. Store result and display as "Portfolio Health Card" on dashboard

---

## 5. Monitoring & Admin Portal (Sprint 6.5)

### Monitoring Stack

```
Application → Structured Logs (JSON) → Axiom/Betterstack
           → Error Tracking → Sentry
           → Metrics → Custom /admin/metrics endpoint + Redis counters
```

### Admin Portal Architecture

Separate set of routes under `/api/v1/admin/` protected by `require_admin` dependency.

**Admin API Endpoints:**

```
GET  /api/v1/admin/users          — list all users with stats
GET  /api/v1/admin/users/:id      — user detail + activity
POST /api/v1/admin/users/:id/deactivate
POST /api/v1/admin/users/:id/activate
GET  /api/v1/admin/metrics        — system metrics (cached 30s)
GET  /api/v1/admin/llm-usage      — LLM cost + usage stats
GET  /api/v1/admin/audit-logs     — paginated audit trail
POST /api/v1/admin/invite-codes   — generate invite codes
GET  /api/v1/admin/feedback       — user feedback list
```

**Frontend Admin Pages:**

```
/admin/dashboard    — overview metrics
/admin/users        — user management table
/admin/ai-usage     — LLM cost tracking
/admin/feedback     — user feedback review
/admin/audit        — audit log viewer
/admin/invites      — invite code management
```

### Metrics Collection (Redis)

```
# Per-request counters (Redis INCR with daily key rotation)
api:requests:{date}:{endpoint}   → count
api:errors:{date}:{endpoint}     → count
api:latency:{date}:{endpoint}    → list of ms values (sampled)

# LLM tracking
llm:calls:{date}:{user_id}      → count
llm:tokens:{date}:{user_id}     → total tokens
llm:cost:{date}                  → total cost (cents)
```

---

## 6. Beta Launch (Sprint 6.6)

### Invite Code System

```python
class InviteCode(TimestampMixin, Base):
    __tablename__ = "invite_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    max_uses: Mapped[int] = mapped_column(default=1)
    current_uses: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime | None]
    is_active: Mapped[bool] = mapped_column(default=True)
```

Registration flow change:
```
POST /api/v1/auth/register
Body: { email, password, full_name, invite_code }

→ Validate invite_code exists, is_active, not expired, current_uses < max_uses
→ Create user
→ Increment current_uses
```

### Feedback Widget

```python
class Feedback(TimestampMixin, Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    feedback_type: Mapped[str]  # BUG, FEATURE, AI_RATING, GENERAL
    content: Mapped[str]        # free text
    rating: Mapped[int | None]  # 1-5 for AI ratings
    page: Mapped[str | None]    # which page they were on
    metadata: Mapped[str | None]  # JSON blob for context
```

---

## Technology Choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Frontend hosting | Vercel | Free tier, automatic PR previews, excellent DX for React/Vite |
| Backend hosting | Railway | Simple Docker deploy, auto-scaling, built-in metrics, $5/mo hobby |
| Database | Neon PostgreSQL | Serverless, branching for staging, generous free tier, connection pooling |
| Cache/Queue | Upstash Redis | Serverless, pay-per-request, no idle cost |
| Error tracking | Sentry | Industry standard, good FastAPI + React integrations |
| Logging | Axiom or Betterstack | Structured log ingestion, free tier sufficient for beta |
| OAuth | Google (via `authlib`) | Largest user base, simple OIDC flow |
| CI/CD | GitHub Actions | Already configured, free for public repos |

---

## Migration Strategy

### Phase 1: Non-Breaking Changes (can deploy to existing local setup)
- Add `role` column to users table
- Add `user_profiles` table
- Add `invite_codes` table
- Add `feedback` table
- Add `audit_logs` table
- Add `api_usage_daily` table

### Phase 2: Behavior Changes (requires testing)
- Enable RLS on all tenant tables
- Add rate limiting middleware
- Add invite code requirement to registration
- Token blacklisting on logout

### Phase 3: Infrastructure (new deployment)
- Deploy to Vercel + Railway + Neon
- Configure custom domains
- Enable Sentry + structured logging
- Set up staging environment

---

## File Structure (New/Modified)

```
backend/
├── core/
│   ├── tenant.py          (NEW — tenant scoping dependency)
│   ├── rate_limit.py      (NEW — Redis-based rate limiter)
│   └── auth.py            (MODIFIED — add blacklist check, RBAC)
├── middleware/
│   └── rate_limit.py      (NEW — rate limit middleware)
├── models/
│   ├── user.py            (MODIFIED — add role field)
│   ├── user_profile.py    (NEW)
│   ├── invite_code.py     (NEW)
│   ├── feedback.py        (NEW)
│   └── audit_log.py       (NEW)
├── api/v1/
│   ├── auth.py            (MODIFIED — invite codes, OAuth)
│   ├── onboarding.py      (NEW)
│   ├── feedback.py        (NEW)
│   └── admin/
│       ├── __init__.py    (NEW)
│       ├── users.py       (NEW)
│       ├── metrics.py     (NEW)
│       ├── invites.py     (NEW)
│       ├── feedback.py    (NEW)
│       └── audit.py       (NEW)
├── services/
│   ├── oauth.py           (NEW — Google OAuth logic)
│   └── metrics.py         (NEW — Redis metrics collection)

frontend/src/
├── pages/
│   ├── Onboarding.tsx     (NEW)
│   ├── admin/
│   │   ├── AdminDashboard.tsx  (NEW)
│   │   ├── AdminUsers.tsx      (NEW)
│   │   ├── AdminAIUsage.tsx    (NEW)
│   │   ├── AdminFeedback.tsx   (NEW)
│   │   └── AdminInvites.tsx    (NEW)
├── components/
│   ├── onboarding/
│   │   ├── RiskStep.tsx        (NEW)
│   │   ├── GoalsStep.tsx       (NEW)
│   │   ├── UploadStep.tsx      (NEW)
│   │   └── DoctorResult.tsx    (NEW)
│   └── feedback/
│       └── FeedbackWidget.tsx  (NEW)

database/migrations/versions/
├── xxxx_add_user_role.py           (NEW)
├── xxxx_add_user_profiles.py       (NEW)
├── xxxx_add_invite_codes.py        (NEW)
├── xxxx_add_feedback.py            (NEW)
├── xxxx_add_audit_logs.py          (NEW)
├── xxxx_add_api_usage.py           (NEW)
├── xxxx_enable_rls.py              (NEW)

.github/workflows/
├── ci.yml                 (MODIFIED — add staging deploy)
├── deploy-staging.yml     (NEW)
├── deploy-production.yml  (NEW)

docker/
├── docker-compose.staging.yml  (NEW)
```
