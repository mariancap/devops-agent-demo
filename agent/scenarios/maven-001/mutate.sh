#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația maven-001..."
sed -i 's/<version>3.5.0<\/version>/<version>3.5.999<\/version>/' "$REPO_ROOT/pom.xml"
echo "✅ Mutație aplicată: spring-boot-starter-parent 3.5.0 → 3.5.999"
