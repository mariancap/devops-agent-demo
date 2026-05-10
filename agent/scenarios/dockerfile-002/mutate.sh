#!/bin/bash
# Scenariu dockerfile-002: COPY → ADD (hadolint DL3020)
# hadolint preferă COPY în locul ADD când nu e nevoie de extracție arhivă
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația dockerfile-002..."
sed -i 's/^COPY /ADD /g' "$REPO_ROOT/Dockerfile"
echo "✅ Mutație aplicată: COPY → ADD"
