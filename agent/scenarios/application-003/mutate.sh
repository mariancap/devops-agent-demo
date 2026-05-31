#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația application-003..."
# primul NOT_FOUND e in getById — al doilea e in updateStatus; schimbam doar primul
sed -i '0,/HttpStatus\.NOT_FOUND, "Task not found"/{s/HttpStatus\.NOT_FOUND, "Task not found"/HttpStatus.BAD_REQUEST, "Task not found"/}' \
  "$REPO_ROOT/src/main/java/com/thesis/demo/controller/TaskController.java"
echo "✅ Mutație aplicată: getById NOT_FOUND → BAD_REQUEST"
