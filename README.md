# QuantPulse

**QuantPulse** is a real-time market monitoring platform: it ingests live trade data for equities, forex, and crypto, runs a rolling anomaly detector over it, layers AI-generated insight on top via Azure OpenAI, and pushes all of it live to a React dashboard — deployed identically to a local Kind cluster and a real Azure Kubernetes Service cluster.

It started as something else entirely — a fake IoT-device monitoring demo called **CloudPulse** — and was pivoted into what it is now. That journey (what changed, why, and what broke along the way) is documented in full below, because the process is as much the point of this project as the final result.

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
- [Development History: From CloudPulse to QuantPulse](#development-history-from-cloudpulse-to-quantpulse)
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
- [Why This Project Is Cloud-Native](#why-this-project-is-cloud-native)
- [Troubleshooting](#troubleshooting)
- [Future Improvements](#future-improvements)
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

## Development History: From CloudPulse to QuantPulse

This project did not start as a market-data platform. It began as **CloudPulse**, an entirely different demo, and was deliberately pivoted. This section is the real build log — what existed before, what changed, and the actual bugs hit at each stage — not a cleaned-up summary.

### Origin: CloudPulse

CloudPulse was a cloud-native **IoT device-monitoring** portfolio project, not connected to any real data source. Its data model was `User`, `Device`, `Reading`, and `Alert`, with alert thresholds hardcoded in a `ReadingService` (temperature > 35, humidity < 20, battery < 20). Its "live" data came from a fake random-number generator (`simulator/`) standing in for connected devices — there was no external feed of any kind. The stack was already close to today's: FastAPI + SQLAlchemy + Pydantic + Alembic + Uvicorn on the backend, React + Vite + NGINX on the frontend, Postgres, Docker, and Kubernetes via Kind — but Redis, CI/CD, Azure AKS/ACR, and any real external data source did not exist yet.

What CloudPulse did have was deployment discipline: four rounds of deliberate **cold-start testing** — tear the Kind cluster down, deploy from nothing, fix whatever broke — until `cleanup.sh → setup-kind.sh → deploy-kind.sh → port-forward.sh` was a genuinely repeatable, zero-intervention flow. That discipline is the one thing carried forward unchanged into every phase of QuantPulse.

### The Pivot Plan

The decision was made to rebrand CloudPulse into a real-time, AI-assisted market monitoring platform, while keeping the cold-start deployment discipline that made the original reliable. A 5-phase plan was set:

1. Prove the deployment pipeline on **real Azure AKS/ACR**, using the *existing* pre-pivot app, before writing a single line of new feature code.
2. Finnhub ingestion + rename the data model (`Device`→`Symbol`, `Reading`→`Tick`).
3. Anomaly detection + an LLM explanation/summary layer.
4. Frontend redesign.
5. Repository cleanup and polish.

The reasoning for doing the cloud migration *first*: every feature built after that point would ship with its own Dockerfile and Kubernetes manifest from day one, rather than "build it locally, bolt the cloud on later" — the exact anti-pattern the cold-start discipline existed to prevent. This also meant setting up a real Azure account (Standard Free tier, $200/30-day credit) with a budget alert configured before any resource existed, and adopting a hands-on execution style that held for the rest of the early project: every command run by hand, one step verified before the next.

### Session 1 — Proving the Pipeline on Real Azure

The first real Azure session hit a run of infrastructure bugs that Kind's local environment had never surfaced, because Kind doesn't have real cloud storage, real quota limits, or real multi-service race conditions:

- **No x86 compute quota on a brand-new subscription.** The first AKS creation attempt failed outright on `Standard_B2s` (x86) — a fresh subscription's starter quota only allowed ARM64 VM families or very expensive specialty instances. The fix was switching to `Standard_B2ps_v2` (ARM64), which meant every image from that point on had to be built for `linux/arm64` via `docker buildx` and QEMU emulation.
- **A Kustomize "cycle detected" error.** The AKS overlay was originally nested inside the `k8s/` base it needed to extend via a relative path back out — a real Kustomize limitation. Fixed by moving `overlays/` out to the repo root as a sibling of `k8s/`.
- **Postgres reported "Ready" before it was.** The StatefulSet had no readiness probe, so `kubectl wait` was satisfied the instant the container process started, not when Postgres had actually finished initializing — a race that Kind's instant local storage never exposed, but Azure Disk's real provisioning delay did.
- **Azure Disk's `lost+found` broke `initdb`.** Once a probe was added, Postgres crash-looped instead: Azure Disk leaves a `lost+found` directory at the root of a freshly provisioned volume, and `initdb` refuses to initialize into a non-empty directory. Fixed by pointing `PGDATA` at a subdirectory of the mount.
- **`$(VAR_NAME)` substitution silently fails inside probes.** The new readiness probe itself then failed with `role "root" does not exist` — Kubernetes' `$(VAR)` substitution works in a container's main command/args but not reliably inside a probe's `exec.command`. Fixed by hardcoding the literal username.

The session ended with a full deploy verified end-to-end on real AKS via a real browser login — still running the pre-pivot, fake-device version of the app. The point of this session was proving the pipeline would hold up on real cloud infrastructure, not the product itself.

### Session 2 — CI, the Full Rebrand, and Real Market Data

With the pipeline proven, this session added GitHub Actions CI (build + push to ACR on every push to `main`; deploy-to-AKS deliberately stayed manual to protect the stop/start cost discipline), then did the **full CloudPulse → QuantPulse rebrand** in one pass — 44 files renamed and rewritten — rather than deferring it to the final cleanup phase.

- **A rename that looked complete but silently broke the frontend build.** A content-only `sed` pass doesn't rename files — `cloudpulseService.js` kept its old filename even as every file importing it was rewritten to expect a "quantpulseService" that didn't exist. A grep for the *old* name came back clean, which was a false negative: the old name genuinely wasn't referenced anymore, it just masked that the new import was already broken. Fixed by properly recreating the file under its new name.
- **A second dangling import outside the searched directory.** `alembic upgrade head` then failed on an import for the now-deleted `Device` model — the earlier verification grep was scoped to `backend/app/` only, and `backend/alembic/env.py` lives just outside it. Fixed, then re-grepped the whole of `backend/`, not just the subdirectory.
- **Rebuilt images that never actually redeployed.** Even after every fix, a running pod kept serving the old broken behavior across full rebuild cycles. Root cause: `kubectl apply` only restarts a pod when the Deployment's own YAML text changes, and with the image tag always `:latest`, a rebuilt image looked byte-identical to `kubectl` no matter what changed inside it. Fixed by adding an unconditional `kubectl rollout restart` after every apply — a fix that mattered well beyond this one bug, since it would otherwise have silently affected every future code change.

With the rebrand done, real Finnhub ingestion replaced the fake simulator: the data model became `Symbol`/`Tick` (keeping both `traded_at` and `created_at`, a deliberate improvement synthetic data never needed), and ingestion was built as its own service — own Dockerfile, own Deployment, hard single-replica constraint to avoid duplicate-inserting trades.

- **A cold-start race that only existed on a truly fresh cluster.** On Kind, ingestion always worked because that cluster already had leftover schema from earlier runs. On a genuinely fresh AKS cluster, every Deployment starts at once — ingestion tried to read the `symbols`/`ticks` tables before the Alembic migration step had created them. Fixed with retry-with-backoff inside ingestion itself, rather than trying to force a particular script ordering.

The session ended with real, live Finnhub market data (confirmed real BINANCE:BTCUSDT trades) flowing end-to-end on both Kind and a genuinely cold AKS cluster.

### Rounding Out the Pivot: AI Layer, Frontend Redesign, Test Suite

The remaining phases of the original pivot plan followed: a rolling z-score anomaly detector feeding real `Alert` rows; three Azure OpenAI-powered jobs (per-alert explanations, a daily digest, a continuously refreshing per-symbol summary); and a full dark-editorial frontend redesign, verified end-to-end on real AKS and then explicitly design-locked — no further visual changes without being asked again. SPY was dropped entirely after real tick-count data showed Finnhub's free tier barely streamed it, and replaced with OANDA:USD_CAD.

Real bugs found in this stretch: a new CronJob manifest that existed on disk but was never added to `kustomization.yaml`, so it silently never deployed to AKS (Kind's wildcard `kubectl apply -f` masked the same gap); and a truncated Azure OpenAI key (21 characters against a real 84) that was silently causing every AI call to fail authentication, caught by diff-checking key length against the real Azure value.

This stretch closed with the first fully automated safety net for the project: a **79-test suite** run against a real Postgres instance (not mocks), gating CI so a broken image can't get built and pushed in the first place.

### Phase 2 — Redis: Real-Time Push and Caching

With the pivot complete and a real test suite in place, a fresh 6-phase roadmap started for the next stage of the project (this numbering is separate from — and comes after — the 5-phase pivot plan above). Phase 2 added a live WebSocket push path — ingestion publishes every tick/alert to Redis the instant it's written, and a backend endpoint relays it to any open browser connection, replacing a flat 5-second polling loop — plus a cache-aside layer in front of the hottest read endpoints.

An adversarial automated code review (`/code-review ultra`) surfaced 10 real concurrency, security, and resource-lifecycle bugs that manual testing had missed: a synchronous DB call blocking the WebSocket event loop for every connection during every handshake; WebSocket auth that never re-validated after the initial connection; a missing socket timeout on the async Redis client; a frontend reconnect loop that retried forever even after an explicit auth rejection; no circuit breaker on Redis publish, so an outage meant every trade paid a multi-second timeout in the live ingestion loop; cleanup code that could itself raise mid-cleanup and skip remaining steps; a malformed cached value crashing the request instead of falling back to Postgres; Redis's default rolling-update strategy risking split publishers/subscribers across old/new pods during a deploy; double-validated cache-miss data; and a React timer never cleared on unmount. Every one of these was fixed and then proven live — for example, deleting a connected user's session mid-stream to confirm the WebSocket cut off within its documented window, and scaling Redis to zero during live trading to confirm the circuit breaker held.

A real process mistake happened here too: a PR was merged before confirming its fix commit had actually been pushed, briefly landing all 10 unfixed bugs back on `main`. It was recovered cleanly, but it produced a permanent rule that's held ever since: always diff the local and remote branch SHA directly before any merge, never infer a push happened from how the conversation went.

### Phase 3 — Real Grafana/Prometheus Dashboards

The dashboard had been 100% generic process metrics despite real application metrics already being scraped since Phase 2. Replaced with 15 real panels — alerts by severity, cache hit rate, active WebSocket connections, request rate and p95 latency labeled by route template to keep cardinality bounded, and CronJob success/failure via a newly added `kube-state-metrics` deployment with RBAC scoped to exactly what it needed. A `redis_exporter` was added for real Redis process metrics. Live testing on AKS also caught a real deploy-pipeline gap: neither deploy script restarted Prometheus or Grafana on a ConfigMap-only change, so a redeploy could silently leave both serving stale configuration — fixed in both scripts.

### Phase 4 — Resilience and Restart Testing

A runbook documenting five real failure-injection scenarios — killing Postgres, killing ingestion mid-tick, an `az aks stop`/`start` cycle, a full delete-and-recreate, and redeploying mid-CronJob-run — paired with a snapshot/diff tool that observes cluster and data state without ever changing it. Every scenario recovered as expected: ingestion survived a Postgres kill with zero restarts, exactly one replacement pod ever appeared after killing ingestion itself, pods resumed in-place after an AKS stop/start cycle, both Kind and a real AKS cluster survived a full delete-and-recreate, and an in-flight CronJob run finished untouched by a concurrent redeploy.

### Phase 5 — Clone-Readiness Re-Check

A fresh look at whether someone cloning the repo cold could actually get it running found one real gap: the Kind Quick Start never mentioned the required `FINNHUB_API_KEY`, even though the deploy script hard-requires it. Fixed, then proven with a full delete-and-recreate on both Kind and AKS from a completely fresh state, using only the documented steps.

### Phase 6 — Repo Cleanup and Documentation

The README's stale pre-rebrand language — the opening tagline, project overview, and key features, all of which had survived since the CloudPulse era — was rewritten to reflect the real project. A later full re-read still caught two more leftover references (an architecture line describing Postgres as storing "devices, readings...", and a diagram whose nodes referenced sample devices) — both fixed.

### Final Review Round, Merge, and Closing Out

Before merging the accumulated Phase 3–6 work, a second comprehensive automated review found 8 more real issues — most notably a Redis metrics sidecar whose failure could have taken the entire Redis Service down, since Kubernetes' Pod-Ready gate is the AND of every container's readiness in a pod. Fixed by moving the exporter into its own separate Deployment. Also fixed: unbounded metric cardinality on unmatched routes, failed (500) requests that were invisible to the very metrics meant to catch them, and a residual version of the resilience tool's own false-alarm bug. Every fix was live-verified the same way as Phase 2's round, including deliberately triggering a real 500 error to confirm it then showed up in the metrics.

A third, whole-codebase review was attempted afterward but ran into the review tool's own hard size limit on a true whole-repository diff. Given that Phase 2 and the Phase 3–6 work had each already received a comprehensive review, and this project's actual purpose is a portfolio/interview demonstration rather than a production system under sustained load, that third pass was closed without merging rather than chased further — a deliberate scope decision, not an unresolved problem.

**What this history adds up to:** a fake IoT-device simulation, hardened through four rounds of cold-start testing before a single real feature existed, became a real-time market monitoring platform — live Finnhub ingestion, a rolling anomaly detector, three Azure OpenAI-powered insight jobs, live WebSocket push with Redis pub/sub, cache-aside reads, a real observability stack, a documented and live-proven resilience posture — deployed identically to a free local cluster and a real Azure cloud environment, both proven from a genuinely cold start.

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

QuantPulse runs as a multi-service application inside a **Kind Kubernetes cluster** on a local development machine, or an equivalent namespace on **Azure Kubernetes Service**.

**Architecture summary:**
- The **user browser** accesses QuantPulse through **NGINX Ingress** at `http://localhost`
- The **frontend service** serves the React application through an NGINX container
- The **backend service** exposes a FastAPI REST API, a live-push WebSocket endpoint, and a `/metrics` endpoint
- **PostgreSQL** stores symbols, ticks, alerts, users, and AI-generated summaries
- **Redis** carries pub/sub events for live push and serves cache-aside reads on hot endpoints
- **Prometheus** scrapes backend, ingestion, kube-state-metrics, and redis_exporter targets
- **Grafana** queries Prometheus and displays observability dashboards

---

## System Screenshots

All four captured live from a real cold-started Kind cluster, real Finnhub crypto/forex data streaming in (equities were closed at capture time, hence the "markets closed" banner and "No data yet" equity rows — that's the app correctly reflecting real NYSE market hours, not a bug).

### Login Page

<img width="1600" alt="QuantPulse login page" src="docs/screenshots/login.png" />

### Main Application Dashboard

<img width="1600" alt="QuantPulse dashboard with live crypto/forex ticks, alerts, and AI insight cards" src="docs/screenshots/dashboard.png" />

### Prometheus Query Validation

The screenshot below shows the `up` query returning all four real scrape targets — backend, ingestion, kube-state-metrics, and redis-exporter.

<img width="1600" alt="Prometheus up query showing all four scrape targets healthy" src="docs/screenshots/prometheus.png" />

### Grafana Monitoring Dashboard

The full 15-panel QuantPulse-specific dashboard described in [Monitoring and Observability](#monitoring-and-observability), rendered with real data from the same live cluster.

<img width="1600" alt="Full Grafana QuantPulse monitoring dashboard with all 15 panels" src="docs/screenshots/grafana.png" />


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

QuantPulse supports a structured deployment flow using scripts.

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
Four scrape targets, every 5s: the backend and ingestion services' own `/metrics` endpoints, plus `kube-state-metrics:8080` and `redis-exporter:9121`. `redis_exporter` runs as its own Deployment rather than a sidecar on the Redis pod — found live via code review that a sidecar ties Kubernetes' Pod-Ready gate (the AND of every container's readiness) to the Redis Service's own endpoints, so a failed exporter image pull would silently take live WS push and caching down too, not just the metrics endpoint.

Example query used during validation:

```promql
up{instance="backend:8000", job="quantpulse-backend"}
```

### Grafana
Grafana is provisioned with:
- A **Prometheus datasource**
- A **pre-configured QuantPulse monitoring dashboard**

The dashboard is QuantPulse-specific, not generic process metrics — ticks ingested and alerts generated were already being scraped since Phase 2, but had zero panels using them until this pass:
- Backend/Redis status, CronJob success rate (top row)
- Ticks ingested rate, active WebSocket connections
- Alerts by severity (HIGH/MEDIUM, from the anomaly detector)
- Cache hit rate (`/ticks/latest`, `/summary/*`)
- Backend request rate + p95 latency, labeled by route template (not raw path, to keep cardinality bounded — see `backend/app/main.py`'s `prometheus_request_metrics` middleware)
- Redis memory usage, ops/sec, connected clients — real process-level metrics from `redis_exporter`, not just the app's own counters
- `ai-explainer`/`ai-daily-summary`/`ai-symbol-summary` job success/failure history, from `kube-state-metrics` (scoped to just `cronjobs`/`jobs` RBAC, not the full generic resource set upstream's own manifests grant)
- Backend CPU/memory, demoted to a small row at the bottom — still useful, just not the whole dashboard anymore

---

## Live Updates & Caching (Redis)

Redis serves two distinct purposes, both independent of each other even though they share the same instance:

**Real-time push (pub/sub).** `ingestion/finnhub_ingestion.py` publishes every tick/alert to a Redis channel (`ticks` / `alerts`) immediately after writing it to Postgres — best-effort, never blocking or failing the write itself if Redis is briefly unreachable. The backend's `WS /api/v1/stream` endpoint (`backend/app/routers/stream.py`) subscribes to those same channels and relays each event straight through to any connected browser tab over a WebSocket. This is what lets the dashboard react to real trade activity as it happens instead of polling on a fixed timer — `frontend/src/services/stream.js` opens the connection and `Dashboard.jsx` reloads (throttled to at most once/sec) whenever something actually arrives, with a much longer interval-based poll kept only as a fallback in case the WS connection is ever down for an extended stretch.

Auth on the socket doesn't go through the usual header-based flow: a browser's native WebSocket API can't set an `Authorization` header on the handshake the way a normal `fetch`/`axios` call can, so the connection is accepted first and the client's first text frame must be `{"token": "<jwt>"}` — validated with the same decode + user lookup every REST endpoint uses. Anything else (timeout, bad token) closes the connection with app-defined WS close code `4401` before ever subscribing to Redis.

**Cache-aside reads.** `GET /ticks/latest` (5s TTL), `GET /summary/today`, and `GET /summary/symbols` (60s TTL) check Redis before hitting Postgres — see `backend/app/core/cache.py`. Pure TTL expiry, not event-driven invalidation: a cached value is simply overwritten on the next miss after it expires, whichever endpoint hits it. Every cache operation degrades silently to "just hit Postgres" on a Redis error, so a Redis outage never takes an endpoint down — only removes the shortcut in front of it.

Redis itself (`redis:7-alpine`) runs with no persistent volume — nothing stored in it is ever the source of truth (Postgres is), so losing it on a restart just means a cold cache and a brief reconnect gap for any open WS clients, never lost data.

**Running locally:** `docker-compose.yml` includes a `redis` service — nothing extra to start. On Kind/AKS it's `k8s/redis/deployment.yaml` + `service.yaml`, deployed automatically by `deploy-kind.sh`/`deploy-aks.sh` alongside everything else.

---

## Automated Test Suite

Real Postgres, not sqlite or mocks — `backend/tests/`, `ingestion/tests/`, and `ai/tests/` each run against an actual Postgres database, since several of the things under test (Postgres's `DISTINCT ON`, real transaction/rollback behavior) don't exist or behave differently against a fake one. Runs in CI (`.github/workflows/build-push-acr.yml`) on every push to `main` that touches app code, gating the image build — `build-and-push` only runs if `test` passes.

**What's covered:**
- `ingestion/tests/test_anomaly_detector.py` — the rolling z-score anomaly detection algorithm itself: threshold classification, cooldown suppression (per-symbol, per-kind), the display-value cap, rolling-window eviction.
- `backend/tests/test_market_hours.py` — `is_market_open()`'s NYSE holiday calendar and DST handling, checked against real calendar facts (actual 2026/2027 holiday dates, actual DST transition dates), not against the module's own internal helpers.
- `backend/tests/test_services.py` — the service layer, including `TickService.get_latest_tick_per_symbol()`'s `DISTINCT ON` tiebreaking.
- `ai/tests/test_explainer.py`, `ai/tests/test_symbol_summary.py` — the two AI CronJob scripts, with the LLM client always monkeypatched (no real Azure OpenAI calls in tests) but every DB read/write real, including the resilience guarantee that one alert's/symbol's failed write or LLM call doesn't sink the rest of the batch.

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

Unlike the automated pytest suite above, this is deliberately user-driven, not automated — the failures (killing Postgres, killing ingestion mid-tick, an `az aks stop`/`start` cycle, a full delete+recreate, redeploying mid-CronJob-run) are injected by hand against a real cluster, one at a time, with the recovery watched and judged live.

`docs/resilience-testing-runbook.md` has the full walkthrough per scenario — what to run, what should happen (grounded in this project's actual code, not a guess), and how to verify it. `scripts/resilience-check.sh` (a thin wrapper around `resilience_check.py`) supports it with two commands that never change cluster state, only observe it:

```bash
./scripts/resilience-check.sh snapshot pre   # before injecting a failure
# ... inject the failure, wait for recovery ...
./scripts/resilience-check.sh diff pre       # after
```

`diff` reports tick count growth since the snapshot, any pod that's still not `Ready`, and any restart count that increased — enough to tell "recovered" from "still broken" without re-deriving it by hand each time.

---

## Why This Project Is Cloud-Native

Yes — QuantPulse follows several cloud-native principles.

### Cloud-native characteristics in this project
- **Containerized services** using Docker — frontend, backend, ingestion, and the AI jobs each get their own image
- **Service decomposition** into frontend, backend, ingestion, three AI CronJobs, Postgres, Redis, and the monitoring stack (Prometheus, Grafana, kube-state-metrics, redis_exporter)
- **Kubernetes orchestration** with declarative manifests — one shared base plus a Kustomize overlay for what actually differs between environments (image registry, pull policy), not two copies of the same YAML
- **Infrastructure automation** with scripts — the same `deploy-kind.sh`/`deploy-aks.sh` pattern deploys either target from one source of truth
- **Observability-first design** with Prometheus, Grafana, kube-state-metrics, and redis_exporter, built on real application metrics (ticks ingested, alerts by severity, cache hit rate, request latency) rather than only generic process stats
- **Stateless application containers** where appropriate — ingestion is the deliberate, documented exception (single-replica by design, not an oversight)
- **Configuration externalization** using ConfigMaps and Secrets
- **Repeatable deployments** validated through cold starts, and **resilience validated through live failure injection** — killing Postgres, killing ingestion mid-tick, a full `az aks stop`/`start` cycle, a complete cluster delete-and-recreate, and redeploying mid-CronJob-run (see [Resilience / Restart Testing](#resilience--restart-testing))

This isn't a "Kind-only, cloud-aspirational" project — it deploys to and has been live-tested on **real Azure Kubernetes Service**, with images built and pushed to a real Azure Container Registry, not just a local cluster. The same manifests and scripts work on Kind for free local development and on AKS for real cloud validation.

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

Deploying to real Azure AKS and CI/CD via GitHub Actions are both done, not future items — see [Deployment Scripts](#deployment-scripts) and the repo's own `.github/workflows/`. What's genuinely still open:

- Add Helm charts as an alternative to the current Kustomize-based deployment
- Enforce role-based access control — `users.role` already exists in the schema (seeded as `admin`) but nothing currently checks it; every authenticated user can hit every endpoint today
- Persist Grafana's own state (alert rules, user preferences created via its UI) with a volume — the dashboard itself already survives a restart fine, since it's provisioned from a ConfigMap, not hand-edited
- Add Prometheus/Grafana alert rules on top of the metrics that already exist (`kube-state-metrics` is already in place specifically to enable CronJob-failure alerting, just not wired to an actual alert yet)
- Add distributed tracing to complement the request-rate/latency metrics that already exist
- Azure Key Vault (or similar) for secrets instead of plain Kubernetes Secrets
- Horizontal pod autoscaling for the backend
- HTTPS — deliberately parked, not forgotten: no public ingress/LoadBalancer is deployed at all right now (everything's reached via `kubectl port-forward`), so there's no public plain-HTTP traffic to protect yet. The hard rule for later: never add a public ingress without HTTPS in the same move.

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
- Taking a project through a real pivot, and cold-start/reliability validation end to end
