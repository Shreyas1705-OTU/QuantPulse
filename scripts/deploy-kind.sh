#!/bin/bash

set -e

echo "========================================"
echo " CloudPulse Kubernetes Deployment"
echo "========================================"

echo ""
echo "[1/8] Building backend image..."
docker build -t cloudpulse-backend:latest ./backend

echo ""
echo "[2/8] Building frontend image..."
docker build -t cloudpulse-frontend:latest ./frontend

echo ""
echo "[3/8] Loading images into Kind..."
kind load docker-image cloudpulse-backend:latest --name cloudpulse
kind load docker-image cloudpulse-frontend:latest --name cloudpulse

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

echo ""
echo "[7/8] Deploying monitoring stack..."
kubectl apply -f k8s/monitoring/prometheus/
kubectl apply -f k8s/monitoring/grafana/

echo ""
echo "[8/8] Deploying ingress..."
kubectl apply -f k8s/ingress/

echo ""
echo "Waiting for deployments..."

kubectl rollout status deployment/backend -n cloudpulse
kubectl rollout status deployment/frontend -n cloudpulse
kubectl rollout status deployment/prometheus -n cloudpulse
kubectl rollout status deployment/grafana -n cloudpulse

echo ""
echo "Waiting for PostgreSQL..."

kubectl wait \
  --for=condition=Ready \
  pod/postgres-0 \
  -n cloudpulse \
  --timeout=180s

echo ""
echo "Running Alembic migrations..."
kubectl exec deployment/backend -n cloudpulse -- alembic upgrade head

echo ""
echo "Seeding database..."
kubectl exec deployment/backend -n cloudpulse -- python -m app.database.seed

echo ""
echo "========================================"
echo " CloudPulse deployed successfully!"
echo "========================================"

echo ""
echo "Application URLs"
echo "----------------"
echo "Frontend   : http://localhost"
echo "Prometheus : http://localhost:9090"
echo "Grafana    : http://localhost:3000"

echo ""
echo "CloudPulse Login"
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
kubectl get pods -n cloudpulse

echo ""
echo "CloudPulse deployment completed successfully!"
