# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

EcoWaste Sorting Assistant — a Dockerized AI SaaS prototype (FastAPI) that detects waste objects in an
uploaded image with a custom YOLO model, applies deterministic recycling rules, and uses a CPU-based BitNet
LLM to explain the result in natural language. Designed to run on a Debian 12 GCP VM via Docker Compose.
See `README.md` for the full deployment/operations walkthrough and `docs/` for stage-specific design notes
(security, monitoring, cost, testing, product scenario).

## Commands

All commands run from the repo root. The app is intended to run inside Docker Compose, not bare-metal —
there is no local virtualenv setup; dependencies (ultralytics, firebase-admin, psycopg2, etc.) are only
installed inside the images.

```bash
docker compose build                 # build all services (bitnet image is slow: clones + compiles BitNet.cpp)
docker compose up -d                 # start the full stack
docker compose ps                    # list services
docker compose logs -f api worker    # tail API + worker logs
docker compose down                  # stop (add -v to also wipe postgres/prometheus/grafana volumes)
```

Tests (run inside the `api` container, which has all deps):

```bash
./scripts/run_tests.sh                                   # build api+worker, then full suite with coverage
./scripts/run_tests.sh tests/test_api.py                 # single file (args pass through to pytest)
./scripts/run_tests.sh tests/test_api.py::test_health_check   # single test
docker compose run --rm api python -m pytest -k inference     # run by keyword
```

`pytest.ini` enforces `--cov=app --cov=scripts` and defines markers `unit`, `api`, `integration`.

Cost estimator (standalone script, covered by tests):

```bash
docker compose run --rm api python scripts/cost_estimator.py --yolo-users 100 --llm-users 100 ...
```

## Architecture

Two execution paths share one request: a **synchronous** API response and an **asynchronous** worker that
enriches the result later.

```
POST /api/v1/image/predict (or /text/generate)
  → Firebase ID token verified (app/services/auth.py)
  → YOLO inference (app/services/inference.py)  OR  BitNet text gen (app/services/llm_client.py)
  → result written to BOTH stores:
      • PostgreSQL  (app/crud.py → Interaction table)  — local audit/history
      • Firestore   (app/services/firebase_store.py, collection: model_outputs)
  → a job is published to RabbitMQ (app/services/rabbitmq_client.py)
  → API returns immediately with firebase_output_id + postprocess_job_id
        ─────────────── async boundary ───────────────
  → app/worker.py consumes the job
  → app/services/postprocess.py computes label counts + applies app/services/ecowaste_rules.py
  → for images, app/services/ecowaste_llm.py asks BitNet to EXPLAIN (not override) the rule output
  → final doc saved to Firestore (collection: postprocessed_outputs, keyed by job_id)
  → client polls GET /api/v1/postprocess/results/{job_id}
```

### Services (docker-compose.yml)
`api` (FastAPI/uvicorn) · `worker` (same image, `python -m app.worker`) · `bitnet` (Dockerfile.bitnet,
llama-server with OpenAI-compatible `/v1/chat/completions`) · `postgres` · `rabbitmq` · `prometheus` ·
`grafana`. **Every port is bound to `127.0.0.1` only** — nothing is exposed off-host by design; remote
access is via SSH tunnel.

### Key cross-cutting conventions

- **Graceful degradation in the API path.** In `app/main.py`, Firebase save and RabbitMQ publish failures
  are caught and the corresponding `*_id` is set to `None` so the request still succeeds. Postgres write
  (`create_interaction`) is *not* guarded and will fail the request. BitNet text generation failure returns
  503. Preserve this distinction when editing endpoints.

- **Two layers, two stores.** Don't conflate them: PostgreSQL (`Interaction`, `app/models.py`) is the local
  request log queried via `/api/v1/history`; Firestore holds the durable model outputs and post-processed
  results. Firestore list queries filter in Python (over-fetch then filter) deliberately, to avoid needing
  composite indexes.

- **LLM is explanatory, not authoritative.** `ecowaste_rules.py` is the source of truth for bin/category
  decisions. The BitNet prompt (`ecowaste_llm.py`) is explicitly instructed to use only the supplied
  detections + rules and never override `recommended_bin`. Keep this grounding when touching prompts.

- **Config is entirely env-var driven.** Every tunable (`YOLO_*`, `BITNET_*`, `RATE_LIMIT_*`, `ALLOWED_*`,
  `ENABLE_BITNET_IMAGE_INTERPRETATION`, collection names, DB/queue URLs) is read via `os.getenv` at call
  time. `.env.example` is the canonical list; `docker-compose.yml` wires them in. Note the YOLO model path
  defaults differ: `Dockerfile` defaults to `yolo11n.pt`, but compose/`.env` override to
  `/app/models/yolo/best.pt`. The `models/` dir is git-ignored (large binaries) and mounted read-only.

- **Auth & Firebase init.** Firebase Admin is initialized lazily and idempotently (`if firebase_admin._apps`)
  in both `auth.py` and `firebase_store.py`, using GCP Application Default Credentials (no service-account
  JSON committed). `get_current_user` is the FastAPI dependency gating all protected routes.

- **Security middleware** is centralized in `app/security.py` (`setup_security`): TrustedHost, CORS, security
  headers, and a combined request-size + in-memory sliding-window rate limiter. Public paths (no auth, no
  rate limit) are `PUBLIC_PATHS`: `/health`, `/metrics`, `/openapi.json`, `/docs`, `/redoc`.

- **Metrics** (`app/monitoring.py`, `setup_metrics`): a middleware records `ai_saas_http_requests_total`,
  `ai_saas_http_request_duration_seconds`, `ai_saas_http_exceptions_total`, exposed at public `/metrics`.

- **YOLO model** is cached with `@lru_cache` (`get_yolo_model`) so it loads once per process.

### Testing pattern (important)

Tests run without any live services by mocking. Because `app/main.py` imports service functions by name
(`from app.services.x import f`), tests `monkeypatch.setattr("app.main.<name>", fake)` — patch the name as
re-exported in `app.main`, **not** the original module. Auth is bypassed via
`app.dependency_overrides[get_current_user]`. Inference/LLM/RabbitMQ/Firestore are all faked. Follow this
when adding endpoint tests.

The `worker` poison-message policy is `basic_nack(requeue=False)` — failed jobs are dropped, not retried, to
avoid infinite loops in development.
