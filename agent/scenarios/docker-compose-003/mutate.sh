#!/bin/bash
# Scenariu docker-compose-003: interval: 5s → interval: abc (durată invalidă)
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația docker-compose-003..."
sed -i 's/interval: 5s/interval: abc/' "$REPO_ROOT/docker-compose.yml"
echo "✅ Mutație aplicată: interval 5s → abc"
