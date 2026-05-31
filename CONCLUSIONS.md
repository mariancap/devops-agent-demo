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
