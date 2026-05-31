#!/bin/bash
# Scenariu dockerfile-003: typo în Maven goal dependency:go-offline
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația dockerfile-003..."
sed -i 's/dependency:go-offline/dependency:go-ofline/' "$REPO_ROOT/Dockerfile"
echo "✅ Mutație aplicată: go-offline → go-ofline"
