# Invention Index 8 — Technical Audit

**Date:** 2026-06-14
**Author:** Hermes Agent
**Branch:** `feat/phase4-pr3-billing-ux-polish` (last commit: `48354e3`)
**Last deploy tag:** `fix(security): harden Postgres + Resend webhook exempt + full audit report`

---

## 1. Build Status

| Check | Tool | Result | Details |
|-------|------|--------|---------|
| Frontend build | `next build` | ✅ PASS | Compiled in 6.5s, all routes built |
| Frontend lint | `next lint` (ESLint) | ⚠️ PASS (warnings) | 1 error: `prefer-const` in blog page. 10+ warnings (unused vars, `<img>` vs `<Image>`) |
| Frontend typecheck | `tsc --noEmit` | ❌ FAIL (1 error) | `webhooks/page.tsx:225` — `Type '{}' is not assignable to type 'ReactNode'` |
| Frontend tests | `jest` | ❌ 1 FAIL / 53 tests | `formatDate` timezone-dependent test: expects "Mar 15" got "Mar 14". 7 suites pass. |
| Backend lint | `ruff check` | ⚠️ UNRUNNABLE | Local venv is Python 3.9.19, project requires 3.12. Ruff not installed. |
| Backend typecheck | `mypy` | ⚠️ UNRUNNABLE | Same venv issue. Docker-based dev only. |
| Backend tests | `pytest` | ⚠️ UNRUNNABLE | Same venv issue. CI pipeline runs tests on Postgres 16 + Redis 7. |
| Docker build | `docker compose build` | ⚠️ NOT TESTED | Docker not running locally; CI handles this. |
| Git status | `git status` | ⚠️ DIRTY | 8 untracked files in `.hermes/` + new `docs/` dir. On feature branch. |

### Build Summary

| Area | Finding | Severity | Evidence | Recommended Fix | PR |
|------|---------|----------|----------|-----------------|----|
| Frontend build | Compiles cleanly | ✅ Low | Build output | None needed | — |
| Frontend typecheck | 1 TS error in webhooks page | High | `tsc --noEmit` | Fix type assignment in webhooks/page.tsx:225 | PR-1 |
| Frontend lint | `prefer-const` error in blog | Medium | ESLint output | Change `let html` to `const html` in `blog/[slug]/page.tsx:238` | PR-1 |
| Frontend lint | 10+ unused-var warnings | Low | ESLint output | Prefix unused params with `_` or remove | PR-2 |
| Frontend lint | `<img>` instead of `<Image>` | Low | ESLint output | Replace with `next/image` in PatentFiguresPanel | PR-2 |
| Frontend tests | 1 timezone-dependent test | Medium | Jest output | Use `TZ=UTC` or mock date formatting | PR-3 |
| Backend venv | Python 3.9, needs 3.12 | Medium | `python --version` | Recreate venv with python3.12 | PR-4 |

---

## 2. Dependency Audit

### Frontend Dependencies (npm)

| Package | Current | Latest | Gap | Risk |
|---------|---------|--------|-----|------|
| next | 15.5.15 | 16.2.9 | 1 major | Medium — Next 16 has breaking changes |
| react / react-dom | 19.2.5 | 19.2.7 | Patch | Low — safe to update |
| @sentry/nextjs | 8.55.2 | 10.57.0 | 2 majors | Medium — V8→V10 migration needed |
| tailwindcss | 3.4.19 | 4.3.1 | 1 major | Medium — Tailwind 4 has config changes |
| eslint | 9.39.4 | 10.5.0 | 1 major | Low — dev only |
| typescript | 5.9.3 | 6.0.3 | 1 major | Low — dev only, but TS6 may surface new errors |
| @types/jest | 29.5.14 | 30.0.0 | 1 major | Low — dev only |
| jest | 29.7.0 | 30.4.2 | 1 major | Low — dev only |
| date-fns | 4.1.0 | 4.4.0 | Minor | Low |
| geist | 1.7.1 | 1.7.2 | Patch | Low |

### Security Vulnerabilities (npm audit)

| Vulnerability | Severity | Package | Fix |
|--------------|----------|---------|-----|
| ws: Uninitialized memory disclosure | Moderate | ws 8.x | `npm audit fix` (non-breaking) |
| uuid: Various CVEs | High | uuid (via @sentry/webpack-plugin) | Requires @sentry update → breaking change |
| Total: 8 vulnerabilities | 5 moderate, 3 high | | |

