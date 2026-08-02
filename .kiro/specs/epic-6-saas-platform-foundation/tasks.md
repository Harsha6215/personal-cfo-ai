# Epic 6 — SaaS Platform Foundation: Implementation Tasks

## Sprint 6.1 — Multi-Tenant Architecture

- [x] 1. Add `role` field to User model (`USER`, `ADMIN` enum) and create Alembic migration
- [x] 2. Create `backend/core/tenant.py` with `get_tenant_db` dependency that sets PostgreSQL session variable `app.current_user_id`
- [x] 3. Audit all API route modules (portfolios, assets, imports, watchlist, decisions, AI, etc.) — add `user_id` filtering to every query that touches user-owned data
- [x] 4. Create Alembic migration to enable Row-Level Security (RLS) on all tenant-scoped tables: `portfolios`, `holdings`, `financial_events`, `import_jobs`, `watchlist`, `decision_history`
- [x] 5. Create `backend/core/rate_limit.py` — sliding window rate limiter using Redis ZSET (100 req/min per user)
- [x] 6. Create `backend/middleware/rate_limit.py` — FastAPI middleware that applies rate limiting to all authenticated endpoints
- [x] 7. Write integration tests: create 2 users, verify User A cannot access User B's portfolios, holdings, events, watchlist, decisions, import jobs
- [x] 8. Write integration test: verify rate limiter returns 429 after exceeding limit

## Sprint 6.2 — Cloud Deployment

- [ ] 9. Create `vercel.json` configuration for frontend deployment (build command, output dir, rewrites for SPA routing)
- [ ] 10. Create `railway.toml` or `Procfile` for backend deployment on Railway
- [ ] 11. Create `.github/workflows/deploy-staging.yml` — auto-deploy to staging on push to `develop` branch
- [ ] 12. Create `.github/workflows/deploy-production.yml` — deploy to production on push to `main` with manual approval gate
- [ ] 13. Update `backend/core/config.py` — add environment-specific settings for Neon (SSL mode, connection pooling), Sentry DSN, log shipping
- [ ] 14. Create `docker/docker-compose.staging.yml` for staging environment (optional local staging test)
- [ ] 15. Update frontend `vite.config.ts` and add environment-specific API base URL handling
- [ ] 16. Document deployment runbook: how to set up Vercel, Railway, Neon, Upstash from scratch (in `docs/deployment.md`)

## Sprint 6.3 — Authentication Upgrade

- [x] 17. Add `authlib` to backend requirements and create `backend/services/oauth.py` for Google OAuth token exchange
- [x] 18. Create `POST /api/v1/auth/google` endpoint — accepts Google auth code, exchanges for user info, finds/creates User, returns JWT tokens
- [x] 19. Add Google sign-in button to frontend Login page using Google Identity Services library
- [x] 20. Implement token blacklisting: on logout, add token JTI to Redis with TTL; update `get_current_user` to check blacklist
- [x] 21. Add JTI (JWT ID) claim to token creation in `security.py`; check JTI in `get_current_user`
- [x] 22. Implement refresh token rotation: on each `/auth/refresh` call, invalidate old refresh token in Redis and issue new pair
- [x] 23. Create `require_admin` dependency in `backend/core/auth.py` that checks `user.role == ADMIN`
- [x] 24. Add OTP-based login: `POST /api/v1/auth/request-otp` (sends email), `POST /api/v1/auth/verify-otp` (validates and returns tokens)
- [x] 25. Add account deletion endpoint: `DELETE /api/v1/auth/account` — soft-delete immediately, schedule hard delete after 30 days
- [x] 26. Update frontend auth service and Login page to support Google OAuth and OTP flows

## Sprint 6.4 — User Onboarding

