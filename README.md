# CareerPilot

Full-lifecycle job-search platform (human-in-the-loop; not an auto-apply bot).

See the architecture plan: `~/.commandcode/plans/jobflow-architecture.md`.

> Current status: **Increment 0 — backend skeleton only.** A bootable FastAPI app plus local
> Postgres (pgvector) and Redis via docker-compose. No models, auth, adapters, or frontend yet.

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
alembic upgrade head        # apply migrations (creates users, llm_usage)
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

## Phase 0 endpoints

- `GET /health` — liveness
- `GET /ready` — readiness (checks Postgres + Redis)
- `POST /api/v1/auth/register` · `/login` · `/refresh` · `GET /api/v1/auth/me`

## LLM gateway

All model calls go through one gateway (`app/gateway`). Set `CAREERPILOT_LLM_PROVIDER` to
`mock` (no key, default in `.env.example`) or `openai` (needs `CAREERPILOT_OPENAI_API_KEY`).
