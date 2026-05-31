#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația maven-005..."
sed -i 's/<artifactId>spring-boot-starter-web<\/artifactId>/<artifactId>spring-boot-starter-webb<\/artifactId>/' "$REPO_ROOT/pom.xml"
echo "✅ Mutație aplicată: spring-boot-starter-web → spring-boot-starter-webb"
