#!/bin/bash
# Scenariu dockerfile-004: typo in Maven goal package → pakage
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația dockerfile-004..."
sed -i 's/mvnw package/mvnw pakage/' "$REPO_ROOT/Dockerfile"
echo "✅ Mutație aplicată: mvnw package → mvnw pakage"
