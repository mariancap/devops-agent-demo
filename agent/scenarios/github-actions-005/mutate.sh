#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația github-actions-005..."
sed -i 's/mvnw verify/mvnw verfy/' "$REPO_ROOT/.github/workflows/ci.yml"
echo "✅ Mutație aplicată: mvnw verify → mvnw verfy"
