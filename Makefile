# =============================================================================
# devops-agent-demo — Reproducibility Makefile
# Usage:
#   make setup          Install all Python dependencies
#   make bench          Run full benchmark (all 28 scenarios)
#   make bench-baseline Run B1 (zero-shot) + B2 (static-only) baselines
#   make bench-smoke    Smoke test: 3 scenarios only (fast verification)
#   make report         Regenerate report.html from existing eval logs
#   make clean          Remove generated artifacts (not eval logs)
#   make clean-logs     Remove eval logs (WARNING: destroys benchmark data)
#   make check-env      Verify all prerequisites are installed
# =============================================================================

PYTHON      := python3
PIP         := pip3
AGENT_DIR   := agent
MCP_DIR     := mcp
EVAL_LOGS   := agent/eval_logs
SCENARIOS   := agent/scenarios
REQUIREMENTS := requirements.txt

# Default target
.PHONY: all
all: check-env bench

# ---------------------------------------------------------------------------
# Environment check
# ---------------------------------------------------------------------------
.PHONY: check-env
check-env:
	@echo "=== Checking prerequisites ==="
	@command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
	@command -v java >/dev/null 2>&1 || { echo "ERROR: java not found (need JDK 21)"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found"; exit 1; }
	@command -v mvn >/dev/null 2>&1 || command -v ./mvnw >/dev/null 2>&1 || { echo "ERROR: maven not found"; exit 1; }
	@command -v act >/dev/null 2>&1 || { echo "WARNING: act not found (local CI simulation unavailable)"; }
	@test -n "$$ANTHROPIC_API_KEY" || { echo "ERROR: ANTHROPIC_API_KEY not set"; exit 1; }
	@$(PYTHON) -c "import anthropic" 2>/dev/null || { echo "ERROR: anthropic SDK not installed — run: make setup"; exit 1; }
	@$(PYTHON) -c "import mcp" 2>/dev/null || { echo "ERROR: mcp not installed — run: make setup"; exit 1; }
	@$(PYTHON) -c "import jsonschema" 2>/dev/null || { echo "ERROR: jsonschema not installed — run: make setup"; exit 1; }
	@echo "All prerequisites OK"

# ---------------------------------------------------------------------------
# Dependency installation
# ---------------------------------------------------------------------------
.PHONY: setup
setup:
	@echo "=== Installing Python dependencies ==="
	$(PIP) install --break-system-packages -r $(REQUIREMENTS)
	@echo "=== Setup complete ==="

# ---------------------------------------------------------------------------
# Benchmark targets
# ---------------------------------------------------------------------------

# Full benchmark: all 28 scenarios
.PHONY: bench
bench: check-env
	@echo "=== Running full benchmark (28 scenarios) ==="
	@mkdir -p $(EVAL_LOGS)
	$(PYTHON) $(AGENT_DIR)/eval_harness_sdk.py \
		--log-dir $(EVAL_LOGS)
	@echo "=== Benchmark complete. Results in $(EVAL_LOGS)/results_sdk.jsonl ==="
	$(MAKE) report

# Baseline B1 (zero-shot) + B2 (static-only) on 6 representative scenarios
.PHONY: bench-baseline
bench-baseline: check-env
	@echo "=== Running B2 baseline (static analysis only) ==="
	$(PYTHON) $(AGENT_DIR)/run_baseline_b2.py \
		--out $(EVAL_LOGS)/baselines_b2.jsonl
	@echo "=== Running B1 baseline (zero-shot agent) ==="
	$(PYTHON) $(AGENT_DIR)/run_baseline_b1.py \
		--out $(EVAL_LOGS)/baselines_b1.jsonl
	@echo "=== Baseline runs complete ==="
	$(MAKE) report

# Smoke test: 3 scenarios, fast verification of setup
.PHONY: bench-smoke
bench-smoke: check-env
	@echo "=== Smoke test: dockerfile-001, maven-001, github-actions-001 ==="
	$(PYTHON) $(AGENT_DIR)/eval_harness_sdk.py \
		--scenarios dockerfile-001 maven-001 github-actions-001 \
		--log-dir $(EVAL_LOGS)
	@echo "=== Smoke test complete. Results in $(EVAL_LOGS)/results_sdk.jsonl ==="

# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
.PHONY: report
report:
	@echo "=== Regenerating report.html ==="
	cd . && $(PYTHON) $(AGENT_DIR)/report_generator.py
	@echo "=== report.html updated ==="

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
.PHONY: clean
clean:
	@echo "=== Cleaning generated artifacts ==="
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".patch-worktree" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "=== Clean complete (eval logs preserved) ==="

.PHONY: clean-logs
clean-logs:
	@echo "WARNING: This will delete all benchmark data in $(EVAL_LOGS)!"
	@read -p "Are you sure? [y/N] " ans && [ "$$ans" = "y" ] || exit 1
	rm -f $(EVAL_LOGS)/*.jsonl
	@echo "=== Eval logs removed ==="

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
.PHONY: help
help:
	@echo ""
	@echo "devops-agent-demo — Available targets:"
	@echo "  make setup          Install all Python dependencies"
	@echo "  make check-env      Verify prerequisites"
	@echo "  make bench          Run full benchmark (28 scenarios)"
	@echo "  make bench-baseline Run B1 + B2 baselines (6 scenarios each)"
	@echo "  make bench-smoke    Smoke test (3 scenarios, fast)"
	@echo "  make report         Regenerate report.html"
	@echo "  make clean          Remove __pycache__ and temp files"
	@echo "  make clean-logs     Remove eval logs (DESTRUCTIVE)"
	@echo ""
	@echo "Required env vars:"
	@echo "  ANTHROPIC_API_KEY   Your Anthropic API key"
	@echo ""
	@echo "Docs: README.md"
	@echo ""
