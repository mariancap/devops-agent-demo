#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația github-actions-004..."
sed -i 's/postgres:16-alpine/postgres:16-alpin/' "$REPO_ROOT/.github/workflows/ci.yml"
echo "✅ Mutație aplicată: postgres:16-alpine → postgres:16-alpin"
