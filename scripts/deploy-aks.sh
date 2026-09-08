#!/bin/bash

set -e

# Defense in depth: .env.azure (and any .env* file) is already covered by
# .gitignore and has never been committed, but that only holds until
# someone runs `git add -f`. This catches that case explicitly, before a
# deploy could ever pick up and run with real secrets from a file that's
# supposed to be local-only.
tracked_env_files=$(git ls-files | grep -E '(^|/)\.env(\..+)?$' || true)
if [ -n "$tracked_env_files" ]; then
    echo "ERROR: the following .env file(s) are tracked by git and must never be:"
    echo "$tracked_env_files"
    echo "Run: git rm --cached <file> for each, then re-run this script."
    exit 1
fi

# All three default to this project's own resources but are overridable,
# so anyone cloning this repo can point the same script at their own
# Azure subscription instead of editing the script itself. See
# scripts/env-azure.example.sh -- copy it to scripts/.env.azure (already
# gitignored), fill in AZURE_RESOURCE_GROUP/AZURE_AKS_CLUSTER/
# AZURE_ACR_NAME with your own resource names, `source` it, then run
# this script. ACR names must be globally unique across all of Azure, so
# a fork genuinely cannot reuse this project's own ACR_NAME even if it
# wanted to.
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-quantpulse}"
AKS_CLUSTER="${AZURE_AKS_CLUSTER:-aks-quantpulse}"
ACR_NAME="${AZURE_ACR_NAME:-quantpulseacrsd}"
ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"

# Deployed by this exact tag, never by the mutable `latest` -- see the
# long comment in overlays/aks/kustomization.yaml for why. `latest` is
# still pushed alongside it purely for convenience (a manual `docker
# pull ...:latest` to poke at an image), but it's never what gets
# deployed. A dirty working tree gets a timestamp appended so repeated
# local iterations each still get a genuinely new tag -- otherwise two
# deploys in a row from the same uncommitted changes would collide on
# the same "-dirty" tag and reintroduce the exact staleness problem a
# real per-deploy tag exists to avoid.
IMAGE_TAG="$(git rev-parse --short HEAD)"
if ! git diff --quiet || ! git diff --cached --quiet; then
  IMAGE_TAG="${IMAGE_TAG}-dirty-$(date +%s)"
fi

echo "========================================"
echo " QuantPulse AKS Deployment"
echo "========================================"
echo ""
echo "Assumes: az login done, and 'az aks start' already run if the"
echo "cluster was stopped (this script does not start/stop the cluster --"
echo "that stays a deliberate manual step to control cost)."

echo ""
echo "[1/9] Pointing kubectl at aks-quantpulse (not Kind)..."
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" --overwrite-existing
kubectl config use-context "$AKS_CLUSTER"

echo ""
echo "[2/9] Logging Docker into ACR..."
az acr login --name "$ACR_NAME"

echo ""
echo "[3/9] Building + pushing backend image (linux/arm64, tag ${IMAGE_TAG})..."
docker buildx build \
  --platform linux/arm64 \
  -t "${ACR_LOGIN_SERVER}/quantpulse-backend:${IMAGE_TAG}" \
  -t "${ACR_LOGIN_SERVER}/quantpulse-backend:latest" \
  --push \
  ./backend

echo ""
echo "[4/9] Building + pushing frontend image (linux/arm64, tag ${IMAGE_TAG})..."
docker buildx build \
  --platform linux/arm64 \
  -t "${ACR_LOGIN_SERVER}/quantpulse-frontend:${IMAGE_TAG}" \
  -t "${ACR_LOGIN_SERVER}/quantpulse-frontend:latest" \
  --push \
  ./frontend

echo ""
echo "[5/9] Building + pushing ingestion image (linux/arm64, tag ${IMAGE_TAG})..."
docker buildx build \
  --platform linux/arm64 \
  -t "${ACR_LOGIN_SERVER}/quantpulse-ingestion:${IMAGE_TAG}" \
  -t "${ACR_LOGIN_SERVER}/quantpulse-ingestion:latest" \
  --push \
  ./ingestion

echo ""
echo "[6/9] Building + pushing ai image (linux/arm64, tag ${IMAGE_TAG})..."
docker buildx build \
  --platform linux/arm64 \
  -t "${ACR_LOGIN_SERVER}/quantpulse-ai:${IMAGE_TAG}" \
  -t "${ACR_LOGIN_SERVER}/quantpulse-ai:latest" \
  --push \
  ./ai

echo ""
echo "[7/9] Applying Kubernetes manifests (namespace, config, postgres,"
echo "backend, frontend, ingestion, ai jobs, monitoring, ingress) via the aks overlay..."
# Not a plain `kubectl apply -k overlays/aks` -- the overlay's images
# section holds the literal placeholders __ACR_LOGIN_SERVER__ and
# __IMAGE_TAG__ (kustomize has no templating of its own), so both are
# substituted in after rendering, right before it's applied. This is what
# lets the same overlay target anyone's ACR via $ACR_NAME instead of only
# this project's own, and deploy by this exact build's tag instead of a
# mutable `latest`.
kubectl kustomize overlays/aks \
  | sed "s|__ACR_LOGIN_SERVER__|${ACR_LOGIN_SERVER}|g; s|__IMAGE_TAG__|${IMAGE_TAG}|g" \
  | kubectl apply -f -

# The Finnhub API key is a real external credential, unlike the demo
# secrets in k8s/secret.yaml -- never committed to git. Create it here
# (once) from the FINNHUB_API_KEY env var, same as deploy-kind.sh.
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
  echo "created -- everything else deploys and works normally."
  echo ""
fi

echo ""
echo "Waiting for deployments..."

kubectl rollout status deployment/backend -n quantpulse
kubectl rollout status deployment/frontend -n quantpulse
kubectl rollout status deployment/ingestion -n quantpulse
kubectl rollout status deployment/prometheus -n quantpulse
kubectl rollout status deployment/grafana -n quantpulse

echo ""
echo "[8/9] Waiting for PostgreSQL..."

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
echo "[9/9] Done."
echo ""
echo "========================================"
echo " QuantPulse deployed to AKS successfully!"
echo "========================================"

echo ""
echo "No ingress controller / LoadBalancer is installed on this cluster yet"
echo "(deliberately deferred to avoid its recurring cost -- see project notes)."
echo "The Ingress resource was applied but has nothing serving it. Use:"
echo ""
echo "  kubectl port-forward svc/frontend 8080:80 -n quantpulse"
echo "  kubectl port-forward svc/prometheus 9090:9090 -n quantpulse"
echo "  kubectl port-forward svc/grafana 3000:3000 -n quantpulse"
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
echo "Current Pod Status"
echo "------------------"
kubectl get pods -n quantpulse -o wide

echo ""
echo "Reminder: run 'az aks stop --resource-group ${RESOURCE_GROUP} --name ${AKS_CLUSTER}'"
echo "when you're done validating, to stop paying for the node while idle."
