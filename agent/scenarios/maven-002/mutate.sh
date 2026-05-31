#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația maven-002..."
# schimbam scope postgresql din runtime in test => app nu porneste in CI
sed -i '/<artifactId>postgresql<\/artifactId>/{n;s/<scope>runtime<\/scope>/<scope>test<\/scope>/}' "$REPO_ROOT/pom.xml"
echo "✅ Mutație aplicată: postgresql scope runtime → test"
