# CareerPilot — Progress Checkpoint

> Saved: end of **increment 5.2 (cover letters + ATS analyzer)** and the **Greenhouse/Lever/Ashby
> ATS source adapters**. Committed checkpoints: Phase 0 + 1.1, increments 1.2 → 4.2, and increments
> 5.1 → 6.2. This checkpoint adds the ATS adapters and Phase 5.2.

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
| Phase 2.4 — Greenhouse/Lever/Ashby ATS source adapters | ✅ complete |
| Phase 3.1 — Deterministic match scoring | ✅ complete |
| Phase 4.1 — Application tracker (event-sourced) | ✅ complete |
| Phase 4.2 — Email notifications (transport) | ✅ complete |
| Phase 5.1 — Resume tailoring (fact-grounding + diff/apply) | ✅ complete |
| Phase 6.1 — Scheduled alerts (idempotent digest email) | ✅ complete |
| Phase 6.2 — Application analytics & rejection intelligence | ✅ complete |
| Phase 5.2 — ATS analyzer (/100 + parse test), cover letters | ✅ complete |
| Phase 6.3 — Follow-ups, notification center, interview prep, skill-gap plan | ⏸️ not started |
| Email/calendar sync (Gmail) | ⏸️ deferred |
| Semantic matching (embeddings / pgvector) | ⏸️ deferred |
| Frontend (Next.js) & browser extension | ⏸️ not started |

## What exists

```
backend/app/
├── core/            config, db, logging, middleware, security, crypto, storage, prompts, media_types
├── models/          User, Profile, CareerGoal, DealBreakers, ResumeVersion, LLMUsage,
│                    Company, Job, JobSource, FetchLog, JobAnalysis, Match,
│                    Application, ApplicationEvent, Alert, AlertRun, TailorRun, CoverLetter
├── schemas/         auth, profile, career_goal, deal_breakers, resume, job, job_analysis,
│                    match, application, notification, alert, tailor, analytics,
│                    cover_letter, ats
├── repositories/    tenancy-scoped repos for every model above
├── services/        auth, profile, career_goal, deal_breakers, resume_parser, resume_renderer,
│                    resume, url_canonicalizer, job_normalizer, dedupe, job_ingestion,
│                    job_service, job_refresh, job_analysis, job_context, match_scoring, match,
│                    application_status, application, notification, encryption,
│                    alert_schedule, alert, tailor_grounding, tailor,
│                    application_analytics, analytics, ats_analyzer, cover_letter
├── adapters/        base (Fetcher/Adapter), robots (RobotsCache), user_url (HttpxFetcher),
│                    greenhouse, lever, ashby, jsonld, mapping, http_json,
│                    dispatch (DispatchFetcher), factory (build_fetcher)
├── gateway/         LLM gateway (providers: mock, openai) — complete + structured output
├── email/           base (EmailSender), console, recording, smtp, factory
├── prompts/         resume_extraction, job_analysis, tailor_resume, cover_letter (versioned)
├── workers/         celery_app + tasks (recheck_jobs, run_alerts)
└── api/v1/          auth, profile, career-goals, deal-breakers, resumes, jobs, matches,
                     applications, notifications, alerts, tailor-runs, cover-letters, analytics
backend/alembic/versions/  0001_initial … 0011_cover_letters
backend/tests/             171 tests (unit + API, offline — fake fetcher / mock LLM / recording email)
infra/docker-compose.yml   Postgres+pgvector, Redis, adobe/s3mock
docs/                      ARCHITECTURE.md, DATA-RETENTION.md, DATA-PROCESSING.md, STATUS.md
```

