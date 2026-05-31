# Architecture

## Overview

`devops-agent-demo` is a human-in-the-loop agentic system for CI/CD failure remediation.
It combines a Claude Code CLI agent with a custom MCP server, operating on a Spring Boot
application with a GitHub Actions pipeline. The agent autonomously diagnoses pipeline
failures, proposes and validates patches, and commits fixes only after passing two
explicit checkpoints.

## Repository Structure

devops-agent-demo/
├── agent/
│   ├── system_prompt.md          # Interactive mode: full HITL prompting
│   ├── system_prompt_batch.md    # Batch mode: auto-approval at CP1/CP2
│   ├── audit_wrapper.py          # CLI wrapper: launches agent, writes audit log
│   ├── audit_to_results.py       # Converts audit JSONL → results_sdk.jsonl entry
│   ├── schemas/
│   │   └── diagnosis.schema.json # JSON Schema for structured DIAGNOSE output
│   ├── scenarios/
│   │   ├── dockerfile-001/       # One directory per benchmark scenario
│   │   │   ├── mutate.sh         # Injects the failure into the repo
│   │   │   ├── ground_truth.patch# The correct fix as a git patch
│   │   │   └── expected_category.json
│   │   └── ... (28 scenarios total)
│   └── eval_logs/
│       ├── audit_<scenario>_<ts>.jsonl  # Per-run audit log (gitignored)
│       └── results_sdk.jsonl            # Aggregated benchmark results
├── mcp/
│   └── server.py                 # MCP server — 9 tools
├── scripts/
│   └── replay.py                 # ANSI terminal + HTML audit log replay
├── src/                          # Spring Boot application (subject under test)
├── .github/workflows/            # GitHub Actions CI pipeline
├── Dockerfile                    # Multi-stage, non-root, eclipse-temurin:21
├── docker-compose.yml            # App + PostgreSQL with healthchecks
├── report.html                   # Evaluation results report
├── CONCLUSIONS.md                # Thesis conclusions
└── ARCHITECTURE.md               # This file

## Agent Pipeline

The agent follows a strict 8-phase state machine enforced by the system prompt:

INGEST → LOCALIZE → DIAGNOSE → CP1 → PATCH → VALIDATE → CP2 → COMMIT

| Phase    | Description                                                         | MCP Tools Used                        |
|----------|---------------------------------------------------------------------|---------------------------------------|
| INGEST   | Reads CI logs and `error.log` to understand the failure             | `get_job_logs`                        |
| LOCALIZE | Identifies the affected file and line number                        | `get_job_logs`, `run_static_check`    |
| DIAGNOSE | Emits a structured JSON diagnosis validated against a JSON Schema   | `write_audit_event`                   |
| CP1      | Human checkpoint — approves the proposed fix before patching        | `request_approval`                    |
| PATCH    | Applies the fix in an isolated git worktree                         | `apply_patch`, `get_diff`             |
| VALIDATE | Runs static checks + full CI pipeline re-execution via `act`        | `run_static_check`, `run_validation`  |
| CP2      | Human checkpoint — approves the validated diff before committing    | `request_approval`                    |
| COMMIT   | Pushes the fix to an `experiment/<scenario-id>` branch              | (Claude Code native git tools)        |

The agent calls `set_session_context` at every phase transition and
`increment_iteration_counter` after every validation failure. A maximum of 3
PATCH→VALIDATE iterations is enforced per session via `get_iteration_state`.

## MCP Server

`mcp/server.py` exposes 9 tools over the Model Context Protocol (stdio transport):

| Tool                       | Purpose                                                        |
|----------------------------|----------------------------------------------------------------|
| `get_job_logs`             | Returns CI log content and `error.log` for the active scenario |
| `run_static_check`         | Runs hadolint, actionlint, `mvn validate`, `docker compose config` in the worktree |
| `apply_patch`              | Creates/resets the `.patch-worktree` and applies a shell command |
| `get_diff`                 | Returns `git diff` from the worktree for human review          |
| `run_validation`           | Executes `act -j build-and-test` in the worktree               |
| `request_approval`         | Blocks execution and presents a CP1/CP2 approval prompt        |
| `write_audit_event`        | Appends a JSONL event to the session audit log                 |
| `set_session_context`      | Records phase transitions in the session state                 |
| `get_iteration_state`      | Returns current iteration count (max 3 per session)            |
| `increment_iteration_counter` | Increments iteration count after each failed VALIDATE       |
| `reset_iteration_counter`  | Resets counter at session start                                |

