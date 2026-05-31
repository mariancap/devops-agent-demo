#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația application-001..."
sed -i 's|@RequestMapping("/api/tasks")|@RequestMapping("/api/taskz")|' \
  "$REPO_ROOT/src/main/java/com/thesis/demo/controller/TaskController.java"
echo "✅ Mutație aplicată: /api/tasks → /api/taskz"
