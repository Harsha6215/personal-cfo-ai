# Epic 6 — SaaS Platform Foundation

## Objective

Transform Personal CFO AI from a single-user desktop/localhost system into a secure, cloud-hosted, multi-tenant SaaS platform with proper user isolation, production-grade authentication, user onboarding, monitoring, and a beta launch plan.

---

## Business Objectives

- Enable multiple users to securely access the platform without data leakage
- Deploy the application to the cloud so it's accessible at `https://app.yourdomain.com`
- Create a compelling first-experience (onboarding + AI Portfolio Doctor)
- Establish production monitoring to detect and resolve issues proactively
- Validate the product with 10 beta users before broader release
- Build an admin portal for platform management

---

## Sprint Breakdown

### Sprint 6.1 — Multi-Tenant Architecture

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| 6.1.1 | Add `user_id` tenant scoping to all data-access queries | Every SELECT, INSERT, UPDATE, DELETE on user-owned tables includes `WHERE user_id = current_user.id`. No cross-user data leakage possible. |
| 6.1.2 | Create a `TenantMiddleware` or dependency that injects user context | All API endpoints that touch user data receive the authenticated user automatically via `Depends(get_current_user)`. |
| 6.1.3 | Add database-level Row-Level Security (RLS) policies | PostgreSQL RLS policies enforce `user_id = current_setting('app.current_user_id')` on all tenant-scoped tables as defense-in-depth. |
| 6.1.4 | Audit existing endpoints for tenant isolation | Review all 25+ API route modules; every endpoint that reads/writes user data must filter by `user_id`. Document any gaps and fix them. |
| 6.1.5 | Add integration tests for tenant isolation | Tests that create 2 users and verify User A cannot see/modify User B's portfolios, holdings, events, watchlist, decisions, or import jobs. |
| 6.1.6 | Rate limiting per user | Implement per-user rate limiting (100 req/min default) using Redis to prevent abuse. Return `429 Too Many Requests` when exceeded. |

### Sprint 6.2 — Cloud Deployment

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| 6.2.1 | Deploy React frontend to Vercel | Frontend accessible at custom domain, auto-deploys on push to `main`, environment variables configured for production API URL. |
| 6.2.2 | Deploy FastAPI backend to Railway | Backend running with health checks passing, connected to Neon PostgreSQL and Redis, auto-deploys on push. |
| 6.2.3 | Migrate database to Neon PostgreSQL | Production database on Neon with connection pooling enabled, Alembic migrations run successfully, data schema matches local. |
| 6.2.4 | Set up Redis on Railway or Upstash | Redis available for caching, rate limiting, and session management in production. |
| 6.2.5 | Configure three environments | Development (local), Staging (auto-deploy from `develop` branch), Production (deploy from `main` with approval). Separate `.env` configs for each. |
| 6.2.6 | Set up CI/CD pipeline for all environments | GitHub Actions: PR → lint + test + build, merge to `develop` → deploy staging, merge to `main` → deploy production (with manual approval gate). |
| 6.2.7 | Configure custom domain with SSL | `app.yourdomain.com` pointing to frontend, `api.yourdomain.com` pointing to backend. HTTPS enforced via platform-managed certificates. |
| 6.2.8 | Deploy AI services | AI services (port 8001) deployed alongside backend with access to same database and Redis. |

### Sprint 6.3 — Authentication Upgrade

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| 6.3.1 | Add Google OAuth login | Users can sign in with Google. On first login, a User record is created. JWT tokens issued same as email/password flow. |
| 6.3.2 | Add OTP-based passwordless login | Users can request OTP via email. OTP valid for 5 minutes, single-use. Successful verification issues JWT tokens. |
| 6.3.3 | Implement token blacklisting on logout | On logout, access token added to Redis blacklist. `get_current_user` checks blacklist before validating token. TTL matches token expiry. |
| 6.3.4 | Add role-based access control (RBAC) | User model gains `role` field (USER, ADMIN). Admin-only endpoints (Sprint 6.5) require `role == ADMIN`. Middleware enforces this. |
| 6.3.5 | Secure refresh token rotation | On each token refresh, old refresh token is invalidated and a new one issued. Prevents refresh token reuse attacks. |
| 6.3.6 | Add account deactivation and deletion | Users can deactivate (soft-delete) or permanently delete their account. Deletion cascades to all user data within 30 days. |

### Sprint 6.4 — User Onboarding

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| 6.4.1 | Build onboarding questionnaire UI | After first login, user sees a multi-step form collecting: risk appetite, investment horizon, monthly income, age, financial goals. Skippable but encouraged. |
| 6.4.2 | Create `UserProfile` model | New database table storing onboarding answers: `risk_appetite`, `investment_horizon`, `monthly_income`, `age`, `primary_goals` (JSON array), `experience_level`. Linked to User via FK. |
| 6.4.3 | Portfolio upload during onboarding | User can upload a broker CSV/PDF during onboarding. Reuse existing import system (Epic 2). Show import progress and summary. |
| 6.4.4 | AI Portfolio Doctor — first-impression analysis | After portfolio upload, automatically trigger the AI analysis pipeline. Present a "Portfolio Health Report" with: allocation breakdown, risk score, top concerns, quick wins. |
| 6.4.5 | Personalized dashboard based on profile | Dashboard adapts based on onboarding answers: conservative users see stability metrics first, aggressive users see opportunity alerts first. |
| 6.4.6 | Onboarding completion tracking | Track which onboarding steps are completed. Show progress indicator. Allow users to complete remaining steps later from Settings. |