- [x] 27. Create `backend/models/user_profile.py` — UserProfile model with risk_appetite, investment_horizon, monthly_income, age, primary_goals, experience_level, onboarding_step, onboarding_completed_at
- [x] 28. Create Alembic migration for `user_profiles` table
- [x] 29. Create `backend/api/v1/onboarding.py` — CRUD endpoints for user profile (GET, PUT) and onboarding progress tracking
- [x] 30. Build frontend `Onboarding.tsx` — multi-step wizard with animated transitions: Welcome → Risk → Goals → Income/Age → Upload → Portfolio Doctor
- [x] 31. Build onboarding step components: `RiskStep.tsx`, `GoalsStep.tsx`, `ProfileStep.tsx`, `UploadStep.tsx`
- [x] 32. Build `DoctorResult.tsx` — AI Portfolio Doctor results page showing allocation pie chart, risk score gauge, concerns list, quick-win recommendations
- [x] 33. Integrate onboarding with existing import system — reuse `POST /api/v1/import/upload` during onboarding upload step
- [x] 34. Add onboarding redirect logic: if user has no completed profile, redirect to `/onboarding` after login
- [x] 35. Update Dashboard to personalize content based on user profile (risk appetite → card ordering, alerts priority)

## Sprint 6.5 — Monitoring & Admin Portal

- [ ] 36. Create `backend/services/metrics.py` — Redis-based metrics collector: request counts, latencies, error counts, LLM usage per user/day
- [ ] 37. Add metrics collection middleware: increment Redis counters on every request (endpoint, status, latency)
- [ ] 38. Integrate Sentry: add `sentry-sdk[fastapi]` to requirements, initialize in `main.py` for production, capture user context on each request
- [ ] 39. Update structured logging: ensure all production logs are JSON with request_id, user_id, endpoint, response_time_ms, status_code
- [ ] 40. Create `backend/models/audit_log.py` — AuditLog model (admin_user_id, action, target_type, target_id, details JSONB)
- [ ] 41. Create Alembic migration for `audit_logs` table
- [ ] 42. Create `backend/api/v1/admin/` package with router: users, metrics, invites, feedback, audit endpoints (all protected by `require_admin`)
- [ ] 43. Create admin user management endpoints: list users, get user detail, deactivate, activate, view user's API usage
- [ ] 44. Create admin metrics endpoint: aggregate Redis counters into response (total requests, errors, p50/p95 latency, active users)
- [ ] 45. Create admin LLM usage endpoint: total calls, cost breakdown by user, token usage, failed requests
- [ ] 46. Build frontend admin pages: `AdminDashboard.tsx` (metrics overview), `AdminUsers.tsx` (user table), `AdminAIUsage.tsx`, `AdminFeedback.tsx`
- [ ] 47. Add admin route protection on frontend: check user.role === 'ADMIN' before rendering admin pages, add `/admin` routes to App.tsx

## Sprint 6.6 — Beta Launch

- [ ] 48. Create `backend/models/invite_code.py` — InviteCode model (code, created_by, max_uses, current_uses, expires_at, is_active)
- [ ] 49. Create Alembic migration for `invite_codes` table
- [ ] 50. Modify `POST /api/v1/auth/register` to require and validate `invite_code` field; increment usage on successful registration
- [ ] 51. Create admin invite code endpoints: generate codes (batch), list codes, deactivate code
- [ ] 52. Create `backend/models/feedback.py` — Feedback model (user_id, feedback_type, content, rating, page, metadata)
- [ ] 53. Create Alembic migration for `feedback` table
- [ ] 54. Create `POST /api/v1/feedback` endpoint — authenticated users can submit feedback
- [ ] 55. Build frontend `FeedbackWidget.tsx` — floating button, popup with type selector (bug/feature/AI rating), text input, optional rating stars
- [ ] 56. Add FeedbackWidget to AppShell so it's available on every authenticated page
- [ ] 57. Run full security audit: verify OWASP Top 10 mitigations, run `pip-audit` and `npm audit`, fix any critical/high vulnerabilities
- [ ] 58. Create `docs/beta-launch-checklist.md` — document launch steps, user communication template, support process, rollback plan
- [ ] 59. Set up automated daily database backup verification (Neon built-in, document recovery steps)
- [ ] 60. Create seed script to generate initial admin user and 10 invite codes for beta launch
