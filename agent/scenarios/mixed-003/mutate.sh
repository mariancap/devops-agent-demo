#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația mixed-003..."
sed -i "s/java-version: '21'/java-version: '17'/" "$REPO_ROOT/.github/workflows/ci.yml"
echo "✅ Mutație aplicată: java-version 21→17 în CI (pom.xml cere 21)"
