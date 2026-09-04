#!/bin/bash

set -e

echo "========================================"
echo " Cleaning QuantPulse"
echo "========================================"

echo ""
echo "Deleting Kind cluster..."

kind delete cluster --name quantpulse

echo ""
echo "QuantPulse cluster deleted successfully."
