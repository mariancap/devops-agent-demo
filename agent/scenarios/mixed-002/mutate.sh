#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația mixed-002..."
sed -i 's/POSTGRES_DB: demo_db/POSTGRES_DB: other_db/' "$REPO_ROOT/docker-compose.yml"
echo "✅ Mutație aplicată: POSTGRES_DB demo_db→other_db în docker-compose"
