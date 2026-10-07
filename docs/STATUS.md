# CareerPilot — Progress Checkpoint

> Saved: end of **Phase 0 (Foundation)**. Phase 1 not started. No git repository yet
> (`git init` + first commit pending the operator's go-ahead).

## Where we are

| Phase | Status |
|---|---|
| Design deliverable (A–J) | ✅ complete (`docs/ARCHITECTURE.md`) |
| Compliance docs | ✅ drafted (`docs/DATA-RETENTION.md`, `docs/DATA-PROCESSING.md`) — need legal review |
| **Phase 0 — Foundation** | ✅ **complete & verified** |
| Phase 1 — Profile, Resume & Career Goal | ⏸️ not started |

## What exists

```
CareerPilot/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app: middleware, CORS, routers
│   │   ├── core/                       # config, db, logging, middleware, security (Argon2+JWT)
│   │   ├── models/                     # User, LLMUsage
│   │   ├── schemas/auth.py             # register/login/refresh/token/user
│   │   ├── repositories/               # BaseRepository (tenancy-scoped) + UserRepository
│   │   ├── services/auth_service.py    # register / authenticate / issue tokens
│   │   ├── api/system.py               # GET /health, GET /ready
│   │   ├── api/v1/auth.py              # register/login/refresh/me
│   │   └── gateway/                     # LLM provider protocol, OpenAI + mock, gateway, factory
│   ├── alembic/                        # env + baseline migration (users, llm_usage)
│   ├── tests/                          # conftest + system/security/auth/gateway (16 tests)
│   ├── Dockerfile  pyproject.toml  .env.example  alembic.ini
├── infra/docker-compose.yml            # Postgres+pgvector, Redis (both healthy)
├── .github/workflows/ci.yml            # ruff, format, mypy, pytest, pip-audit, gitleaks
├── docs/                               # ARCHITECTURE.md, DATA-RETENTION.md, DATA-PROCESSING.md
└── README.md  .gitignore
```

## Verified (last run)

- **16/16 tests pass** · **ruff check** clean · **ruff format** clean · **mypy --strict** clean.
- `docker compose up -d` → `infra-db-1` + `infra-redis-1` **healthy**.
- `alembic upgrade head` against real Postgres → tables `users`, `llm_usage`, `alembic_version`.
- `GET /health` → 200 `{"status":"ok"}`; `GET /ready` → 200 `{"status":"ok","checks":{"database":"ok","cache":"ok"}}`.

## How to resume

```bash
# 1. Infra (may still be running; otherwise start it)
docker compose -f infra/docker-compose.yml up -d      # stop with: ... down

# 2. Backend
cd backend
.venv\Scripts\activate            # venv already created with deps installed
alembic upgrade head
pytest -q                         # expect 16 passing
uvicorn app.main:app --reload     # http://localhost:8000/docs

# 3. Checks
ruff check . ; ruff format --check . ; mypy app
```

> Note: Docker containers are **not** part of the repo. `.env` is gitignored — copy `.env.example`
> if it's missing (defaults: `LLM_PROVIDER=mock`, no API key needed).

## Next step

**Phase 1 — Profile, Resume & Career Goal:** onboarding wizard (< 5 min), PDF/DOCX upload →
parsed profile with per-section confidence, GitHub + LinkedIn-export imports, immutable resume
versioning, ATS-safe PDF/DOCX export. Awaiting go-ahead.

## Open follow-ups

- `git init` + first commit (not done — removes nothing, just hasn't been requested).
- Legal review of the two compliance docs; fill `(confirm)` items and the DPDP Grievance Officer/DPO contact.
- Google Programmable Search keys (adapter stays feature-flagged off until provided).
- Real OpenAI key for non-mock LLM runs.
