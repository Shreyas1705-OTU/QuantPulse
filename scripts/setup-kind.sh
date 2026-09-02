#!/bin/bash

set -e

echo "========================================"
echo " CloudPulse Kind Cluster Setup"
echo "========================================"

echo ""
echo "[1/3] Creating Kind cluster..."
kind create cluster --config kind-config.yaml --name cloudpulse

echo ""
echo "[2/3] Installing NGINX Ingress..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

echo ""
echo "[3/3] Waiting for ingress-nginx deployment..."

until kubectl get deployment ingress-nginx-controller -n ingress-nginx >/dev/null 2>&1
do
    sleep 2
done

kubectl rollout status deployment/ingress-nginx-controller \
  -n ingress-nginx \
  --timeout=180s

echo ""
echo "Waiting for ingress controller pod..."

kubectl wait \
  --namespace ingress-nginx \
  --for=condition=Ready \
  pod \
  -l app.kubernetes.io/component=controller \
  --timeout=180s

echo ""
echo "========================================"
echo " Kind cluster is ready!"
echo "========================================"

echo ""
kubectl cluster-info

echo ""
kubectl get pods -n ingress-nginx

echo ""
echo "Next step:"
echo "./scripts/deploy-kind.sh"
