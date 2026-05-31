#!/bin/bash
# Scenariu docker-compose-004: image: postgres:16-alpine → image: postgres: (ref malformată)
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația docker-compose-004..."
sed -i 's/image: postgres:16-alpine/image: postgres:/' "$REPO_ROOT/docker-compose.yml"
echo "✅ Mutație aplicată: postgres:16-alpine → postgres:"
