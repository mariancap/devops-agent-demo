#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația application-002..."
sed -i 's/@ResponseStatus(HttpStatus.CREATED)/@ResponseStatus(HttpStatus.OK)/' \
  "$REPO_ROOT/src/main/java/com/thesis/demo/controller/TaskController.java"
echo "✅ Mutație aplicată: @ResponseStatus CREATED → OK"
