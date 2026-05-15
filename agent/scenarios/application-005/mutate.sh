#!/bin/bash
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
echo "🔴 Aplicând mutația application-005..."
sed -i 's/\.value("Fix pipeline")/.value("Wrong title")/' \
  "$REPO_ROOT/src/test/java/com/thesis/demo/controller/TaskControllerUnitTest.java"
echo "✅ Mutație aplicată: jsonPath expected value Fix pipeline → Wrong title"
