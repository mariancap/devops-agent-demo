#!/bin/bash
# Scenariu dockerfile-004: COPY --from=builder caută *.war în loc de *.jar
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația dockerfile-004..."
sed -i 's|target/\*.jar|target/*.war|' "$REPO_ROOT/Dockerfile"
echo "✅ Mutație aplicată: *.jar → *.war"
