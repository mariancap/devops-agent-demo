#!/bin/bash
# Scenariu dockerfile-005: USER appuser → USER root (hadolint DL3002)
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația dockerfile-005..."
sed -i 's/^USER appuser$/USER root/' "$REPO_ROOT/Dockerfile"
echo "✅ Mutație aplicată: USER appuser → USER root"
