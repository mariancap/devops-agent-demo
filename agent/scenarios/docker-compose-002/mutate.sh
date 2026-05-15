#!/bin/bash
# Scenariu docker-compose-002: condition: service_healthy → condition: service_fast (enum invalid)
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația docker-compose-002..."
sed -i 's/condition: service_healthy/condition: service_fast/' "$REPO_ROOT/docker-compose.yml"
echo "✅ Mutație aplicată: service_healthy → service_fast"