## Isolation and Safety

**Git worktree isolation.** All patch operations are performed in `.patch-worktree`,
a git worktree created from the current HEAD. The main working tree is never modified
by the agent. If validation fails, the worktree is reset and the agent retries.

**Branch-per-scenario commits.** Successful fixes are pushed to
`experiment/<scenario-id>` branches, never directly to `develop` or `master`.

**Protected branches.** `master` requires a passing `build-and-test` CI check and
a pull request before any merge. Direct pushes are rejected by GitHub branch protection.

**Audit logging.** Every agent action is recorded in an append-only JSONL audit log
at `agent/eval_logs/audit_<scenario>_<timestamp>.jsonl`. The log captures session
start/end, phase transitions, tool calls, and agent output lines.

## Benchmark Design

Each of the 28 scenarios consists of three files:

- **`mutate.sh`** — a shell script that injects a single reproducible failure into
  the repository (e.g., a typo in a Dockerfile `FROM` tag, a wrong Maven scope,
  an invalid GitHub Actions Java version).
- **`ground_truth.patch`** — the minimal correct fix as a `git diff`-format patch.
- **`expected_category.json`** — metadata: category, subcategory, affected file,
  detection method (static vs. dynamic), and difficulty estimate.

Before each evaluation run, `audit_wrapper.py` applies `mutate.sh` to a clean
checkout, launches the Claude Code agent, and records the full session to a JSONL
audit log. After the session ends, `audit_to_results.py` parses the log and appends
a result record to `agent/eval_logs/results_sdk.jsonl`.

## Failure Categories

| Category       | Count | Mutation Type                                     | Detection Method  |
|----------------|-------|---------------------------------------------------|-------------------|
| dockerfile     | 5     | FROM tag typo, COPY→ADD, USER, Maven goal typo    | Static + Dynamic  |
| docker-compose | 5     | Port invalid, depends_on condition, image tag     | Static + Dynamic  |
| github-actions | 5     | Java version, checkout version, env var, image    | Static + Dynamic  |
| maven          | 5     | Parent version, scope, java.version, dependency   | Dynamic           |
| application    | 5     | Annotation typo, HTTP status, mapping method      | Dynamic           |
| mixed          | 3     | Cross-file inconsistencies (port, DB_NAME, java)  | Dynamic           |

## Technology Stack

| Component         | Technology                                              |
|-------------------|---------------------------------------------------------|
| Agent             | Claude Code CLI + Claude Sonnet 4.6                     |
| MCP Server        | Python 3.12, `mcp` SDK (stdio transport)                |
| Application       | Spring Boot 3.5.0, Java 21 (Temurin), Maven 3.9.9       |
| Database          | PostgreSQL 16 (docker-compose/CI), H2 (Maven tests)     |
| CI Pipeline       | GitHub Actions (`build-and-test` workflow)              |
| Local CI Runner   | `act` CLI (Docker Desktop + WSL2 integration)           |
| Static Analysis   | hadolint, actionlint, `mvn validate`, `docker compose config` |
| Audit Replay      | `scripts/replay.py` (ANSI terminal + dark HTML export)  |
| Environment       | WSL2/Ubuntu 24.04, VS Code, Docker Desktop              |

## Key Design Decisions

**Why a custom MCP server instead of native Claude Code tools?**
A custom MCP server allows precise control over the tool surface exposed to the agent.
By restricting filesystem mutations to `apply_patch` (worktree only) and validation to
`run_validation` (read-only from the agent's perspective), the server acts as a safety
boundary. Native Claude Code bash access would allow unrestricted mutations.

**Why `act` for local CI re-execution?**
Using `act` to replay the exact GitHub Actions workflow locally ensures that the
validation signal is identical to what GitHub CI would produce. An alternative like
`mvn test` would miss Docker-layer failures and docker-compose integration issues.

**Why JSON Schema validation at the DIAGNOSE phase?**
Requiring the agent to emit a schema-validated JSON diagnosis before proceeding to
PATCH ensures the diagnosis is machine-readable and comparable across runs. It also
forces the agent to commit to a specific root cause and affected file before touching
any code, reducing hallucinated or vague patch attempts.

**Why two checkpoints (CP1 and CP2)?**
CP1 (post-diagnosis) allows a human reviewer to reject implausible diagnoses before
any code is modified. CP2 (post-validation) allows review of the actual diff and
CI results before the fix is committed. In production use, these checkpoints would
be surfaced via a notification system; in the benchmark, they are auto-approved.
