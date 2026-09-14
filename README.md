# QuantPulse

**QuantPulse** is a real-time market monitoring platform: it ingests live trade data for equities, forex, and crypto, runs a rolling anomaly detector over it, layers AI-generated insight on top via Azure OpenAI, and pushes all of it live to a React dashboard — deployed identically to a local Kind cluster and a real Azure Kubernetes Service cluster.

It is designed as a portfolio-ready full-stack project that demonstrates:

- **Real-time data pipelines** — a live Finnhub WebSocket feed, Redis pub/sub, and a live-push WebSocket to the browser in place of polling
- **Frontend development** with React
- **Backend API development** with FastAPI, including WebSocket auth and live updates
- **Database design and migrations** with PostgreSQL + Alembic
- **AI integration** with Azure OpenAI for anomaly explanations and market summaries
- **Containerization** with Docker
- **Kubernetes orchestration**, deployed identically to local Kind and real Azure AKS
- **Observability** with Prometheus, Grafana, and kube-state-metrics — built on real application metrics, not just process stats
- **Deployment automation** with shell scripts

---

## Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [System Screenshots](#system-screenshots)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Quick Start](#quick-start)
- [Deployment Scripts](#deployment-scripts)
- [Access URLs and Credentials](#access-urls-and-credentials)
- [Monitoring and Observability](#monitoring-and-observability)
- [Live Updates & Caching (Redis)](#live-updates--caching-redis)
- [Automated Test Suite](#automated-test-suite)
- [Resilience / Restart Testing](#resilience--restart-testing)
- [Cold-Start Validation and Testing](#cold-start-validation-and-testing)
- [Why This Project Is Cloud-Native](#why-this-project-is-cloud-native)
- [Troubleshooting](#troubleshooting)
- [Future Improvements](#future-improvements)
- [Mermaid Diagram Sources](#mermaid-diagram-sources)
- [Author](#author)

---

## Project Overview

QuantPulse streams live trades for a mix of equities (AAPL, TSLA, NVDA, MSFT, GOOGL, AMZN, META), forex (EUR/USD, USD/CAD), and crypto (BTC/USDT) from Finnhub's WebSocket API, writes every trade to Postgres, and runs a rolling z-score anomaly detector on price and volume in real time. Three separate Azure OpenAI-powered jobs turn that data into plain-English insight: per-alert explanations, a once-daily digest, and a continuously refreshing per-symbol summary. The application provides:

- A **web dashboard** for live price trends, trade summaries, AI-generated insights, and alerts — updated over a WebSocket instead of polling
- A **FastAPI backend** for the REST API, JWT auth, and the live-push WebSocket endpoint
- A **PostgreSQL database** for ticks, alerts, symbols, and AI-generated summaries
- **Redis** for pub/sub live push and cache-aside reads on hot endpoints
- A **Prometheus metrics endpoint** exposing real application metrics (ticks ingested, alerts by severity, cache hit rate, active connections), not just process stats
- A **Grafana dashboard** built on those real metrics, plus CronJob health via kube-state-metrics and Redis process health via redis_exporter
- A **Kubernetes deployment** that runs identically on Kind (local) and Azure Kubernetes Service (real cloud)

This project was refined through multiple **cold-start deployments** and **live failure-injection testing** (killing services, forcing outages, full cluster rebuilds), with each finding used to improve automation, provisioning, and reliability.

---

## Key Features

### Application Features
- User login/authentication (JWT)
- Live price trends and trade summaries across equities, forex, and crypto
- Real-time anomaly alerts (rolling z-score on price and volume)
- AI-generated insight: per-alert explanations, a daily digest, and a continuously refreshing per-symbol summary
- Live dashboard updates over WebSocket, not polling
- Seeded demo data for quick evaluation

### Platform / DevOps Features
- Dockerized backend, frontend, ingestion, and AI job images
- Kubernetes manifests for every service, with a shared base + Kustomize overlays for Kind vs. AKS
- Ingress-based routing for the main application
- Automated database migrations with Alembic
- Automated seed data initialization
- Prometheus scraping of real application metrics, not just process stats
- Pre-provisioned Grafana data source and dashboard
- One-command deployment support through shell scripts, identical for local Kind and real Azure AKS

---

## Architecture

QuantPulse runs as a multi-service application inside a **Kind Kubernetes cluster** on a local development machine.

### High-Level Architecture Diagram

<img width="4950" height="5460" alt="Architecture Diagram" src="https://github.com/user-attachments/assets/2411bcda-315e-4c80-8302-13e709648571" />


**Architecture summary:**
- The **user browser** accesses QuantPulse through **NGINX Ingress** at `http://localhost`
- The **frontend service** serves the React application through an NGINX container
- The **backend service** exposes a FastAPI REST API and a `/metrics` endpoint
- **PostgreSQL** stores symbols, ticks, alerts, users, and AI-generated summaries
- **Prometheus** scrapes backend metrics
- **Grafana** queries Prometheus and displays observability dashboards

---

## System Screenshots

### Login Page

<img width="1920" height="1080" alt="QuantPulse_Login" src="https://github.com/user-attachments/assets/fefd3688-8bee-4f20-aec2-17ab79ec304c" />


### Main Application Dashboard

<img width="1920" height="1020" alt="QuantPulse_Dashboard" src="https://github.com/user-attachments/assets/9b78f704-88e7-4edb-b26a-6b3fbac1f8c1" />


### Prometheus Query Validation

The screenshot below shows the `up` query successfully returning the backend target.

<img width="1920" height="1080" alt="Prometheus" src="https://github.com/user-attachments/assets/e19ac7a8-ab30-4f3d-ac95-bc73379ac8f3" />


### Grafana Monitoring Dashboard

<img width="1920" height="1506" alt="Grafana_Dashboard" src="https://github.com/user-attachments/assets/35475e4d-3926-459e-987f-faf79106ddad" />


### Successful Automated Deployment Output

<img width="1759" height="716" alt="Deployment" src="https://github.com/user-attachments/assets/43a6b5a7-cca4-4b54-9eb6-2c67059fac39" />


---

## Tech Stack

### Frontend
- **React**
- **Vite**
- **NGINX** (for static frontend serving)

### Backend
- **FastAPI**
- **SQLAlchemy**
- **Pydantic**
- **Alembic**
- **Uvicorn**

### Database
- **PostgreSQL**

### Caching / Real-Time Messaging
- **Redis** (cache-aside reads + pub/sub for live push)

### Monitoring
- **Prometheus**
- **Grafana**
- **kube-state-metrics** (CronJob/Job success-failure visibility)
- **redis_exporter** (Redis process-level metrics)

### Infrastructure / DevOps
- **Docker**
- **Kubernetes**
- **Kind**
- **NGINX Ingress Controller**
- **Bash scripting**

---

## Repository Structure

```text
.
├── backend/                     # FastAPI backend
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── core/                # config, security (JWT), cache, redis client
│   │   ├── database/            # models, session
│   │   ├── routers/             # auth, symbols, ticks, alerts, summary, stream (WS)
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/                   # real-Postgres pytest suite
│   ├── Dockerfile
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/                    # React frontend
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   ├── nginx.conf                # includes the WS-upgrade proxy config for live push
│   └── package.json
├── ingestion/                    # Finnhub WebSocket ingestion service (single replica)
│   ├── finnhub_ingestion.py       # the real service
│   ├── anomaly_detector.py        # rolling z-score anomaly detection
│   ├── finnhub_peek.py            # ad-hoc manual inspection script
│   └── tests/
├── ai/                            # Three Azure OpenAI-powered CronJobs
│   ├── explainer.py                # per-alert explanations
│   ├── daily_summary.py            # once-daily digest
│   ├── symbol_summary.py           # continuous per-symbol summary
│   ├── llm_client.py
│   ├── db.py
│   └── tests/
├── k8s/                          # Kubernetes manifests (base, shared by Kind and AKS)
│   ├── backend/ frontend/ ingestion/ ai/ postgres/ redis/
│   ├── monitoring/
│   │   ├── prometheus/ grafana/
│   │   └── kube-state-metrics/    # RBAC scoped to just cronjobs/jobs
│   ├── ingress/
│   ├── namespace.yaml configmap.yaml secret.yaml
│   └── kustomization.yaml
├── overlays/aks/                 # Kustomize overlay: ACR image rewriting for AKS
├── dashboards/
│   └── dashboard-export.json    # Exported Grafana dashboard JSON
├── scripts/
│   ├── setup-kind.sh deploy-kind.sh cleanup.sh port-forward.sh
│   ├── deploy-aks.sh             # same deploy, real Azure
│   ├── resilience-check.sh / resilience_check.py   # Phase 4 snapshot/diff tool
│   └── env-azure.example.sh
├── docs/
│   └── resilience-testing-runbook.md   # 5 live failure-injection scenarios
├── kind-config.yaml
├── docker-compose.yml
├── pytest.ini
└── README.md
```

---

## Quick Start

### Prerequisites

Make sure the following are installed:

- Docker
- kubectl
- kind
- Bash shell
- Git

Optional but helpful:
- Node.js / npm
- Python 3.10+

### Recommended Deployment Flow

QuantPulse now supports a structured deployment flow using scripts.

1. **Clean up any existing cluster**
2. **Create a Kind cluster and install ingress**
3. **Deploy the full application stack**
4. **Start port forwarding for Prometheus and Grafana**

### Step 1 — Clean up old resources

```bash
./scripts/cleanup.sh
```

### Step 2 — Create the Kind cluster and install ingress

```bash
./scripts/setup-kind.sh
```

### Step 3 — Deploy QuantPulse

Needs a real [Finnhub](https://finnhub.io/) API key (free tier is fine) exported first — the script hard-fails with a clear message if it's missing, rather than silently deploying an ingestion service that can never authenticate to Finnhub:

```bash
export FINNHUB_API_KEY='your-key-here'
./scripts/deploy-kind.sh
```

Azure OpenAI is optional for Kind too (same as the AKS flow below) — without `AZURE_OPENAI_ENDPOINT`/`AZURE_OPENAI_API_KEY`/`AZURE_OPENAI_DEPLOYMENT` exported, the deploy still succeeds and everything works except the two AI CronJobs that call it, which just fail at their next scheduled trigger until the secret exists.

### Step 4 — Start Prometheus and Grafana port forwarding

```bash
./scripts/port-forward.sh
```

> If you do not use `port-forward.sh`, Prometheus and Grafana can also be run with separate terminal sessions:
>
> ```bash
> kubectl port-forward svc/prometheus 9090:9090 -n quantpulse
> kubectl port-forward svc/grafana 3000:3000 -n quantpulse
> ```

---

## Deployment Scripts

<img width="2234" height="7430" alt="Deployment Automation" src="https://github.com/user-attachments/assets/dabc5582-bce1-4b21-8914-77c0c5deb63c" />


### `cleanup.sh`
Deletes the existing Kind cluster and helps ensure a clean cold start.

### `setup-kind.sh`
Responsible for:
- Creating the Kind cluster
- Installing NGINX Ingress Controller
- Waiting for ingress readiness

### `deploy-kind.sh`
Responsible for:
- Building backend Docker image
- Building frontend Docker image
- Loading images into Kind
- Applying Kubernetes manifests
- Waiting for pods to become ready
- Running Alembic migrations
- Seeding the database
- Printing URLs and credentials

### `port-forward.sh`
Starts port forwarding for:
- Prometheus on `localhost:9090`
- Grafana on `localhost:3000`

### `deploy-aks.sh`
Same idea as `deploy-kind.sh`, but for a real Azure Kubernetes Service
cluster instead of a local Kind one: builds + pushes all four images to
Azure Container Registry (`linux/arm64`), applies the `overlays/aks`
Kustomize overlay, provisions the `finnhub-secret` and
`azure-openai-secret` Kubernetes secrets from environment variables, runs
migrations, and seeds the database.

It defaults to this project's own Azure resource names, but every name is
overridable — anyone cloning this repo can point it at their own
subscription instead of editing the script:

```bash
cp scripts/env-azure.example.sh scripts/.env.azure
# edit scripts/.env.azure: fill in your Finnhub/Azure OpenAI keys, and
# uncomment + set AZURE_RESOURCE_GROUP / AZURE_AKS_CLUSTER / AZURE_ACR_NAME
# if you're deploying to your own Azure resources rather than the
# author's
source scripts/.env.azure
./scripts/deploy-aks.sh
```

`scripts/.env.azure` is gitignored (matches the existing `.env.*` rule) —
your real keys never get committed. Requires an existing AKS cluster and
ACR (`az aks create` / `az acr create`) and `az aks start` run first if
the cluster is stopped; this script deliberately never starts or stops
the cluster itself, to keep that a conscious, cost-aware step.

---

## Access URLs and Credentials

### Application URLs

- **QuantPulse Frontend:** `http://localhost`
- **Prometheus:** `http://localhost:9090`
- **Grafana:** `http://localhost:3000`

### Default Local Demo Credentials

#### QuantPulse Login
- **Username:** `shreyas`
- **Password:** `Password123`

#### Grafana Login
- **Username:** `admin`
- **Password:** `admin123`

> These credentials are intended for **local development/demo only**.

---

## Monitoring and Observability

QuantPulse includes an observability stack that helps validate backend health and runtime behavior.

### Prometheus
Four scrape targets, every 5s: the backend and ingestion services' own `/metrics` endpoints, plus (new) `kube-state-metrics:8080` and `redis-exporter:9121`. `redis_exporter` runs as its own Deployment rather than a sidecar on the Redis pod -- found live via code review that a sidecar ties Kubernetes' Pod-Ready gate (the AND of every container's readiness) to the Redis Service's own endpoints, so a failed exporter image pull would silently take live WS push and caching down too, not just the metrics endpoint.

Example query used during validation:

```promql
up{instance="backend:8000", job="quantpulse-backend"}
```

### Grafana
Grafana is provisioned with:
- A **Prometheus datasource**
- A **pre-configured QuantPulse monitoring dashboard**

The dashboard is QuantPulse-specific, not generic process metrics -- ticks ingested and alerts generated were already being scraped since Phase 2, but had zero panels using them until this pass:
- Backend/Redis status, CronJob success rate (top row)
- Ticks ingested rate, active WebSocket connections
- Alerts by severity (HIGH/MEDIUM, from the anomaly detector)
- Cache hit rate (`/ticks/latest`, `/summary/*`)
- Backend request rate + p95 latency, labeled by route template (not raw path, to keep cardinality bounded -- see `backend/app/main.py`'s `prometheus_request_metrics` middleware)
- Redis memory usage, ops/sec, connected clients -- real process-level metrics from `redis_exporter`, not just the app's own counters
- `ai-explainer`/`ai-daily-summary`/`ai-symbol-summary` job success/failure history, from `kube-state-metrics` (scoped to just `cronjobs`/`jobs` RBAC, not the full generic resource set upstream's own manifests grant)
- Backend CPU/memory, demoted to a small row at the bottom -- still useful, just not the whole dashboard anymore

### Monitoring Flow Diagram

<img width="5179" height="780" alt="Monitering data flow" src="https://github.com/user-attachments/assets/a5748820-1461-4244-a914-c92987b172db" />


---

## Live Updates & Caching (Redis)

Redis serves two distinct purposes, both independent of each other even though they share the same instance:

**Real-time push (pub/sub).** `ingestion/finnhub_ingestion.py` publishes every tick/alert to a Redis channel (`ticks` / `alerts`) immediately after writing it to Postgres -- best-effort, never blocking or failing the write itself if Redis is briefly unreachable. The backend's `WS /api/v1/stream` endpoint (`backend/app/routers/stream.py`) subscribes to those same channels and relays each event straight through to any connected browser tab over a WebSocket. This is what lets the dashboard react to real trade activity as it happens instead of polling on a fixed timer -- `frontend/src/services/stream.js` opens the connection and `Dashboard.jsx` reloads (throttled to at most once/sec) whenever something actually arrives, with a much longer interval-based poll kept only as a fallback in case the WS connection is ever down for an extended stretch.

Auth on the socket doesn't go through the usual header-based flow: a browser's native WebSocket API can't set an `Authorization` header on the handshake the way a normal `fetch`/`axios` call can, so the connection is accepted first and the client's first text frame must be `{"token": "<jwt>"}` -- validated with the same decode + user lookup every REST endpoint uses. Anything else (timeout, bad token) closes the connection with app-defined WS close code `4401` before ever subscribing to Redis.

**Cache-aside reads.** `GET /ticks/latest` (5s TTL), `GET /summary/today`, and `GET /summary/symbols` (60s TTL) check Redis before hitting Postgres -- see `backend/app/core/cache.py`. Pure TTL expiry, not event-driven invalidation: a cached value is simply overwritten on the next miss after it expires, whichever endpoint hits it. Every cache operation degrades silently to "just hit Postgres" on a Redis error, so a Redis outage never takes an endpoint down -- only removes the shortcut in front of it.

Redis itself (`redis:7-alpine`) runs with no persistent volume -- nothing stored in it is ever the source of truth (Postgres is), so losing it on a restart just means a cold cache and a brief reconnect gap for any open WS clients, never lost data.

**Running locally:** `docker-compose.yml` includes a `redis` service -- nothing extra to start. On Kind/AKS it's `k8s/redis/deployment.yaml` + `service.yaml`, deployed automatically by `deploy-kind.sh`/`deploy-aks.sh` alongside everything else.

---

## Automated Test Suite

Real Postgres, not sqlite or mocks -- `backend/tests/`, `ingestion/tests/`, and `ai/tests/` each run against an actual Postgres database, since several of the things under test (Postgres's `DISTINCT ON`, real transaction/rollback behavior) don't exist or behave differently against a fake one. Runs in CI (`.github/workflows/build-push-acr.yml`) on every push to `main` that touches app code, gating the image build -- `build-and-push` only runs if `test` passes.

**What's covered:**
- `ingestion/tests/test_anomaly_detector.py` -- the rolling z-score anomaly detection algorithm itself: threshold classification, cooldown suppression (per-symbol, per-kind), the display-value cap, rolling-window eviction.
- `backend/tests/test_market_hours.py` -- `is_market_open()`'s NYSE holiday calendar and DST handling, checked against real calendar facts (actual 2026/2027 holiday dates, actual DST transition dates), not against the module's own internal helpers.
- `backend/tests/test_services.py` -- the service layer, including `TickService.get_latest_tick_per_symbol()`'s `DISTINCT ON` tiebreaking.
- `ai/tests/test_explainer.py`, `ai/tests/test_symbol_summary.py` -- the two AI CronJob scripts, with the LLM client always monkeypatched (no real Azure OpenAI calls in tests) but every DB read/write real, including the resilience guarantee that one alert's/symbol's failed write or LLM call doesn't sink the rest of the batch.

**Running locally:**

```bash
# A throwaway Postgres for tests -- separate from your dev/deploy one.
docker run -d --name quantpulse-test-pg \
  -e POSTGRES_USER=quantpulse -e POSTGRES_PASSWORD=quantpulse123 -e POSTGRES_DB=quantpulse \
  -p 5433:5432 postgres:16-alpine

cd backend
DATABASE_URL="postgresql://quantpulse:quantpulse123@localhost:5433/quantpulse" alembic upgrade head
cd ..

pip install -r backend/requirements.txt -r ingestion/requirements.txt -r ai/requirements.txt pytest

TEST_DATABASE_URL="postgresql://quantpulse:quantpulse123@localhost:5433/quantpulse" \
  pytest backend/tests/ ingestion/tests/ ai/tests/ -v
```

---

## Resilience / Restart Testing

Unlike the automated pytest suite above, this is deliberately user-driven, not automated -- the failures (killing Postgres, killing ingestion mid-tick, an `az aks stop`/`start` cycle, a full delete+recreate, redeploying mid-CronJob-run) are injected by hand against a real cluster, one at a time, with the recovery watched and judged live.

`docs/resilience-testing-runbook.md` has the full walkthrough per scenario -- what to run, what should happen (grounded in this project's actual code, not a guess), and how to verify it. `scripts/resilience-check.sh` (a thin wrapper around `resilience_check.py`) supports it with two commands that never change cluster state, only observe it:

```bash
./scripts/resilience-check.sh snapshot pre   # before injecting a failure
# ... inject the failure, wait for recovery ...
./scripts/resilience-check.sh diff pre       # after
```

`diff` reports tick count growth since the snapshot, any pod that's still not `Ready`, and any restart count that increased -- enough to tell "recovered" from "still broken" without re-deriving it by hand each time.

---

## Cold-Start Validation and Testing

A major goal of this project was to move from a partially manual setup to a **repeatable, low-friction deployment**.

This was achieved through repeated cold-start testing.

### Cold-Start Improvement Summary

<img width="1240" height="5895" alt="Testing" src="https://github.com/user-attachments/assets/645af8ab-8180-4589-aa3b-047733ead0b8" />


### What Was Improved Across Iterations

#### Cold Start 1
- Found frontend image loading issues
- Found Grafana provisioning/configuration issues
- Fixed ConfigMap setup and image handling

#### Cold Start 2
- Found misplaced dashboard JSON and ingress timing issues
- Reorganized files and improved deployment order
- Added better deployment automation

#### Cold Start 3
- Found missing database migrations and seed data
- Automated Alembic migrations and database seeding

#### Cold Start 4
- Achieved zero-intervention deployment success

### Final Result
The final deployment flow was successfully cold-started end-to-end, including:
- Cluster creation
- Ingress installation
- Application deployment
- Monitoring deployment
- Database schema initialization
- Demo data seeding
- Frontend login success
- Prometheus validation
- Grafana dashboard availability

---

## Why This Project Is Cloud-Native

Yes — QuantPulse follows several cloud-native principles.

### Cloud-native characteristics in this project
- **Containerized services** using Docker -- frontend, backend, ingestion, and the AI jobs each get their own image
- **Service decomposition** into frontend, backend, ingestion, three AI CronJobs, Postgres, Redis, and the monitoring stack (Prometheus, Grafana, kube-state-metrics, redis_exporter)
- **Kubernetes orchestration** with declarative manifests -- one shared base plus a Kustomize overlay for what actually differs between environments (image registry, pull policy), not two copies of the same YAML
- **Infrastructure automation** with scripts -- the same `deploy-kind.sh`/`deploy-aks.sh` pattern deploys either target from one source of truth
- **Observability-first design** with Prometheus, Grafana, kube-state-metrics, and redis_exporter, built on real application metrics (ticks ingested, alerts by severity, cache hit rate, request latency) rather than only generic process stats
- **Stateless application containers** where appropriate -- ingestion is the deliberate, documented exception (single-replica by design, not an oversight)
- **Configuration externalization** using ConfigMaps and Secrets
- **Repeatable deployments** validated through cold starts, and **resilience validated through live failure injection** -- killing Postgres, killing ingestion mid-tick, a full `az aks stop`/`start` cycle, a complete cluster delete-and-recreate, and redeploying mid-CronJob-run (see [Resilience / Restart Testing](#resilience--restart-testing))

This isn't a "Kind-only, cloud-aspirational" project -- it deploys to and has been live-tested on **real Azure Kubernetes Service**, with images built and pushed to a real Azure Container Registry, not just a local cluster. The same manifests and scripts work on Kind for free local development and on AKS for real cloud validation.

---

## Troubleshooting

### 1. Frontend loads but login fails
Possible cause:
- Database migrations or seed data did not run

Fix:
- Ensure deployment script completed successfully
- Re-run migrations and seeding if necessary

```bash
kubectl exec -it deployment/backend -n quantpulse -- alembic upgrade head
kubectl exec -it deployment/backend -n quantpulse -- python -m app.database.seed
```

### 2. Grafana opens but dashboard has no data
Possible causes:
- Prometheus port forwarding not running
- Prometheus datasource not provisioned
- Dashboard provisioning misconfigured

Fix:
- Start/restart `./scripts/port-forward.sh`
- Verify Prometheus is reachable at `http://localhost:9090`
- Check Grafana provisioning ConfigMaps

### 3. Prometheus query fails
Possible cause:
- Backend target not being scraped

Fix:
- Open Prometheus and run:

```promql
up
```

Expected result should include:

```text
up{instance="backend:8000", job="quantpulse-backend"} 1
```

### 4. Ingress creation fails during setup
Possible cause:
- Ingress controller admission webhook is not ready yet

Fix:
- Wait until ingress-nginx controller pod is fully ready before applying ingress resources
- Re-run deployment after readiness is confirmed

### 5. Port forwarding stops working
Possible cause:
- The terminal session was closed

Fix:
- Restart:

```bash
./scripts/port-forward.sh
```

Or run both commands manually in separate terminals.

---

## Future Improvements

Deploying to real Azure AKS and CI/CD via GitHub Actions are both done, not future items -- see [Deployment Scripts](#deployment-scripts) and the repo's own `.github/workflows/`. What's genuinely still open:

- Add Helm charts as an alternative to the current Kustomize-based deployment
- Enforce role-based access control -- `users.role` already exists in the schema (seeded as `admin`) but nothing currently checks it; every authenticated user can hit every endpoint today
- Persist Grafana's own state (alert rules, user preferences created via its UI) with a volume -- the dashboard itself already survives a restart fine, since it's provisioned from a ConfigMap, not hand-edited
- Add Prometheus/Grafana alert rules on top of the metrics that already exist (`kube-state-metrics` is already in place specifically to enable CronJob-failure alerting, just not wired to an actual alert yet)
- Add distributed tracing to complement the request-rate/latency metrics that already exist
- Azure Key Vault (or similar) for secrets instead of plain Kubernetes Secrets
- Horizontal pod autoscaling for the backend
- HTTPS -- deliberately parked, not forgotten: no public ingress/LoadBalancer is deployed at all right now (everything's reached via `kubectl port-forward`), so there's no public plain-HTTP traffic to protect yet. The hard rule for later: never add a public ingress without HTTPS in the same move.

---

## Mermaid Diagram Sources

The PNG diagrams in `docs/diagrams/` can be backed by the following Mermaid source code.

### 1. Architecture Diagram

```mermaid
flowchart TB
    User[User Browser]

    subgraph LocalHost[Local Development Machine]
        Docker[Docker Engine]
        Kind[Kind Kubernetes Cluster]
        Docker --> Kind
    end

    subgraph QuantPulse[Kubernetes Namespace: quantpulse]
        Ingress[NGINX Ingress]
        FrontendService[Frontend Service]
        Frontend[React Frontend / NGINX Container]
        BackendService[Backend Service]
        Backend[FastAPI Backend]
        PostgresService[PostgreSQL Service]
        Postgres[(PostgreSQL StatefulSet)]
        PromService[Prometheus Service]
        Prometheus[Prometheus]
        GrafanaService[Grafana Service]
        Grafana[Grafana]

        Ingress -->|/| FrontendService
        Ingress -->|/api| BackendService
        FrontendService --> Frontend
        Frontend -->|REST API| BackendService
        BackendService --> Backend
        Backend -->|SQLAlchemy| PostgresService
        PostgresService --> Postgres
        Prometheus -->|Scrape /metrics| BackendService
        PromService --> Prometheus
        Grafana -->|PromQL queries| PromService
        GrafanaService --> Grafana
    end

    User -->|http://localhost| Ingress
    User -->|localhost:3000| GrafanaService
    LocalHost --> QuantPulse
```

### 2. Deployment Workflow Diagram

```mermaid
flowchart TD
    A[cleanup.sh] --> B[Delete existing Kind cluster]
    B --> C[setup-kind.sh]
    C --> D[Create Kind cluster]
    D --> E[Install ingress-nginx]
    E --> F[Wait for ingress readiness]
    F --> G[deploy-kind.sh]
    G --> H[Build backend image]
    H --> I[Build frontend image]
    I --> J[Load images into Kind]
    J --> K[Apply Kubernetes manifests]
    K --> L[Wait for pods]
    L --> M[Run Alembic migrations]
    M --> N[Seed database]
    N --> O[port-forward.sh]
    O --> P[Prometheus :9090]
    O --> Q[Grafana :3000]
    N --> R[QuantPulse :80]
```

### 3. Database Initialization Diagram

```mermaid
flowchart TD
    A[PostgreSQL Pod Ready] --> C[Alembic Upgrade Head]
    B[Backend Pod Ready] --> C
    C --> D[Create Database Schema]
    D --> E[Run Seed Module]
    E --> F[Create Default User]
    E --> G[Seed Active Symbols]
    F --> I[QuantPulse Login Ready]
    G --> I
```

### 4. Monitoring Flow Diagram

```mermaid
flowchart LR
    User[Developer / Reviewer] --> Grafana[Grafana Dashboard]
    Grafana -->|Queries Prometheus| Prometheus[Prometheus]
    Prometheus -->|Scrapes| Metrics[/metrics endpoint/]
    Backend[FastAPI Backend] --> Metrics
```

### 5. Cold-Start Validation Diagram

```mermaid
flowchart TD
    A[Cold Start 1] --> B[Found frontend image and Grafana provisioning issues]
    B --> C[Added image loading and fixed ConfigMaps]
    C --> D[Cold Start 2]
    D --> E[Found misplaced dashboard JSON and ingress timing]
    E --> F[Reorganized files and added deployment automation]
    F --> G[Cold Start 3]
    G --> H[Found missing migrations and seed data]
    H --> I[Automated Alembic and database seeding]
    I --> J[Cold Start 4]
    J --> K[Zero-intervention deployment passed]
```

---

## Author

**Shreyas Dhanvantari**  
Master's Graduate in Electrical and Computer Engineering  
Ontario Tech University

If this project is being reviewed for internships, co-op, or entry-level software/cloud roles, it demonstrates practical experience in:
- Full-stack development
- Kubernetes deployment
- Monitoring and observability
- Debugging distributed systems
- Deployment automation
- Cold-start validation and reliability improvement
