#!/bin/bash

set -e

echo "========================================"
echo " Cleaning CloudPulse"
echo "========================================"

echo ""
echo "Deleting Kind cluster..."

kind delete cluster --name cloudpulse

echo ""
echo "CloudPulse cluster deleted successfully."
