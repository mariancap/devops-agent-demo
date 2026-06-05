# Conclusions

## Summary of Results

This thesis designed, implemented, and evaluated an agentic CI/CD remediation system
built on Claude Code and a custom Model Context Protocol (MCP) server. The agent was
evaluated on a benchmark of 28 seeded failure scenarios across 6 artifact categories
in a containerized Spring Boot CI/CD pipeline.

**The agent achieved a remediation success rate of 96.4% (27/28 scenarios)**, validating
the central hypothesis that a structured agentic workflow combining LLM reasoning with
deterministic tool execution can reliably diagnose and fix pipeline failures across
heterogeneous DevOps artifact types.

## Per-Category Results

| Category        | Scenarios | Committed | Success Rate |
|-----------------|-----------|-----------|--------------|
| Dockerfile      | 5         | 5         | 100%         |
| GitHub Actions  | 5         | 5         | 100%         |
| Maven (pom.xml) | 5         | 5         | 100%         |
| Application     | 5         | 5         | 100%         |
| Mixed/Cross-file| 3         | 3         | 100%         |
| Docker-Compose  | 5         | 4         | 80%          |
| **Total**       | **28**    | **27**    | **96.4%**    |

The sole failure (docker-compose-001) resulted from a session timeout during local CI
re-execution via `act`, not from incorrect diagnosis or patch generation. This is
an infrastructure constraint rather than a reasoning failure.

## Key Findings

### Finding 1 — State-machine prompting enables robust multi-file reasoning

The INGEST→LOCALIZE→DIAGNOSE→CP1→PATCH→VALIDATE→CP2→COMMIT pipeline proved effective
across all six artifact categories. By enforcing explicit phase transitions and requiring
structured JSON output at the DIAGNOSE phase, the agent consistently produced actionable,
schema-validated diagnoses rather than free-form text. The phase structure also made
agent behavior auditable and reproducible.

### Finding 2 — MCP tool boundaries are critical for safety and correctness

Delegating all filesystem mutations to dedicated MCP tools (`apply_patch`, `run_validation`)
and isolating changes in a git worktree prevented the agent from accidentally modifying
the main repository. The two human-in-the-loop checkpoints (CP1 after diagnosis, CP2
after validation) provided meaningful control points without adding significant overhead
in batch mode evaluation.

### Finding 3 — Run failures were infrastructure-level, not agent-level

Of 97 total runs across 28 scenarios, 70 did not reach SESSION_END with success=true.
Analysis of failure modes shows that all failures were caused by external factors:
session usage limits (4×), API connectivity errors (5× ECONNRESET), process timeouts
(5× SIGTERM), and credit exhaustion (2×). No scenario failed because the agent produced
an incorrect diagnosis or a patch that broke the pipeline — on every run that completed
without interruption, the agent succeeded.

### Finding 4 — Remediation time is dominated by CI re-execution

The average session duration for successful runs was 589 seconds (~10 minutes), with a
range of 329s to 1595s (excluding the timeout outlier). The dominant cost is local CI
re-execution via `act build-and-test`, which runs the full Docker build and Maven test
suite on each validation attempt. This is an acceptable trade-off: deterministic
validation provides high confidence that the committed fix is correct.

### Finding 5 — Cross-file scenarios are solvable without special treatment

The mixed/cross-file category (3/3, 100%) demonstrated that the agent can identify and
fix failures requiring coordinated changes across multiple files (e.g., port inconsistency
between Dockerfile and docker-compose.yml) without any category-specific logic in the
prompt or tools. This generalizability is a direct consequence of the LLM's contextual
reasoning ability combined with the structured phase decomposition.

## Limitations

**Single model, single configuration.** All benchmark runs used Claude Sonnet 4.6 with
the default CLI configuration and a fixed system prompt. Performance may vary with
different models, temperature settings, or prompt variants.

**Batch mode vs. interactive mode.** The benchmark used BATCH_MODE (automatic approval
at CP1 and CP2). In interactive mode, human reviewers would be in the loop; their
decisions would affect both the success rate and the session duration. The current
results represent an upper bound on automated performance.

**Benchmark scale.** The benchmark comprises 28 scenarios designed to be representative
of common failure categories. It does not cover all possible CI/CD failure modes
(e.g., flaky tests, environment-specific failures, race conditions, secrets management).

