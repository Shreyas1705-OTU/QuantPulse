# Resilience / Cold-Start Testing Runbook

Phase 4 of the post-Phase-1 roadmap. Unlike Phases 1-3, this one is
**user-driven** -- you inject the failures yourself, on a real cluster
(Kind or AKS, your call per scenario), and this doc + `scripts/resilience-check.sh`
exist to make each run fast to execute and unambiguous to judge.

Every "what should happen" below is grounded in this project's actual
code, not a guess -- each entry names the file/mechanism responsible so
a surprising result points you straight at what to go read.

## Before you start

```bash
./scripts/resilience-check.sh snapshot pre
```

Captures tick count, latest tick's age, alert count, symbol_summaries
state, and every pod's status/restart count into `docs/logs/resilience-pre.json`
(gitignored, same as the other session logs). Do this once per scenario,
right before you inject the failure.

After the cluster looks recovered:

```bash
./scripts/resilience-check.sh diff pre
```

Diffs current state against that snapshot and prints a pass/fail-shaped
summary -- tick count growing again, gap duration since the last
pre-failure tick, any pod that's still not Ready, any new restarts.

---

## Scenario 1 -- Kill Postgres

```bash
kubectl delete pod postgres-0 -n quantpulse
```

**What should happen:** `postgres-0` is a StatefulSet pod, so Kubernetes
recreates it with the same name and re-attaches the same PVC -- no data
loss, since Postgres itself wasn't corrupted, just its process. Every
other service loses its DB connection for the outage window:

- **backend**: SQLAlchemy's connection pool raises on the next query;
  FastAPI's own request/response cycle means this surfaces as a 500 to
  whoever's mid-request, not a crash of the backend pod itself.
- **ingestion**: `insert_tick`/`insert_alert` (finnhub_ingestion.py) will
  raise on the write -- **this is not caught**, so a tick landing during
  the exact outage window is dropped, not queued or retried. Ingestion
  itself does NOT crash from this (the exception propagates out of
  `on_message`, which `websocket-client` swallows per-callback), so the
  pod stays up and resumes writing normally once Postgres is back.
- **ai/\* CronJobs**: any job whose scheduled trigger lands inside the
  outage hits `wait_for_schema`'s retry loop (ai/db.py, 10 attempts \*
  3s = 30s budget) -- self-heals on the very next scheduled trigger if
  that budget isn't enough, same as the known cold-start DNS race.

**Verify:** `kubectl get pod postgres-0 -n quantpulse` back to `1/1
Running`, then `resilience-check.sh diff` shows tick count climbing
again. Expect a real gap in `ticks.traded_at` covering the outage --
that's the honest, expected data loss here, not a bug to chase.

---

## Scenario 2 -- Kill ingestion mid-tick

```bash
kubectl delete pod -n quantpulse -l app=ingestion
```

**What should happen:** ingestion **must** run as a single replica (see
the docstring at the top of `finnhub_ingestion.py` and the comment in
`k8s/ingestion/deployment.yaml`) -- Kubernetes replaces the killed pod
with exactly one new one, never two. The new pod:

1. Re-runs `wait_for_schema()` and `load_symbol_map()` from scratch
   (cheap, both just re-query Postgres).
2. Opens a fresh Finnhub WebSocket connection and re-subscribes to every
   symbol -- Finnhub doesn't replay missed trades, so whatever traded
   during the pod's downtime is genuinely gone from `ticks`, permanently.
3. **The anomaly detector's rolling window resets to empty**
   (`AnomalyDetector.__init__`'s `_windows` dict is pure in-process
   memory, never persisted). The new pod needs `WINDOW` fresh ticks per
   symbol before it can flag anomalies again -- a real "cold detection"
   period, not a bug. A trade that would've been a HIGH anomaly one
   minute after restart may go unflagged simply because the window
   hasn't filled yet.
4. The circuit breaker in `publish_event` and Redis pub/sub subscribers
   are unaffected by this -- they don't hold any ingestion-side state
   across the restart.

**Verify:** exactly one ingestion pod post-restart (`kubectl get pods -l
app=ingestion` -- never two), tick ingestion resumes, and don't be
alarmed if alerts go quiet for a bit right after -- that's the cold
window, not a break.

---

## Scenario 3 -- `az aks stop` / `az aks start` cycle

Only meaningful on AKS (Kind has no equivalent power-cycle). You've
already done this operationally multiple times this project -- this
scenario formalizes it as a deliberate test rather than an incidental
side effect of cost control.