### Backend Dependencies (Poetry/pyproject.toml)

| Package | Version | Notes |
|---------|---------|-------|
| fastapi | ^0.115 | Stable |
| sqlalchemy | ^2.0 (async) | Stable |
| celery | ^5.4 (redis) | Stable |
| anthropic | ^0.40 | Stable |
| stripe | ^11.0 | Stable |
| pgvector | ^0.3 | Stable |
| google-cloud-bigquery | ^3.25 | Large dep, only used for WIPO ingestion |
| sentry-sdk | ^2.0 | May need update to match frontend Sentry version |
| slowapi | ^0.1.9 | Rate limiting |
| structlog | ^24.4 | Structured logging |

### Dependency Risks

| Risk | Severity |
|------|----------|
| Next.js 16 has breaking changes — stay on 15.x until after revamp | Medium |
| Sentry major version gap across frontend/backend | Low |
| Tailwind 4 migration non-trivial — pin to 3.x for revamp | Medium |
| `google-cloud-bigquery` is a large dependency for a single ingestion path | Low |
| No lockfile for backend in local (Poetry broken, Docker-only) | Medium |

---

## 3. Security Audit

Based on the 2026-06-12 security vulnerability audit (`.hermes/reports/2026-06-12_security-vulnerability-audit.md`):

### Fixed

| Vuln | Description | Severity | Fix |
|------|-------------|----------|-----|
| VULN-01 | Redis publicly exposed (0.0.0.0:6379, no password) | P0 | Changed to 127.0.0.1 + requirepass |
| VULN-02 | PostgreSQL publicly exposed (0.0.0.0:5432) | P0 | Changed to 127.0.0.1 |
| VULN-04 | Resend webhook rate-limited | P2 | Added `@limiter.exempt` |

### Still Requires Andy Action

| Vuln | Description | Severity | Action |
|------|-------------|----------|--------|
| VULN-03 | Postgres default password is `secret` | P1 | Set strong POSTGRES_PASSWORD in .env on server |
| PRE-01 | Admin trigger endpoints lack `require_admin` | P1 | Add auth guard to 8 endpoints |
| VULN-05 | Blog HTML rendered via `dangerouslySetInnerHTML` | P3 | Add DOMPurify sanitizer |
| VULN-06 | Webhook config test endpoint allows SSRF | P3 | Validate webhook URLs reject private IPs |
| PRE-02 | Backend/frontend ports bind to 0.0.0.0 | P3 | Move to Docker-internal-only when Caddy proxies |

### OWASP Top 10 Assessment

| Category | Status | Notes |
|----------|--------|-------|
| A01: Broken Access Control | ✅ Good | `require_admin` on admin endpoints, `current_user` on auth endpoints |
| A02: Cryptographic Failures | ✅ Good | JWT auth, HMAC webhook signatures, TLS via Caddy |
| A03: Injection | ✅ Good | All queries use parameterized SQLAlchemy |
| A04: Insecure Design | ⚠️ Minor | Rate limiting exists but is basic (60/min global) |
| A05: Security Misconfiguration | ⚠️ Minor | Default passwords, port binding issues (mostly fixed) |
| A06: Vulnerable Components | ⚠️ Minor | npm audit shows 8 vulns; Sentry/Next.js major versions behind |
| A07: Auth Failures | ✅ Good | Magic-link auth with JWT cookies, proper expiry |
| A08: Software/Data Integrity | ✅ Good | CI/CD with auto-rollback, Docker image pinning |
| A09: Logging/Monitoring Failures | ⚠️ Minor | Structlog + Sentry wired, but missing: chat cost tracking, Celery beat health, email webhook silence detection |
| A10: SSRF | ⚠️ Minor | VULN-06: webhook test endpoint can POST to internal IPs |

---

## 4. Code Quality

### Frontend

| Metric | Value |
|--------|-------|
| Test files | 8 test files (`__tests__/`, `*.test.tsx`) |
| Tests | 53 tests, 1 failure |
| Components with no tests | 80%+ (only Card, SourceAttribution, Badge, StatTile, BriefingItem, UsageWarningBanner, PatentCard tested) |
| TypeScript strictness | Moderate — TypeScript catches type errors in CI build |
| Dead code | ~10 unused imports/variables (ESLint warnings) |
| `<img>` vs `<Image>` | 1 instance in `PatentFiguresPanel` |

