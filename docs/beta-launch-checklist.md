# Beta Launch Checklist

Pre-launch verification for Personal CFO AI beta release.

---

## 🔒 Security

- [ ] Run `pip-audit` — no critical vulnerabilities in Python deps
- [ ] Run `npm audit` in frontend/ — no high/critical issues
- [ ] Verify all environment variables are set in production (no defaults leaking)
- [ ] CORS origins restricted to production domain only
- [ ] JWT secret is strong (32+ chars, randomly generated)
- [ ] OAuth client secrets not committed to git
- [ ] Rate limiting enabled on auth endpoints
- [ ] Admin endpoints require `require_admin` dependency

## 🗄️ Database

- [ ] Neon database backup verified (point-in-time recovery enabled)
- [ ] All migrations applied cleanly (`alembic upgrade head`)
- [ ] invite_codes table created with proper indexes
- [ ] feedback table created with proper indexes
- [ ] No pending migration conflicts
- [ ] Connection pooling configured (asyncpg pool size appropriate for beta load)

## 🚀 Deployment

- [ ] Environment-specific configs verified (staging vs production)
- [ ] Health check endpoint responds: `GET /api/v1/health`
- [ ] Frontend build succeeds: `npm run build` exits 0
- [ ] Backend starts cleanly: no import errors on boot
- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] Monitoring/alerting configured (error rate, latency spikes)
- [ ] Log aggregation working (structured logs flowing)

## 👥 Users

- [ ] Admin account verified: harsha.coolguy@gmail.com has ADMIN role
- [ ] Beta invite codes generated (run `python -m database.seeds.beta_seed`)
- [ ] Invite codes distributed to beta testers
- [ ] Registration flow tested with invite code
- [ ] Registration flow tested without invite code (still allowed for now)
- [ ] Feedback widget visible and functional

## ↩️ Rollback Plan

If critical issues are discovered post-launch:

1. **Immediate**: Disable new registrations by deactivating all invite codes via admin API
2. **Frontend**: Revert to previous deploy (Vercel/Netlify instant rollback)
3. **Backend**: Redeploy previous Docker image tag
4. **Database**: If schema changes caused issues:
   - Run `alembic downgrade 0006` to revert invite_codes + feedback tables
   - This is safe — no other tables depend on these
5. **Communication**: Notify beta users via email if service is interrupted

---

## Post-Launch Monitoring (First 48 Hours)

- [ ] Watch error rates in monitoring dashboard
- [ ] Review feedback submissions in admin panel
- [ ] Check invite code redemption counts
- [ ] Verify AI endpoints responding within acceptable latency
- [ ] Confirm no unusual auth patterns (brute force attempts)
