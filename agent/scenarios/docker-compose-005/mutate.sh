#!/bin/bash
# Scenariu docker-compose-005: retries: 5 → retries: -1 (valoare negativă invalidă)
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația docker-compose-005..."
sed -i 's/retries: 5/retries: -1/' "$REPO_ROOT/docker-compose.yml"
echo "✅ Mutație aplicată: retries 5 → -1"
