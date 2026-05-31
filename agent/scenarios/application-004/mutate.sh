#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația application-004..."
sed -i 's|// POST /api/tasks\n    @PostMapping|// POST /api/tasks\n    @PutMapping|' \
  "$REPO_ROOT/src/main/java/com/thesis/demo/controller/TaskController.java"
# sed -i nu expandeaza \n in pattern; folosim perl
perl -i -0pe 's|// POST /api/tasks\n    \@PostMapping|// POST /api/tasks\n    \@PutMapping|' \
  "$REPO_ROOT/src/main/java/com/thesis/demo/controller/TaskController.java"
echo "✅ Mutație aplicată: @PostMapping → @PutMapping pe create"
