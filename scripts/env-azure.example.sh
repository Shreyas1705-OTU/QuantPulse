#!/bin/bash
#
# Template for the env vars deploy-aks.sh needs to auto-provision
# finnhub-secret and azure-openai-secret on a fresh cluster (see the
# "Azure OpenAI is enrichment, not core functionality" comment in
# deploy-aks.sh for why the Azure OpenAI ones are optional and the
# Finnhub one is required).
#
# This file is a template ONLY -- it holds no real values and is safe to
# commit. To actually use it:
#
#   cp scripts/env-azure.example.sh scripts/.env.azure
#   # edit scripts/.env.azure, fill in the real values below
#   source scripts/.env.azure
#   ./scripts/deploy-aks.sh
#
# scripts/.env.azure is already covered by .gitignore's ".env.*" rule --
# it can never be accidentally committed. Never fill these values in
# directly in THIS file (env-azure.example.sh); it's tracked in git.

export FINNHUB_API_KEY='your-finnhub-key-here'

export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com/openai/v1'
export AZURE_OPENAI_API_KEY='your-azure-openai-key-here'
export AZURE_OPENAI_DEPLOYMENT='your-deployment-name-here'