### Sprint 6.5 — Monitoring & Admin Portal

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| 6.5.1 | Application health monitoring | Health endpoint returns detailed status: database connectivity, Redis connectivity, AI services status, response time p50/p95/p99. |
| 6.5.2 | Structured logging for production | All logs output as JSON in production. Include: request_id, user_id, endpoint, response_time, status_code. Ship to log aggregator (e.g., Axiom or Betterstack). |
| 6.5.3 | Error tracking integration | Integrate Sentry for uncaught exceptions. Capture user context, request details, and stack traces. Alert on error spike. |
| 6.5.4 | Admin dashboard — user management | Admin UI showing: total users, new signups (daily/weekly), active users. Ability to view user details, deactivate accounts, reset passwords. |
| 6.5.5 | Admin dashboard — system metrics | Dashboard showing: API response times, request volume, error rates, cache hit ratio, database query performance. |
| 6.5.6 | Admin dashboard — AI/LLM usage | Track and display: total LLM calls, cost per user, average latency, token usage, failed AI requests. |
| 6.5.7 | Admin dashboard — audit logs | Immutable audit log of admin actions: user deactivations, role changes, system config changes. |
| 6.5.8 | API usage analytics per user | Track API calls per user for usage-based billing readiness. Store in Redis with daily rollup to PostgreSQL. |

### Sprint 6.6 — Beta Launch

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| 6.6.1 | Invite-only registration | Registration gated by invite codes. Admin can generate invite codes with expiry and usage limits. Public registration disabled. |
| 6.6.2 | Beta feedback system | In-app feedback widget: thumbs up/down on AI recommendations, free-text feedback, bug reports. Stored in database, visible in admin portal. |
| 6.6.3 | Onboard 10 beta users | Send invites to 10 selected users. Provide onboarding support documentation. Track their journey through onboarding funnel. |
| 6.6.4 | Performance baseline | Establish baselines: API p95 latency < 500ms, AI analysis < 10s, onboarding completion > 70%, zero data leakage incidents. |
| 6.6.5 | Security checklist validation | Complete security review: OWASP Top 10 mitigations verified, dependency audit (no critical CVEs), secrets scanning in CI, HTTPS everywhere. |
| 6.6.6 | Data backup and recovery | Automated daily database backups (Neon built-in). Document and test recovery procedure. RTO < 1 hour, RPO < 24 hours. |

---

## Architecture Changes

### Current → Target

```
CURRENT (localhost, single-user):
  Frontend (localhost:3000) → Backend (localhost:8000) → PostgreSQL (localhost:5432)
                                                      → Redis (localhost:6379)
                              AI Services (localhost:8001) ↗

TARGET (cloud, multi-tenant):
  Frontend (Vercel) → Backend (Railway) → Neon PostgreSQL (connection pooling)
       ↓                    ↓            → Upstash Redis
  Custom Domain       AI Services (Railway)
       ↓                    ↓
  app.domain.com      api.domain.com
```

### Database Migration Strategy

1. Add `user_id` WHERE clauses to all queries (application-level isolation)
2. Enable PostgreSQL RLS as defense-in-depth (database-level isolation)
3. Add `UserProfile` table for onboarding data
4. Add `invite_codes` table for beta gating
5. Add `feedback` table for beta feedback
6. Add `audit_logs` table for admin actions
7. Add `api_usage` table for per-user tracking

### New Tables

```sql
user_profiles (id, user_id FK, risk_appetite, investment_horizon, monthly_income, age, primary_goals JSONB, experience_level, onboarding_completed_at)
invite_codes (id, code UNIQUE, created_by FK, max_uses, current_uses, expires_at, is_active)
feedback (id, user_id FK, type, content, page, metadata JSONB, created_at)
audit_logs (id, admin_user_id FK, action, target_type, target_id, details JSONB, created_at)
api_usage_daily (id, user_id FK, date, endpoint, request_count, avg_response_ms)
```

---

## Security Checklist

- [ ] Row-Level Security enabled on all tenant tables
- [ ] JWT secret rotated for production (min 256-bit)
- [ ] CORS restricted to production domains only
- [ ] Rate limiting active (100 req/min per user)
- [ ] SQL injection prevention (parameterized queries via SQLAlchemy)
- [ ] XSS prevention (React default escaping + CSP headers)
- [ ] CSRF protection (SameSite cookies or token-based)
- [ ] Secrets scanning in CI (GitHub secret scanning enabled)
- [ ] Dependency audit (no critical/high CVEs)
- [ ] HTTPS enforced everywhere
- [ ] Token blacklisting on logout
- [ ] Password policy enforced (min 8 chars, already done)
- [ ] Account lockout after 5 failed login attempts
- [ ] Sensitive data encrypted at rest (Neon default)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Deployment time (push to live) | < 5 minutes |
| API p95 latency | < 500ms |
| Uptime | > 99.5% |
| Onboarding completion rate | > 70% |
| First AI analysis latency | < 10 seconds |
| Zero cross-tenant data access | 0 incidents |
| Beta user retention (week 1) | > 80% |
| Beta feedback submissions | > 3 per user |

---

## Out of Scope (Deferred)

- Mobile application (Epic 11)
- Social features (feeds, likes, following — not planned for 12+ months)
- LLM router/multi-provider abstraction (revisit when second provider needed)
- Payment/billing integration (Epic 12)
- Multi-region deployment
- Enterprise SSO (SAML/OIDC)
