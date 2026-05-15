#!/bin/bash
# Scenariu docker-compose-001: port host invalid "5432:5432" → "5432:badport"
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația docker-compose-001..."
sed -i 's/"5432:5432"/"5432:badport"/' "$REPO_ROOT/docker-compose.yml"
echo "✅ Mutație aplicată: 5432:5432 → 5432:badport"