## API (v1)

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register` · `/login` · `/refresh` · `GET /auth/me` |
| Profile | `GET/PUT /profile`, `GET/PUT /career-goals`, `GET/PUT /deal-breakers` |
| Resumes | `POST /resumes` (upload) · `GET /resumes` · `GET /resumes/{id}` · `GET /resumes/{id}/export?format=pdf\|docx` · `POST /resumes/{id}/tailor` · `GET /resumes/{id}/ats-report?job_id=` |
| Jobs | `POST /jobs` (paste URL — Greenhouse/Lever/Ashby URLs use their public APIs) · `GET /jobs` · `GET /jobs/{id}` · `GET /jobs/{id}/sources` · `POST /jobs/{id}/refresh` · `POST /jobs/{id}/analyze` · `GET /jobs/{id}/analysis` · `POST /jobs/{id}/match` |
| Matches | `GET /matches` · `GET /matches/{id}` · `POST /matches/recompute` |
| Applications | `POST /applications` · `GET /applications` · `GET /applications/{id}` · `POST /applications/{id}/events` · `GET /applications/{id}/events` |
| Tailoring | `GET /tailor-runs/{id}` · `POST /tailor-runs/{id}/decisions` · `POST /tailor-runs/{id}/apply` |
| Cover letters | `POST /cover-letters` (generate) · `GET /cover-letters` · `GET /cover-letters/{id}` |
| Alerts | `POST /alerts` · `GET /alerts` · `GET /alerts/{id}` · `PUT /alerts/{id}` · `DELETE /alerts/{id}` · `POST /alerts/{id}/preview` · `POST /alerts/{id}/run` · `GET /alerts/{id}/runs` · `POST /alerts/unsubscribe/{token}` |
| Analytics | `GET /analytics/funnel` · `GET /analytics/rates` · `GET /analytics/rejections?by=source\|company\|role\|location\|resume_version\|month` |
| Notifications | `POST /notifications/test` |
| System | `GET /health` · `GET /ready` |

## Verified (last run)

- **171/171 tests pass** · **ruff check** clean · **ruff format** clean · **mypy --strict** clean.
- Migrations `0001` → `0011` apply cleanly to real Postgres (`alembic current` = `0011_cover_letters`).
- Live smoke against real Postgres (`uvicorn` with `LLM_PROVIDER=mock`, real DB + S3): resume upload →
  `GET /resumes/{id}/ats-report` → `/100` report with parse-test block; `GET /cover-letters` lists.
- ATS adapters: unit-tested per source with `httpx.MockTransport` (URL matching, JSON-LD mapping,
  Greenhouse double-unescape, HTTP-error fallback) plus an E2E ingestion test asserting
  `job_sources.adapter` = `greenhouse`/`lever`/`ashby`; a plain URL still files as `user_url`.
- Cover-letter generation and tailoring grounding are covered by unit + API tests (mock gateway);
  neither live smoke needed an ingested job (no outbound network).
- Earlier live E2E (increments 1.2–6.2): resume upload → parse → export; job ingest → dedupe;
  refresh → `Expired`; analyze → persisted; match `overall`/`sub_scores`/`scoring_version`;
  application derived status; `POST /notifications/test`; analytics funnel/rates/rejections; alerts.

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

# 4. Workers (lifecycle re-checks + scheduled alert digests)
celery -A app.workers.celery_app.celery_app worker
celery -A app.workers.celery_app.celery_app beat
```

> `.env` is gitignored — copy `.env.example`. Defaults need no keys: `LLM_PROVIDER=mock`,
> `EMAIL_PROVIDER=console` (nothing is sent or leaves the box until SMTP/OpenAI are configured).

## Next steps (agreed order)

1. **Follow-ups + notification center** — CRM reminders on applications; a persisted in-app feed.
2. **Interview prep + feedback** — kits, practice answers + rubric feedback history, STAR bank.
3. **Skill-gap + daily plan** — demand % / marginal coverage; an aggregate daily plan.
4. **Phase 2 remainder** — SmartRecruiters/RSS adapters + Google-PSE discovery (feature-flagged).
5. Deferred: Gmail/calendar sync; embeddings/pgvector semantic match sub-score; resume-specific
   matching; frontend & browser extension.

## Open follow-ups

- Legal review of the two compliance docs; fill `(confirm)` items and the DPDP DPO/Grievance contact.
- Google Programmable Search keys (adapter stays feature-flagged off until provided).
- Real OpenAI key for non-mock LLM runs; SMTP credentials for real email delivery.
- GitHub + LinkedIn-export imports into the canonical profile (Phase 1 remainder).
