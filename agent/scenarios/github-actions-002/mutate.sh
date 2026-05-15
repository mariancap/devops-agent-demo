#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația github-actions-002..."
sed -i 's/checkout@v4.2.2/checkout@v99.9.9/' "$REPO_ROOT/.github/workflows/ci.yml"
echo "✅ Mutație aplicată: checkout@v4.2.2 → checkout@v99.9.9"
