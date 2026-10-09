# CareerPilot

Full-lifecycle job-search platform (human-in-the-loop; not an auto-apply bot).

See the architecture plan: `~/.commandcode/plans/jobflow-architecture.md`.

> Current status: **increments 0 → 8.2** plus the **Greenhouse/Lever/Ashby/SmartRecruiters ATS source
> adapters** and the **RSS/Atom + Google-PSE discovery sources with a leads lifecycle** — auth,
> profile/career goal/deal-breakers, resume upload/parse/versioning + ATS-safe export,
> Greenhouse/Lever/Ashby/SmartRecruiters + user-URL job ingestion with dedupe, a leads
> (New→Queued→Captured→Dismissed) discovery layer (RSS/Atom feeds + a feature-flagged Google-PSE
> source with a daily quota + 24 h query cache), lifecycle expiry re-checks, LLM job analysis,
> deterministic match scoring (non-Active jobs never recommended), an event-sourced application
> tracker with bookmarklet/paste-URL capture, an email notification
> layer, resume tailoring with deterministic fact-grounding + diff/apply, grounded cover letters with
> revision lineage, a deterministic ATS analyzer (/100 + parse test) with persisted report snapshots,
> interview kits + practice rubric
> feedback
> + a STAR bank, skill-gap demand analysis (with marginal-coverage gain) + a daily plan (with a
> learning roadmap), a Command Center,
> a contacts CRM + grounded outreach/referral drafts, a follow-ups view + a persisted in-app
> notification center (auto-refreshed on a Celery-beat schedule), provider-abstracted email
> classification + calendar suggestions, scheduled
> (idempotent digest) alerts, and application analytics & rejection intelligence (funnel/rates with
> per-dimension breakdowns + a period filter). Frontend and browser
> extension are not started. See `docs/STATUS.md` for the checkpoint.

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
alembic upgrade head        # apply migrations 0001..0016
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
  `GET /api/v1/resumes/{id}/ats-report?job_id=` · `POST /api/v1/resumes/{id}/ats-report` (persist)
- ATS reports: `GET /api/v1/ats-reports?resume_version_id=&job_id=&limit=&offset=` ·
  `GET /api/v1/ats-reports/{id}`
- Jobs: `POST /api/v1/jobs` (paste a URL; Greenhouse/Lever/Ashby/SmartRecruiters use their public
  APIs) · `POST /api/v1/jobs/capture` (paste a URL; create/update the job + start an application) ·
  `GET /api/v1/jobs?status=` · `GET /api/v1/jobs/{id}` ·
  `/sources` · `POST /{id}/refresh` · `POST /{id}/analyze` · `GET /{id}/analysis` · `POST /{id}/match`
- Leads: `POST/GET /api/v1/discovery-sources` · `DELETE /api/v1/discovery-sources/{id}` ·
  `POST /api/v1/discovery-sources/{id}/run` · `GET /api/v1/leads?status=` · `GET /api/v1/leads/{id}` ·
  `POST /api/v1/leads/{id}/capture` · `POST /api/v1/leads/{id}/dismiss`
- Matches: `GET /api/v1/matches` · `GET /api/v1/matches/{id}` · `POST /api/v1/matches/recompute`
- Applications: `POST /api/v1/applications` · `GET /api/v1/applications` ·
  `GET /api/v1/applications/{id}` · `POST/GET /api/v1/applications/{id}/events`
- Tailoring: `GET /api/v1/tailor-runs/{id}` · `POST /api/v1/tailor-runs/{id}/decisions` ·
  `POST /api/v1/tailor-runs/{id}/apply`
- Cover letters: `POST /api/v1/cover-letters` · `GET /api/v1/cover-letters?job_id=&limit=&offset=` ·
  `GET /api/v1/cover-letters/{id}` · `POST /api/v1/cover-letters/{id}/revise` ·
  `DELETE /api/v1/cover-letters/{id}`
- Interview: `POST/GET /api/v1/interview-kits` · `GET /api/v1/interview-kits/{id}` ·
  `POST/GET /api/v1/practice-sessions` · `GET /api/v1/practice-sessions/{id}` ·
  `POST/GET /api/v1/star-stories` · `GET/PUT/DELETE /api/v1/star-stories/{id}` ·
  `POST /api/v1/star-stories/draft`
- Insights: `GET /api/v1/skill-gap` · `GET /api/v1/learning-roadmap` · `GET /api/v1/daily-plan`
- Command Center: `GET /api/v1/command-center`
- CRM: `POST/GET /api/v1/contacts` · `GET/PUT/DELETE /api/v1/contacts/{id}` ·
  `GET /api/v1/follow-ups` · `POST/GET /api/v1/outreach-drafts` ·
  `GET /api/v1/outreach-drafts/{id}` · `POST /api/v1/outreach-drafts/{id}/send`
- Email/Cal: `POST/GET /api/v1/integrations` · `DELETE /api/v1/integrations/{id}` ·
  `POST /api/v1/integrations/{id}/sync` · `GET /api/v1/emails?status=` · `GET /api/v1/emails/{id}` ·
  `POST /api/v1/emails/{id}/suggest|accept|dismiss` · `POST/GET /api/v1/calendar-suggestions` ·
  `POST /api/v1/calendar-suggestions/{id}/confirm|dismiss`
- Alerts: `POST/GET /api/v1/alerts` · `GET/PUT/DELETE /api/v1/alerts/{id}` ·
  `POST /api/v1/alerts/{id}/preview` · `POST /api/v1/alerts/{id}/run` ·
  `GET /api/v1/alerts/{id}/runs` · `POST /api/v1/alerts/unsubscribe/{token}`
- Analytics: `GET /api/v1/analytics/funnel?by=&since=&until=` · `/rates?by=&since=&until=` ·
  `/rejections?by=source|company|role|location|resume_version|month&since=&until=`
- Notifications: `POST /api/v1/notifications/test` · `GET /api/v1/notifications?unread=` ·
  `GET /api/v1/notifications/unread-count` · `POST /api/v1/notifications/refresh` ·
  `POST /api/v1/notifications/read-all` · `POST /api/v1/notifications/{id}/read` ·
  `DELETE /api/v1/notifications/{id}`

## LLM gateway

All model calls go through one gateway (`app/gateway`). Set `CAREERPILOT_LLM_PROVIDER` to
`mock` (no key, default in `.env.example`) or `openai` (needs `CAREERPILOT_OPENAI_API_KEY`).
