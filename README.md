# CareerPilot

Full-lifecycle job-search platform (human-in-the-loop; not an auto-apply bot).

See the architecture plan: `~/.commandcode/plans/jobflow-architecture.md`.

> Current status: **increments 0 → 8.2** plus the **Greenhouse/Lever/Ashby ATS source adapters** —
> auth, profile/career goal/deal-breakers, resume upload/parse/versioning + ATS-safe export,
> Greenhouse/Lever/Ashby + user-URL job ingestion with dedupe, lifecycle expiry re-checks, LLM job
> analysis, deterministic match scoring, an event-sourced application tracker, an email notification
> layer, resume tailoring with deterministic fact-grounding + diff/apply, grounded versioned cover
> letters, a deterministic ATS analyzer (/100 + parse test), interview kits + practice rubric feedback
> + a STAR bank, skill-gap demand analysis + a daily plan (with a learning roadmap), a Command Center,
> a contacts CRM + grounded outreach/referral drafts, provider-abstracted email classification +
> calendar suggestions, scheduled (idempotent digest) alerts, and application analytics & rejection
> intelligence. Frontend and browser extension are not started. See `docs/STATUS.md` for the checkpoint.

## Prerequisites

- Docker Desktop
- Python 3.11+

## 1. Start infrastructure

From the repo root:

```bash
docker compose -f infra/docker-compose.yml up -d
```

This brings up:
- `db` — Postgres 16 with pgvector on `localhost:5432` (user/pass/db: `careerpilot`)
- `redis` — Redis 7 on `localhost:6379`

## 2. Run the backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    |  macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## 3. Check it's alive

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

Interactive API docs: http://localhost:8000/docs

## Database migrations

```bash
cd backend
alembic upgrade head        # apply migrations 0001..0014
alembic revision --autogenerate -m "your change"
```

> Requires the `db` container to be running.

## Tests and checks

```bash
cd backend
pytest                       # unit + API tests (uses in-memory SQLite, no Docker needed)
ruff check .                 # lint
ruff format --check .        # formatting
mypy app                     # type check
```

## Endpoints (v1)

- System: `GET /health` · `GET /ready`
- Auth: `POST /api/v1/auth/register` · `/login` · `/refresh` · `GET /api/v1/auth/me`
- Profile: `GET/PUT /api/v1/profile` · `/career-goals` · `/deal-breakers`
- Resumes: `POST /api/v1/resumes` · `GET /api/v1/resumes` · `GET /api/v1/resumes/{id}` ·
  `GET /api/v1/resumes/{id}/export?format=pdf|docx` · `POST /api/v1/resumes/{id}/tailor` ·
  `GET /api/v1/resumes/{id}/ats-report?job_id=`
- Jobs: `POST /api/v1/jobs` (paste a URL; Greenhouse/Lever/Ashby use their public APIs) ·
  `GET /api/v1/jobs` · `GET /api/v1/jobs/{id}` ·
  `/sources` · `POST /{id}/refresh` · `POST /{id}/analyze` · `GET /{id}/analysis` · `POST /{id}/match`
- Matches: `GET /api/v1/matches` · `GET /api/v1/matches/{id}` · `POST /api/v1/matches/recompute`
- Applications: `POST /api/v1/applications` · `GET /api/v1/applications` ·
  `GET /api/v1/applications/{id}` · `POST/GET /api/v1/applications/{id}/events`
- Tailoring: `GET /api/v1/tailor-runs/{id}` · `POST /api/v1/tailor-runs/{id}/decisions` ·
  `POST /api/v1/tailor-runs/{id}/apply`
- Cover letters: `POST /api/v1/cover-letters` · `GET /api/v1/cover-letters` ·
  `GET /api/v1/cover-letters/{id}`
- Interview: `POST/GET /api/v1/interview-kits` · `GET /api/v1/interview-kits/{id}` ·
  `POST/GET /api/v1/practice-sessions` · `GET /api/v1/practice-sessions/{id}` ·
  `POST/GET /api/v1/star-stories` · `GET/PUT/DELETE /api/v1/star-stories/{id}` ·
  `POST /api/v1/star-stories/draft`
- Insights: `GET /api/v1/skill-gap` · `GET /api/v1/learning-roadmap` · `GET /api/v1/daily-plan`
- Command Center: `GET /api/v1/command-center`
- CRM: `POST/GET /api/v1/contacts` · `GET/PUT/DELETE /api/v1/contacts/{id}` ·
  `POST/GET /api/v1/outreach-drafts` · `GET /api/v1/outreach-drafts/{id}` ·
  `POST /api/v1/outreach-drafts/{id}/send`
- Email/Cal: `POST/GET /api/v1/integrations` · `DELETE /api/v1/integrations/{id}` ·
  `POST /api/v1/integrations/{id}/sync` · `GET /api/v1/emails?status=` · `GET /api/v1/emails/{id}` ·
  `POST /api/v1/emails/{id}/suggest|accept|dismiss` · `POST/GET /api/v1/calendar-suggestions` ·
  `POST /api/v1/calendar-suggestions/{id}/confirm|dismiss`
- Alerts: `POST/GET /api/v1/alerts` · `GET/PUT/DELETE /api/v1/alerts/{id}` ·
  `POST /api/v1/alerts/{id}/preview` · `POST /api/v1/alerts/{id}/run` ·
  `GET /api/v1/alerts/{id}/runs` · `POST /api/v1/alerts/unsubscribe/{token}`
- Analytics: `GET /api/v1/analytics/funnel` · `/rates` · `/rejections?by=source|company|role|location|resume_version|month`
- Notifications: `POST /api/v1/notifications/test`

## LLM gateway

All model calls go through one gateway (`app/gateway`). Set `CAREERPILOT_LLM_PROVIDER` to
`mock` (no key, default in `.env.example`) or `openai` (needs `CAREERPILOT_OPENAI_API_KEY`).
