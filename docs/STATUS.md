# CareerPilot — Progress Checkpoint

> Saved: end of **increment 4.2 (email notifications)**. Phases 0 and 1.1 were committed earlier;
> this checkpoint lands increments 1.2 → 4.2 (resumes, job ingestion, matching, applications, email).

## Where we are

| Phase / increment | Status |
|---|---|
| Design deliverable (A–J) | ✅ complete (`docs/ARCHITECTURE.md`) |
| Compliance docs | ✅ drafted (`docs/DATA-RETENTION.md`, `docs/DATA-PROCESSING.md`) — need legal review |
| Phase 0 — Foundation | ✅ committed |
| Phase 1.1 — Profile, career goal, deal-breakers | ✅ committed |
| Phase 1.2 — Resume upload, parse, versioning, export | ✅ complete |
| Phase 2.1 — User-URL job ingestion, dedupe, fetch log | ✅ complete |
| Phase 2.2 — Job lifecycle expiry re-check (Celery) | ✅ complete |
| Phase 2.3 — LLM job analysis | ✅ complete |
| Phase 3.1 — Deterministic match scoring | ✅ complete |
| Phase 4.1 — Application tracker (event-sourced) | ✅ complete |
| Phase 4.2 — Email notifications (transport) | ✅ complete |
| Phase 5 — Tailoring, ATS analyzer, cover letters | ⏸️ not started |
| Phase 6 — Analytics, alerts, email/calendar sync | ⏸️ not started (alerts next) |
| Semantic matching (embeddings / pgvector) | ⏸️ deferred |
| Frontend (Next.js) & browser extension | ⏸️ not started |

## What exists

```
backend/app/
├── core/            config, db, logging, middleware, security, crypto, storage, prompts, media_types
├── models/          User, Profile, CareerGoal, DealBreakers, ResumeVersion, LLMUsage,
│                    Company, Job, JobSource, FetchLog, JobAnalysis, Match,
│                    Application, ApplicationEvent
├── schemas/         auth, profile, career_goal, deal_breakers, resume, job, job_analysis,
│                    match, application, notification
├── repositories/    tenancy-scoped repos for every model above
├── services/        auth, profile, career_goal, deal_breakers, resume_parser, resume_renderer,
│                    resume, url_canonicalizer, job_normalizer, dedupe, job_ingestion,
│                    job_service, job_refresh, job_analysis, match_scoring, match,
│                    application_status, application, notification, encryption
├── adapters/        base (Fetcher), robots (RobotsCache), user_url (HttpxFetcher, build_fetcher)
├── gateway/         LLM gateway (providers: mock, openai) — complete + structured output
├── email/           base (EmailSender), console, recording, smtp, factory
├── workers/         celery_app + tasks (recheck_jobs)
└── api/v1/          auth, profile, career-goals, deal-breakers, resumes, jobs, matches,
                     applications, notifications
backend/alembic/versions/  0001_initial … 0008_applications
backend/tests/             110 tests (unit + API, offline — fake fetcher / mock LLM / recording email)
infra/docker-compose.yml   Postgres+pgvector, Redis, adobe/s3mock
docs/                      ARCHITECTURE.md, DATA-RETENTION.md, DATA-PROCESSING.md, STATUS.md
```

## API (v1)

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register` · `/login` · `/refresh` · `GET /auth/me` |
| Profile | `GET/PUT /profile`, `GET/PUT /career-goals`, `GET/PUT /deal-breakers` |
| Resumes | `POST /resumes` (upload) · `GET /resumes` · `GET /resumes/{id}` · `GET /resumes/{id}/export?format=pdf\|docx` |
| Jobs | `POST /jobs` (paste URL) · `GET /jobs` · `GET /jobs/{id}` · `GET /jobs/{id}/sources` · `POST /jobs/{id}/refresh` · `POST /jobs/{id}/analyze` · `GET /jobs/{id}/analysis` · `POST /jobs/{id}/match` |
| Matches | `GET /matches` · `GET /matches/{id}` · `POST /matches/recompute` |
| Applications | `POST /applications` · `GET /applications` · `GET /applications/{id}` · `POST /applications/{id}/events` · `GET /applications/{id}/events` |
| Notifications | `POST /notifications/test` |
| System | `GET /health` · `GET /ready` |

## Verified (last run)

- **110/110 tests pass** · **ruff check** clean · **ruff format** clean · **mypy --strict** clean.
- Migrations `0001` → `0008` apply cleanly to real Postgres (`alembic upgrade head`).
- Live end-to-end per increment (uvicorn + real fetch + real Postgres):
  - resume upload → parse → export; job ingest → dedupe; refresh → `Expired`;
    analyze → persisted; match → `overall`/`sub_scores`/`scoring_version`;
    application create → derived status; `POST /notifications/test` → `provider=console`.

## How to resume

```powershell
# 1. Infra (may already be running)
docker compose -f infra/docker-compose.yml up -d

# 2. Backend
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
pytest -q
uvicorn app.main:app --reload          # http://localhost:8000/docs

# 3. Checks
ruff check . ; ruff format --check . ; mypy app

# 4. Workers (lifecycle re-checks)
celery -A app.workers.celery_app.celery_app worker
celery -A app.workers.celery_app.celery_app beat
```

> `.env` is gitignored — copy `.env.example`. Defaults need no keys: `LLM_PROVIDER=mock`,
> `EMAIL_PROVIDER=console` (nothing is sent or leaves the box until SMTP/OpenAI are configured).

## Next steps (agreed order)

1. **Scheduled alerts** — `alerts` + `alert_runs`, Celery beat, idempotent per-run logs, digest
   batching, quiet hours, unsubscribe, preview (uses the email layer + `matches`).
2. **Resume tailoring with diff + fact-check** — tailoring output as a new `resume_version`,
   claim→source-span fact-grounding verifier (unmapped claims blocked), side-by-side diff with
   per-change approve/reject.
3. Deferred: embeddings/pgvector semantic match sub-score; resume-specific matching; frontend &
   browser extension.

## Open follow-ups

- Legal review of the two compliance docs; fill `(confirm)` items and the DPDP DPO/Grievance contact.
- Google Programmable Search keys (adapter stays feature-flagged off until provided).
- Real OpenAI key for non-mock LLM runs; SMTP credentials for real email delivery.
- GitHub + LinkedIn-export imports into the canonical profile (Phase 1 remainder).
