#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația mixed-001..."
sed -i 's/EXPOSE 8080/EXPOSE 9090/' "$REPO_ROOT/Dockerfile"
sed -i 's/- "8080:8080"/- "9090:8080"/' "$REPO_ROOT/docker-compose.yml"
echo "✅ Mutație aplicată: EXPOSE 8080→9090 în Dockerfile + port 8080→9090 în docker-compose"
