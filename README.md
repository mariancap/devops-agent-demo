# devops-agent-demo

> **Agentic CI/CD Remediation with Claude Code**  
> A human-in-the-loop agent that diagnoses and fixes CI/CD pipeline failures in containerised Spring Boot workflows.

Master's thesis project — Marian Capotă, 2026.  
Evaluated on a seeded benchmark of 28 reproducible failure scenarios across 6 categories.

---

## Results at a glance

| System | Success Rate | Notes |
|--------|-------------|-------|
| **Agent (full)** | **96.4% (27/28)** | Claude Sonnet 4.6, HITL |
| B2 Static-only | 50% (3/6) | hadolint + actionlint + mvn validate |
| B1 Zero-shot | 16.7% (1/6) | Agent without structured system prompt |

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Java (JDK) | 21 | [SDKMAN](https://sdkman.io): `sdk install java 21.0.5-tem` |
| Maven | 3.9+ | `sdk install maven 3.9.9` or use `./mvnw` |
| Docker | 24+ | [Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| Python | 3.11+ | System package or `apt install python3` |
| `act` | 0.2.x | [nektos/act](https://github.com/nektos/act): `curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | bash` |
| `gh` CLI | 2.x | [cli.github.com](https://cli.github.com) (optional, for PR workflow) |

**Environment variable required:**

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## One-command setup

```bash
# 1. Clone the repo
git clone https://github.com/mariancap/devops-agent-demo.git
cd devops-agent-demo

# 2. Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Install Python dependencies
make setup

# 4. Verify everything is in order
make check-env

# 5. Run the full benchmark
make bench
```

Results are written to `agent/eval_logs/results_sdk.jsonl`.  
An HTML report is generated at `report.html`.

---

## Running specific targets

```bash
# Smoke test — 3 scenarios, ~5 minutes, low cost
make bench-smoke

# Baseline comparisons only (B1 zero-shot + B2 static)
make bench-baseline

# Regenerate report.html from existing eval logs (no API calls)
make report

# Check prerequisites without running anything
make check-env
```

---

## Project structure

```
devops-agent-demo/
├── Makefile                    # Reproducibility entry point
├── README.md                   # This file
├── requirements.txt            # Pinned Python dependencies
├── report.html                 # Generated benchmark report (dark theme)
├── CONCLUSIONS.md              # 5 key findings + limitations
├── ARCHITECTURE.md             # Full pipeline documentation
├── SUBMISSION.md               # Thesis submission guide
│
├── agent/
│   ├── system_prompt.md        # Agent state machine (8 phases)
│   ├── audit_wrapper.py        # Claude Code CLI wrapper + JSONL audit logging
│   ├── eval_harness_sdk.py     # Benchmark runner (Anthropic SDK)
│   ├── baseline_b1.py          # B1 zero-shot baseline
│   ├── baseline_b2.py          # B2 static-analysis-only baseline
│   ├── report_generator.py     # Generates report.html
│   ├── audit_to_results.py     # Converts audit JSONL → results_sdk.jsonl
│   ├── parse_results.py        # Metrics aggregation + SQLite
│   ├── schemas/
│   │   └── diagnosis.schema.json
│   ├── scenarios/
│   │   ├── dockerfile-001/     # mutate.sh + ground_truth.patch + expected_category.json
│   │   ├── dockerfile-002/
│   │   ├── ... (28 scenarios total)
│   │   └── mixed-003/
│   └── eval_logs/
│       ├── results_sdk.jsonl   # Primary benchmark results
│       ├── baselines_b1.jsonl
│       ├── baselines_b2.jsonl
│       └── *.jsonl             # Per-session audit logs
│
├── mcp/
│   └── server.py               # Custom MCP server (11 tools)
│
├── src/                        # Spring Boot application (Java)
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

---

## Scenario categories

| Category | Scenarios | Example mutation |
|----------|-----------|-----------------|
| `dockerfile` | 001–005 | Invalid base image tag (`21-jdk-alpne`) |
| `docker-compose` | 001–005 | Wrong service name in `depends_on` |
| `github-actions` | 001–005 | Wrong Java version in setup-java |
| `maven` | 001–005 | Wrong Spring Boot parent version |
| `application` | 001–005 | Wrong `@RequestMapping` path |
| `mixed` | 001–003 | Cross-file mutations (Dockerfile + docker-compose) |

Each scenario includes:
- `mutate.sh` — injects the failure into a git worktree
- `ground_truth.patch` — minimal fix verified to restore CI green
- `expected_category.json` — metadata for evaluation scoring

---

## Agent architecture

The agent follows an 8-phase state machine executed via the Anthropic SDK:

```
INGEST → LOCALIZE → DIAGNOSE → CP1 → PATCH → VALIDATE → CP2 → COMMIT
```

Human checkpoints at **CP1** (diagnosis approval) and **CP2** (patch approval) are configurable — in benchmark mode, they are bypassed automatically; in interactive mode, they require explicit human confirmation.

The MCP server (`mcp/server.py`) exposes 11 tools:

| Tool | Purpose |
|------|---------|
| `get_job_logs` | Retrieve CI failure logs |
| `run_static_check` | Run hadolint / actionlint / mvn validate |
| `write_audit_event` | Append to JSONL audit log |
| `request_approval` | Human-in-the-loop checkpoint |
| `run_validation` | Re-run CI pipeline in worktree |
| `apply_patch` | Apply git patch to worktree |
| `get_diff` | Show current worktree diff |
| `get_iteration_state` | Read iteration counter |
| `reset_iteration_counter` | Reset to 0 |
| `increment_iteration_counter` | +1 per validation failure |
| `set_session_context` | Declare phase transitions |

---

## Reproducing thesis results

All numbers in the thesis are derived from files in `agent/eval_logs/`. To reproduce:

```bash
# Reproduce full benchmark from scratch
make bench

# Reproduce baselines only
make bench-baseline

# Regenerate report from committed eval logs (no agent runs needed)
make report
```

Expected output for `make bench`:
- 28 scenarios executed
- ~96% success rate (27/28)
- `agent/eval_logs/results_sdk.jsonl` populated
- `report.html` regenerated

**Note:** Due to LLM non-determinism, individual runs may differ from committed logs. The committed `agent/eval_logs/results_sdk.jsonl` is the authoritative dataset used in the thesis. A clean reproduction using `make bench` should yield results within ±1 scenario of the reported 27/28.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ Yes | Anthropic API key for agent runs |

No other secrets required. All tools (hadolint, actionlint, mvn, act, docker) are invoked locally.

---

## Cost estimate

| Target | API calls | Estimated cost |
|--------|-----------|---------------|
| `make bench-smoke` (3 scenarios) | ~150 | ~$0.10 |
| `make bench-baseline` (6 × B1 + B2) | ~30 | ~$0.02 |
| `make bench` (28 scenarios) | ~800–1200 | ~$0.50–$1.00 |

Model: `claude-sonnet-4-6`. Costs may vary with model pricing changes.

---

## Troubleshooting

**`Permission denied` on `mvnw`:**
```bash
chmod +x mvnw
git add mvnw
git commit -m "restore mvnw executable bit"
```

**`ANTHROPIC_API_KEY not set`:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Or add to ~/.bashrc for persistence
```

**Docker not running (WSL2):**  
Start Docker Desktop on Windows, verify with `docker ps`.

**`act` not found:**  
Static check steps that don't require `act` still work. Install `act` for full CI simulation:
```bash
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | bash
```

**MCP server import errors:**  
```bash
make setup
# or manually:
pip3 install --break-system-packages -r requirements.txt
```

---

## Citation

```bibtex
@mastersthesis{capota2026devops,
  title   = {Agentic CI/CD Remediation with Claude Code: A Human-in-the-Loop System
             for Diagnosing and Fixing Pipeline Failures in Containerised Build Workflows},
  author  = {Capotă, Marian},
  year    = {2026},
  school  = {[University Name]},
  type    = {Master's Thesis}
}
```

---

## License

MIT License. See `LICENSE` for details.
