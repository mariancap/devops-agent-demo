#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația maven-004..."
sed -i '/<artifactId>h2<\/artifactId>/{n;s/<scope>test<\/scope>/<scope>runtime<\/scope>/}' "$REPO_ROOT/pom.xml"
echo "✅ Mutație aplicată: h2 scope test → runtime"
