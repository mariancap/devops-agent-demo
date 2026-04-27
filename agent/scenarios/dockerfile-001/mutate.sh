#!/bin/bash
# Scenariu dockerfile-001: typo în base image tag
# Mutație: eclipse-temurin:21-jdk-alpine → eclipse-temurin:21-jdk-alpne

set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

echo "🔴 Aplicând mutația dockerfile-001..."
sed -i 's/eclipse-temurin:21-jdk-alpine/eclipse-temurin:21-jdk-alpne/' "$REPO_ROOT/Dockerfile"
echo "✅ Mutație aplicată: 21-jdk-alpine → 21-jdk-alpne"
