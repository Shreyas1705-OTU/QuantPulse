#!/bin/bash

# Thin wrapper around resilience_check.py, for consistency with this
# directory's other entrypoints (deploy-kind.sh, setup-kind.sh, ...).
# The actual logic lives in the .py file -- proper JSON handling
# throughout beats interpolating JSON strings through a second layer of
# shell/python string substitution.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/resilience_check.py" "$@"
