#!/bin/bash

echo "========================================"
echo " CloudPulse Port Forwarding"
echo "========================================"

echo ""
echo "Starting Prometheus on :9090..."
kubectl port-forward svc/prometheus 9090:9090 -n cloudpulse &
PROM_PID=$!

echo "Starting Grafana on :3000..."
kubectl port-forward svc/grafana 3000:3000 -n cloudpulse &
GRAF_PID=$!

echo ""
echo "Frontend:"
echo "http://localhost"

echo "Prometheus:"
echo "http://localhost:9090"

echo "Grafana:"
echo "http://localhost:3000"

echo ""
echo "Press Ctrl+C to stop port forwarding."

trap "kill $PROM_PID $GRAF_PID" EXIT

wait
