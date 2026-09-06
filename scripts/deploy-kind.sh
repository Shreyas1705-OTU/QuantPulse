#!/bin/bash

set -e

echo "========================================"
echo " QuantPulse Kubernetes Deployment"
echo "========================================"

echo ""
echo "[1/8] Building backend image..."
docker build -t quantpulse-backend:latest ./backend

echo ""
echo "[2/8] Building frontend image..."
docker build -t quantpulse-frontend:latest ./frontend

echo ""
echo "[3/8] Loading images into Kind..."
kind load docker-image quantpulse-backend:latest --name quantpulse
kind load docker-image quantpulse-frontend:latest --name quantpulse

echo ""
echo "[4/8] Creating namespace and configuration..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

echo ""
echo "[5/8] Deploying PostgreSQL..."
kubectl apply -f k8s/postgres/

echo ""
echo "[6/8] Deploying backend and frontend..."
kubectl apply -f k8s/backend/
kubectl apply -f k8s/frontend/

# kubectl apply only restarts a pod when the Deployment's own YAML text
# changes -- since the image tag here is always ":latest", a rebuilt image
# with new code looks "unchanged" to kubectl even though its content is
# different, so the already-running pod would otherwise keep serving the
# stale image. Force a rollout restart every run so this can't happen.
kubectl rollout restart deployment/backend -n quantpulse
kubectl rollout restart deployment/frontend -n quantpulse

echo ""
echo "[7/8] Deploying monitoring stack..."
kubectl apply -f k8s/monitoring/prometheus/
kubectl apply -f k8s/monitoring/grafana/

echo ""
echo "[8/8] Deploying ingress..."
kubectl apply -f k8s/ingress/

echo ""
echo "Waiting for deployments..."

kubectl rollout status deployment/backend -n quantpulse
kubectl rollout status deployment/frontend -n quantpulse
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
