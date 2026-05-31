#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația github-actions-003..."
sed -i 's/DB_HOST: localhost/DB_HOST: wronghost/' "$REPO_ROOT/.github/workflows/ci.yml"
echo "✅ Mutație aplicată: DB_HOST localhost → wronghost"
