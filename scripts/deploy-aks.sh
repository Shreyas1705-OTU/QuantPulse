#!/bin/bash

set -e

RESOURCE_GROUP="rg-quantpulse"
AKS_CLUSTER="aks-quantpulse"
ACR_NAME="quantpulseacrsd"
ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"

echo "========================================"
echo " QuantPulse AKS Deployment"
echo "========================================"
echo ""
echo "Assumes: az login done, and 'az aks start' already run if the"
echo "cluster was stopped (this script does not start/stop the cluster --"
echo "that stays a deliberate manual step to control cost)."

echo ""
echo "[1/8] Pointing kubectl at aks-quantpulse (not Kind)..."
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" --overwrite-existing
kubectl config use-context "$AKS_CLUSTER"

echo ""
echo "[2/8] Logging Docker into ACR..."
az acr login --name "$ACR_NAME"

echo ""
echo "[3/8] Building + pushing backend image (linux/arm64)..."
docker buildx build \
  --platform linux/arm64 \
  -t "${ACR_LOGIN_SERVER}/quantpulse-backend:latest" \
  --push \
  ./backend

echo ""
echo "[4/8] Building + pushing frontend image (linux/arm64)..."
docker buildx build \
  --platform linux/arm64 \
  -t "${ACR_LOGIN_SERVER}/quantpulse-frontend:latest" \
  --push \
  ./frontend

echo ""
echo "[5/8] Building + pushing ingestion image (linux/arm64)..."
docker buildx build \
  --platform linux/arm64 \
  -t "${ACR_LOGIN_SERVER}/quantpulse-ingestion:latest" \
  --push \
  ./ingestion

echo ""
echo "[6/8] Applying Kubernetes manifests (namespace, config, postgres,"
echo "backend, frontend, ingestion, monitoring, ingress) via the aks overlay..."
kubectl apply -k overlays/aks

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

# Same reasoning as deploy-kind.sh: the image tag here is always ":latest",
# so a freshly-pushed image with new code looks "unchanged" to kubectl and
# won't trigger a pod restart on its own. Force one every run.
kubectl rollout restart deployment/backend -n quantpulse
kubectl rollout restart deployment/frontend -n quantpulse
kubectl rollout restart deployment/ingestion -n quantpulse

echo ""
echo "Waiting for deployments..."

kubectl rollout status deployment/backend -n quantpulse
kubectl rollout status deployment/frontend -n quantpulse
kubectl rollout status deployment/ingestion -n quantpulse
kubectl rollout status deployment/prometheus -n quantpulse
kubectl rollout status deployment/grafana -n quantpulse

echo ""
echo "[7/8] Waiting for PostgreSQL..."

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
echo "[8/8] Done."
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