### Backend

| Metric | Value |
|--------|-------|
| Test files | 80+ test files across 10+ directories |
| Test coverage | Unknown (pytest-cov configured but not runnable locally) |
| API tests | Every endpoint module has test coverage (`test_*.py`) |
| Integration tests | `tests/integration/test_sprint7_flows.py` exists |
| Dead code | `_check_chat_quota_stub` in chat.py (noted in V3 audit) |
| Code style | Ruff configured (E, F, I, W rules, 100-char lines) |

---

## 5. Performance Baseline

### Known Issues (from existing audits)

| Issue | Screen | Impact |
|-------|--------|--------|
| Companies page shows "0 of 0" coverage | `/companies` | High — looks broken, trust issue |
| Figure thumbnails only ~5K/64K populated | Patent detail | Medium — visual appeal degraded |
| Blog posts use placeholder patent IDs | `/blog` | High — broken links if published |
| Embedding coverage ~65% at last check | Semantic search | Medium — some patents not searchable |
| Chat memory TTL 30 min, no continuation prompt | Chat | Low — UX polish |
| Persona only affects briefing, not search | Search | Low — consistency gap |
| Onboarding skip leaves persona null | Onboarding | Medium — unpersonalized experience |

### Frontend Performance (from build)

| Metric | Value |
|--------|-------|
| Build time | 6.5s (compiled successfully) |
| Next.js version | 15.5.15 (App Router) |
| CSS framework | Tailwind 3.4 (utility classes, no purge issues) |
| Image optimization | Not using `next/image` (lint warning) |
| Code splitting | Automatic via Next.js route-based splitting |

---

## 6. Complex / Fragile Modules

| Module | Concern | Severity |
|--------|---------|----------|
| `suppliers.py` / Companies page | "0 of 0" coverage bars — data flow broken somewhere in supplier_normalized → summary query → frontend rendering | High |
| `chat.py` + `chat_tools.py` + `chat_retrieval.py` | Most complex feature — SSE streaming + RAG + tool calls + citations + quota. Stub code still present. | Medium |
| `celery_app.py` | Multiple queues (ingestion, summarization, maintenance), 30+ tasks, Celery beat schedule. No beat health monitoring. | Medium |
| `middleware.ts` | Has a `.disabled` variant for edge eval bug. If re-enabled wrong, breaks prod. | Low |
| `billing/stripe_client.py` | Stripe in TEST mode. LIVE flip checklist not yet complete. | High (pre-launch) |
| `PatentFiguresPanel.tsx` | Uses raw `<img>` tags, figure URLs from Google Patents are brittle (content-addressed hashes change) | Medium |

---

## 7. Immediate Stabilization Priorities

Ordered by user impact:

1. **Fix Companies "0 of 0" coverage** — Trust-breaking. Core page looks broken.
2. **Fix TypeScript typecheck error** — Breaking `tsc --noEmit` means CI could fail.
3. **Fix blog lint error** — `prefer-const` on line 238. Trivial fix.
4. **Fix timezone-dependent test** — Use UTC to avoid CI flakiness.
5. **Recreate backend venv** — Unblock local development (P3.12).
6. **Run `npm audit fix`** — Address 8 vulnerabilities; defer Sentry major update.
7. **Replace placeholder patent IDs in blog posts** — Before public launch.
8. **Add `require_admin` to admin trigger endpoints** — Defense-in-depth.

---

## 8. Before/After Revamp Checklist

### Pre-revamp
- [x] Build compiles
- [x] CI pipeline works
- [x] Security audit complete
- [x] App map created
- [ ] Backend venv usable locally
- [ ] All typecheck/type errors fixed
- [ ] All tests pass (including timezone fix)
- [ ] npm audit vulnerabilities addressed

### Post-revamp
- [ ] Core Web Vitals measured (LCP, INP, CLS)
- [ ] Lighthouse scores on main routes
- [ ] All empty states explain why
- [ ] Companies page renders real data
- [ ] Expiry Radar shows opportunities, not just dates
- [ ] Today screen is personalized and actionable
- [ ] Keyboard navigation works on main routes
- [ ] Mobile breakpoints functional
