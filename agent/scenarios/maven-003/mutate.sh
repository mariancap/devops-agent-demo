#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația maven-003..."
sed -i 's/<java.version>21<\/java.version>/<java.version>99<\/java.version>/' "$REPO_ROOT/pom.xml"
echo "✅ Mutație aplicată: java.version 21 → 99"