```bash
az aks stop --resource-group rg-quantpulse --name aks-quantpulse
# wait for confirmation, then:
az aks start --resource-group rg-quantpulse --name aks-quantpulse
```

**What should happen, from prior live runs:**

- The AKS control plane's own DNS record can take a short while to
  become resolvable again after a start -- seen live as `kubectl` and
  even `az aks show` failing with DNS errors for a stretch immediately
  after `Running` is reported. If this happens **from WSL2 specifically**
  while everything resolves fine from a public resolver (`nslookup
  <hostname> 8.8.8.8`), it's WSL2's own DNS relay being stale, not
  Azure -- a `HOSTALIASES` override or `wsl --shutdown` from Windows
  fixes it; it is not a cluster problem.
- The node itself comes back `NotReady` for a short window before
  flipping `Ready` -- normal kubelet startup, not a failure.
- `ai-explainer`/`ai-daily-summary`/`ai-symbol-summary` CronJob triggers
  landing in the first ~30s after the node's `Ready` can hit the same
  Postgres-DNS cold-start race already covered in the project's own
  history (ai/db.py's 30s retry budget) -- expect at most one `Error`
  pod per job that self-heals on its next trigger, nothing sustained.
- Every Deployment's pods (backend/frontend/ingestion/redis/prometheus/
  grafana/kube-state-metrics) should come back on their own once the
  node is `Ready` -- no manual restart needed for any of them.

**Verify:** `kubectl get nodes` shows `Ready`, `kubectl get pods -n
quantpulse` shows everything `Running` with low restart counts, and
`resilience-check.sh diff` shows ticks resuming.

---

## Scenario 4 -- Full delete + recreate

The most drastic test: prove the cluster can be rebuilt from nothing,
not just recovered from a transient failure. This is also effectively
Phase 5's clone-readiness check exercised early.

```bash
# Kind:
kind delete cluster --name quantpulse
./scripts/setup-kind.sh && ./scripts/deploy-kind.sh

# AKS (destructive -- only do this if you actually mean it):
az aks delete --resource-group rg-quantpulse --name aks-quantpulse --yes
# then recreate the cluster (not currently scripted -- this project's
# az-based cluster creation was a one-time manual setup step; ask before
# treating this as routine)
```

**What should happen:** every Deployment/StatefulSet/CronJob applies
cleanly from the manifests with zero manual intervention beyond the
Finnhub/Azure OpenAI secrets (`deploy-kind.sh`/`deploy-aks.sh` both
create `finnhub-secret` themselves from your shell's `FINNHUB_API_KEY`
env var; `azure-openai-secret` is optional -- its CronJobs just fail
until it exists, everything else works). Postgres starts genuinely
empty -- migrations + seed are both required steps in the deploy
scripts, not optional.

**Verify:** full `deploy-kind.sh`/`deploy-aks.sh` run exits 0, then the
same live battery from Phases 2-3 (real ticks flowing, WS push working,
Grafana panels showing real data) -- this scenario is really "did we
miss documenting a manual step anywhere," and a clean run from scratch
is the only way to know.

---

## Scenario 5 -- Redeploy mid-CronJob-run

```bash
# Watch for a CronJob to be actively running (kubectl get jobs -n quantpulse
# -w, or just catch ai-explainer near one of its 2-minute triggers), then
# immediately:
./scripts/deploy-kind.sh   # or deploy-aks.sh
```

**What should happen:** CronJob-created Jobs are independent of the
Deployments a redeploy touches -- redeploying backend/frontend/ingestion
doesn't touch any in-flight Job pod at all, so an ai-explainer run
already executing should simply finish undisturbed. The risk this
scenario actually tests is narrower than it sounds: does the redeploy
process itself assume anything about CronJob state that a mid-run
CronJob would violate (it shouldn't -- `kubectl apply` on a CronJob spec
doesn't affect already-created Jobs, only future ones).

**Verify:** the in-flight Job completes normally (`kubectl get jobs -n
quantpulse` shows it `Completed`, not `Failed`, not orphaned), and the
redeploy itself completes with its usual exit code.

---

## After a session

Save a final snapshot for the record:

```bash
./scripts/resilience-check.sh snapshot post-session
```

Neither snapshot is git-tracked (`docs/logs/` is gitignored) -- if a run
surfaces something worth keeping, write it up as a proper doc update or
a memory note, not by committing the raw JSON.