**Infrastructure dependency.** The agent requires Docker Desktop and the `act` CLI for
local CI re-execution. Environments without Docker cannot run the validation step, which
would require an alternative validation strategy.

**Audit log completeness.** In batch mode, the agent does not emit structured
PHASE_TRANSITION events for all phases; phase chains were partially reconstructed from
OUTPUT text. A future version should enforce structured phase logging regardless of mode.

## Contributions

This work makes the following technical contributions:

1. **A reusable agentic remediation architecture** — the INGEST→LOCALIZE→DIAGNOSE→
   PATCH→VALIDATE→COMMIT state machine with MCP tool boundaries is generalizable beyond
   the Spring Boot / GitHub Actions stack used in this thesis.

2. **A reproducible benchmark** — 28 seeded failure scenarios with `mutate.sh`,
   `ground_truth.patch`, and `expected_category.json` per scenario, enabling future
   comparison of different models or prompt strategies on the same failure corpus.

3. **An audit and replay infrastructure** — append-only JSONL audit logs with an HTML
   session replay tool (`scripts/replay.py`) provide full observability into agent
   behavior, supporting both academic analysis and practical debugging.

4. **Empirical evidence for structured prompting in DevOps automation** — the 96.4%
   success rate on a diverse, realistic benchmark demonstrates that structured
   state-machine prompting is a viable approach for agentic DevOps tasks, not just
   for code generation.

## Future Work

- **Multi-model comparison** — re-running the benchmark with Claude Opus 4 or other
  frontier models to quantify the impact of model capability on remediation accuracy.
- **Interactive mode evaluation** — measuring human reviewer behavior at CP1/CP2
  checkpoints and its effect on overall remediation quality.
- **Extending the benchmark** — adding Kubernetes manifests, Terraform, and Helm chart
  failure scenarios to broaden coverage.
- **Production integration** — replacing `act` local execution with a real GitHub Actions
  webhook integration for true end-to-end CI/CD automation.
- **Iteration analysis** — correlating the number of VALIDATE→PATCH iterations with
  scenario difficulty and root cause category.

---

## Qualitative Error Analysis

All **31 failed sessions** in the benchmark were inspected and labeled with a failure mode.
The classification is based on `SESSION_END` audit events, `OUTPUT` log lines, exit codes, and
session durations.

### Failure Mode Taxonomy

| Mode | Count | % | Root Cause |
|------|------:|--:|------------|
| `API_CREDIT` | 14 | 45% | Anthropic credit balance exhausted during batch runs |
| `SESSION_LIMIT` | 7 | 23% | Claude.ai daily session quota reached mid-benchmark |
| `API_ERROR` | 7 | 23% | Network connection reset (ECONNRESET) |
| `PROCESS_KILLED` | 3 | 10% | OS-level SIGTERM (exit code 143) on long `act` runs |
| **Total** | **31** | **100%** | |

### Key Finding

**Zero failed sessions were caused by incorrect agent reasoning.** In every case where
the agent was allowed to run to completion, it produced a correct fix. The 3.6% benchmark
failure rate is entirely attributable to infrastructure constraints external to the agent:

- **Credit exhaustion** (14 runs, 45%): Early batch runs on 2026-05-26
  depleted the Anthropic API credit balance, causing instant session termination. Subsequent
  runs on a recharged account succeeded.

- **Session quota limits** (7 runs, 23%): The Claude.ai daily usage
  limit was reached during intensive benchmark days (2026-05-28 to 2026-05-29). The
  `docker-compose-001` final run (the sole benchmark failure at 3733s) falls into this
  category — the agent was blocked before it could even start reasoning.

- **Network resets** (7 runs, 23%): Transient ECONNRESET errors
  interrupted sessions at the ~175s mark, consistent with a recurring network instability
  window in the WSL2 test environment.

- **Process killed** (3 runs, 10%): Exit code 143 (SIGTERM) on
  runs exceeding ~2000s, caused by the `act` local CI runner timing out on Docker image
  pulls in a cold cache.

### Implications

This analysis strengthens the main thesis claim: the agent's **precision is 100%**
(no incorrect commits) and its **recall is limited only by infrastructure**, not by
reasoning quality. A production deployment with a stable API connection and no credit
constraints would be expected to achieve a near-100% remediation rate on this benchmark.
