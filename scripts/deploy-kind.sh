#!/bin/bash

set -e

# Defense in depth: .env.azure (and any .env* file) is already covered by
# .gitignore and has never been committed, but that only holds until
# someone runs `git add -f`. This catches that case explicitly, before a
# deploy could ever pick up and run with real secrets from a file that's
# supposed to be local-only -- see scripts/env-azure.example.sh.
tracked_env_files=$(git ls-files | grep -E '(^|/)\.env(\..+)?$' || true)
if [ -n "$tracked_env_files" ]; then
    echo "ERROR: the following .env file(s) are tracked by git and must never be:"
    echo "$tracked_env_files"
    echo "Run: git rm --cached <file> for each, then re-run this script."
    exit 1
fi

echo "========================================"
echo " QuantPulse Kubernetes Deployment"
echo "========================================"

echo ""
echo "[1/10] Building backend image..."
docker build -t quantpulse-backend:latest ./backend

echo ""
echo "[2/10] Building frontend image..."
docker build -t quantpulse-frontend:latest ./frontend

echo ""
echo "[3/10] Building ingestion image..."
docker build -t quantpulse-ingestion:latest ./ingestion

echo ""
echo "[4/10] Building ai image..."
docker build -t quantpulse-ai:latest ./ai

echo ""
echo "[5/10] Loading images into Kind..."
kind load docker-image quantpulse-backend:latest --name quantpulse
kind load docker-image quantpulse-frontend:latest --name quantpulse
kind load docker-image quantpulse-ingestion:latest --name quantpulse
kind load docker-image quantpulse-ai:latest --name quantpulse

echo ""
echo "[6/10] Creating namespace and configuration..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# The Finnhub API key is a real external credential, unlike the demo
# secrets above -- never committed to git. Create it here (once) from the
# FINNHUB_API_KEY env var so the deploy stays a single command, without
# ever writing the real key into a tracked file.
if kubectl get secret finnhub-secret -n quantpulse >/dev/null 2>&1; then
  echo "finnhub-secret already exists, leaving it as-is."
else
  if [ -z "$FINNHUB_API_KEY" ]; then
    echo ""
    echo "ERROR: finnhub-secret does not exist yet, and FINNHUB_API_KEY"
    echo "is not set in your shell. Export it first, then re-run:"
    echo ""
    echo "  export FINNHUB_API_KEY='your-key-here'"
    echo ""
    exit 1
  fi

  kubectl create secret generic finnhub-secret \
    --namespace quantpulse \
    --from-literal=FINNHUB_API_KEY="$FINNHUB_API_KEY"
fi

# Azure OpenAI is enrichment, not core functionality (see ai/) -- unlike
# Finnhub above, a missing key does NOT fail the deploy. The two ai
# CronJobs just fail at their next scheduled trigger until this secret
# exists; everything else (ticks, anomaly detection, the dashboard) works
# fine without it.
if kubectl get secret azure-openai-secret -n quantpulse >/dev/null 2>&1; then
  echo "azure-openai-secret already exists, leaving it as-is."
elif [ -n "$AZURE_OPENAI_ENDPOINT" ] && [ -n "$AZURE_OPENAI_API_KEY" ] && [ -n "$AZURE_OPENAI_DEPLOYMENT" ]; then
  kubectl create secret generic azure-openai-secret \
    --namespace quantpulse \
    --from-literal=AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
    --from-literal=AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
    --from-literal=AZURE_OPENAI_DEPLOYMENT="$AZURE_OPENAI_DEPLOYMENT"
else
  echo ""
  echo "WARNING: azure-openai-secret does not exist and AZURE_OPENAI_ENDPOINT/"
  echo "AZURE_OPENAI_API_KEY/AZURE_OPENAI_DEPLOYMENT are not all set. The"
  echo "ai-explainer and ai-daily-summary CronJobs will fail until it's"
  echo "created -- everything else deploys and works normally. To enable"
  echo "them later, export all three and re-run this script, or:"
  echo ""
  echo "  kubectl create secret generic azure-openai-secret -n quantpulse \\"
  echo "    --from-literal=AZURE_OPENAI_ENDPOINT='...' \\"
  echo "    --from-literal=AZURE_OPENAI_API_KEY='...' \\"
  echo "    --from-literal=AZURE_OPENAI_DEPLOYMENT='...'"
  echo ""
fi

echo ""
echo "[7/10] Deploying PostgreSQL..."
kubectl apply -f k8s/postgres/

echo ""
echo "[8/10] Deploying backend, frontend, ingestion, and ai jobs..."
kubectl apply -f k8s/backend/
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/ingestion/
kubectl apply -f k8s/ai/

# kubectl apply only restarts a pod when the Deployment's own YAML text
# changes -- since the image tag here is always ":latest", a rebuilt image
# with new code looks "unchanged" to kubectl even though its content is
# different, so the already-running pod would otherwise keep serving the
# stale image. Force a rollout restart every run so this can't happen.
# (Not needed for k8s/ai/ -- those are CronJobs, not Deployments; each
# scheduled run always pulls/uses whatever image is present at trigger
# time, so there's no stale running pod to restart.)
kubectl rollout restart deployment/backend -n quantpulse
kubectl rollout restart deployment/frontend -n quantpulse
kubectl rollout restart deployment/ingestion -n quantpulse

echo ""
echo "[9/10] Deploying monitoring stack..."
kubectl apply -f k8s/monitoring/prometheus/
kubectl apply -f k8s/monitoring/grafana/

echo ""
echo "[10/10] Deploying ingress..."
kubectl apply -f k8s/ingress/

echo ""
echo "Waiting for deployments..."

kubectl rollout status deployment/backend -n quantpulse
kubectl rollout status deployment/frontend -n quantpulse
kubectl rollout status deployment/ingestion -n quantpulse
kubectl rollout status deployment/prometheus -n quantpulse
kubectl rollout status deployment/grafana -n quantpulse

echo ""
echo "Waiting for PostgreSQL..."

kubectl wait \
  --for=condition=Ready \
  pod/postgres-0 \
  -n quantpulse \
  --timeout=180s

echo ""
echo "Running Alembic migrations..."
kubectl exec deployment/backend -n quantpulse -- alembic upgrade head

echo ""
echo "Seeding database..."
kubectl exec deployment/backend -n quantpulse -- python -m app.database.seed

echo ""
echo "========================================"
echo " QuantPulse deployed successfully!"
echo "========================================"

echo ""
echo "Application URLs"
echo "----------------"
echo "Frontend   : http://localhost"
echo "Prometheus : http://localhost:9090"
echo "Grafana    : http://localhost:3000"

echo ""
echo "QuantPulse Login"
echo "----------------"
echo "Username : shreyas"
echo "Password : Password123"

echo ""
echo "Grafana Login"
echo "-------------"
echo "Username : admin"
echo "Password : admin123"

echo ""
echo "Start port forwarding:"
echo ""
echo "./scripts/port-forward.sh"

echo ""
echo "Current Pod Status"
echo "------------------"
kubectl get pods -n quantpulse

echo ""
echo "QuantPulse deployment completed successfully!"
