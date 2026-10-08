# CareerPilot — Progress Checkpoint

> Saved: end of **increment 7.2 (skill-gap analysis & daily plan)**. Committed checkpoints: Phase 0 +
> 1.1, increments 1.2 → 4.2, 5.1 → 6.2, the ATS adapters + 5.2, and 7.1. This checkpoint adds
> skill-gap demand analysis and the daily plan.

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
| Phase 7.1 — Interview kits, practice rubric feedback, STAR bank | ✅ complete |
| Phase 7.2 — Skill-gap demand analysis, daily plan | ✅ complete |
| Phase 7.3 — Learning roadmap, Command Center | ⏸️ not started (next) |
| Phase 6.3 — Follow-ups, notification center | ⏸️ not started |
| Email/calendar sync (Gmail) | ⏸️ deferred |
| Semantic matching (embeddings / pgvector) | ⏸️ deferred |
| Frontend (Next.js) & browser extension | ⏸️ not started |

## What exists

```
backend/app/
├── core/            config, db, logging, middleware, security, crypto, storage, prompts, media_types
├── models/          User, Profile, CareerGoal, DealBreakers, ResumeVersion, LLMUsage,
│                    Company, Job, JobSource, FetchLog, JobAnalysis, Match,
│                    Application, ApplicationEvent, Alert, AlertRun, TailorRun, CoverLetter,
│                    InterviewKit, PracticeSession, StarStory
├── schemas/         auth, profile, career_goal, deal_breakers, resume, job, job_analysis,
│                    match, application, notification, alert, tailor, analytics,
│                    cover_letter, ats, interview, insights
├── repositories/    tenancy-scoped repos for every model above
├── services/        auth, profile, career_goal, deal_breakers, resume_parser, resume_renderer,
│                    resume, url_canonicalizer, job_normalizer, dedupe, job_ingestion,
│                    job_service, job_refresh, job_analysis, job_context, match_scoring, match,
│                    application_status, application, notification, encryption,
│                    alert_schedule, alert, tailor_grounding, tailor,
│                    application_analytics, analytics, ats_analyzer, cover_letter,
│                    answer_signals, interview_kit, practice, star_story,
│                    skill_gap, skill_gap_service, daily_plan, daily_plan_service
├── adapters/        base (Fetcher/Adapter), robots (RobotsCache), user_url (HttpxFetcher),
│                    greenhouse, lever, ashby, jsonld, mapping, http_json,
│                    dispatch (DispatchFetcher), factory (build_fetcher)
├── gateway/         LLM gateway (providers: mock, openai) — complete + structured output
├── email/           base (EmailSender), console, recording, smtp, factory
├── prompts/         resume_extraction, job_analysis, tailor_resume, cover_letter,
│                    interview_kit, answer_feedback, star_story (versioned)
├── workers/         celery_app + tasks (recheck_jobs, run_alerts)
└── api/v1/          auth, profile, career-goals, deal-breakers, resumes, jobs, matches,
                     applications, notifications, alerts, tailor-runs, cover-letters,
                     interview-kits, practice-sessions, star-stories, insights, analytics
backend/alembic/versions/  0001_initial … 0012_interview_prep
backend/tests/             201 tests (unit + API, offline — fake fetcher / mock LLM / recording email)
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
| Interview | `POST /interview-kits` · `GET /interview-kits?job_id=` · `GET /interview-kits/{id}` · `POST /practice-sessions` · `GET /practice-sessions` · `GET /practice-sessions/{id}` · `POST/GET /star-stories` · `GET/PUT/DELETE /star-stories/{id}` · `POST /star-stories/draft` |
| Insights | `GET /skill-gap` · `GET /daily-plan` |
| Alerts | `POST /alerts` · `GET /alerts` · `GET /alerts/{id}` · `PUT /alerts/{id}` · `DELETE /alerts/{id}` · `POST /alerts/{id}/preview` · `POST /alerts/{id}/run` · `GET /alerts/{id}/runs` · `POST /alerts/unsubscribe/{token}` |
| Analytics | `GET /analytics/funnel` · `GET /analytics/rates` · `GET /analytics/rejections?by=source\|company\|role\|location\|resume_version\|month` |
| Notifications | `POST /notifications/test` |
| System | `GET /health` · `GET /ready` |

## Verified (last run)

- **201/201 tests pass** · **ruff check** clean · **ruff format** clean · **mypy --strict** clean.
- Migrations `0001` → `0012` apply cleanly to real Postgres (`alembic current` = `0012_interview_prep`);
  7.2 added no tables (skill-gap + daily plan are computed on the fly).
- Live smoke (7.2) against real Postgres: `GET /skill-gap` and `GET /daily-plan` return 200 with the
  expected shape and reject unauthenticated calls; the deterministic folds are covered by pure unit
  tests plus API tests seeding analyses/matches/applications.
- Live smoke (7.1): `POST /practice-sessions` → rubric + deterministic signals with the timed
  `duration_seconds`; `POST`/`GET /star-stories` persist and list. Interview kits and the STAR `draft`
  are covered by unit + API tests (mock gateway).
- ATS adapters: unit-tested per source with `httpx.MockTransport` (URL matching, JSON-LD mapping,
  Greenhouse double-unescape, HTTP-error fallback) plus an E2E ingestion test asserting
  `job_sources.adapter` = `greenhouse`/`lever`/`ashby`; a plain URL still files as `user_url`.
- Earlier live E2E (increments 1.2–5.2): resume upload → parse → export → tailor/ats-report; job
  ingest → dedupe; refresh → `Expired`; analyze → persisted; match scores; application status; email;
  analytics; alerts; cover letters.

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

1. **Learning roadmap + Command Center** (Phase 7.3) — roadmap linked to the daily plan; Command
   Center aggregating goal/funnel/today/insight with evidence links.
2. **Follow-ups + notification center** — CRM reminders on applications; a persisted in-app feed.
3. **Phase 2 remainder** — SmartRecruiters/RSS adapters + Google-PSE discovery (feature-flagged).
4. Deferred: Gmail/calendar sync; embeddings/pgvector semantic match sub-score; resume-specific
   matching; frontend & browser extension.

## Open follow-ups

- Legal review of the two compliance docs; fill `(confirm)` items and the DPDP DPO/Grievance contact.
- Google Programmable Search keys (adapter stays feature-flagged off until provided).
- Real OpenAI key for non-mock LLM runs; SMTP credentials for real email delivery.
- GitHub + LinkedIn-export imports into the canonical profile (Phase 1 remainder).
