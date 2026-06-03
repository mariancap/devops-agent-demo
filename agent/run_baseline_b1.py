#!/usr/bin/env python3
"""
B1 Baseline — Zero-shot agent (no structured system prompt).
Copies only relevant DevOps files to a minimal tmpdir.
"""

import json
import subprocess
import tempfile
import shutil
import time
import os
from pathlib import Path

SCENARIOS = [
    "dockerfile-001",
    "docker-compose-001",
    "github-actions-001",
    "maven-001",
    "application-001",
    "mixed-001",
]

# Only these files/dirs are copied — keeps tmpdir minimal so agent doesn't wander
RELEVANT_FILES = [
    "Dockerfile",
    "docker-compose.yml",
    "pom.xml",
    "mvnw",
    "mvnw.cmd",
    ".github",
    "src",
]

ZERO_SHOT_PROMPT = """You are a DevOps assistant. There is exactly one bug in this repository that causes CI to fail.

Your task:
1. Inspect the DevOps files (Dockerfile, docker-compose.yml, .github/workflows/ci.yml, pom.xml, src/) to find the bug.
2. Fix the bug by editing the file directly.
3. Commit the fix with: git add -A && git commit -m "fix: <description>"

Rules:
- Do NOT run docker, mvn, act, or any build/test commands.
- Do NOT restore files to git HEAD. The bug is in the current working tree.
- Make exactly one commit with the fix.
"""


def run_b1_scenario(repo_root: Path, scenario_id: str) -> dict:
    scenario_dir = repo_root / "agent" / "scenarios" / scenario_id
    expected_path = scenario_dir / "expected_category.json"
    expected = json.loads(expected_path.read_text()) if expected_path.exists() else {}
    category = expected.get("category", "unknown")

    result = {
        "scenario_id": scenario_id,
        "baseline": "B1",
        "category": category,
        "committed": False,
        "agent_output": "",
        "duration_s": 0.0,
        "error": None,
        "git_log": "",
    }

    t0 = time.time()

    with tempfile.TemporaryDirectory(prefix=f"b1_{scenario_id}_") as tmpdir:
        wt = Path(tmpdir) / "wt"
        wt.mkdir()

        # Ensure repo is clean before copying (previous mutations may linger)
        subprocess.run(["git", "restore", "."], cwd=repo_root, capture_output=True)

        # Copy only relevant files
        for name in RELEVANT_FILES:
            src = repo_root / name
            dst = wt / name
            if src.is_dir():
                shutil.copytree(src, dst)
            elif src.is_file():
                shutil.copy2(src, dst)

        # Init minimal git repo
        subprocess.run(["git", "init"], cwd=wt, capture_output=True)
        subprocess.run(["git", "config", "user.email", "b1@thesis.local"], cwd=wt, capture_output=True)
        subprocess.run(["git", "config", "user.name", "B1 Baseline"], cwd=wt, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=wt, capture_output=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=wt, capture_output=True)

        # Apply mutation
        mutate_sh = scenario_dir / "mutate.sh"
        env_mutate = os.environ.copy()
        env_mutate["REPO_ROOT"] = str(wt)
        rc = subprocess.run(["bash", str(mutate_sh)], cwd=wt, capture_output=True, env=env_mutate).returncode
        if rc != 0:
            result["error"] = "mutate.sh failed"
            result["duration_s"] = round(time.time() - t0, 2)
            return result

        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "B1 Baseline"
        env["GIT_AUTHOR_EMAIL"] = "b1@thesis.local"
        env["GIT_COMMITTER_NAME"] = "B1 Baseline"
        env["GIT_COMMITTER_EMAIL"] = "b1@thesis.local"

        try:
            proc = subprocess.run(
                ["claude", "--dangerously-skip-permissions", "-p", ZERO_SHOT_PROMPT],
                cwd=wt,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )
            output = (proc.stdout + proc.stderr).strip()
            result["agent_output"] = output[:3000]

            # committed = more than 1 commit (baseline + fix)
            count = int(subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=wt, capture_output=True, text=True
            ).stdout.strip() or "0")
            result["committed"] = count > 1

            result["git_log"] = subprocess.run(
                ["git", "log", "--oneline", "-3"],
                cwd=wt, capture_output=True, text=True
            ).stdout.strip()

        except subprocess.TimeoutExpired:
            result["error"] = "TIMEOUT (300s)"
        except Exception as e:
            result["error"] = str(e)

    result["duration_s"] = round(time.time() - t0, 2)
    return result


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=".", help="Path to repo root")
    p.add_argument("--out", default="agent/eval_logs/baselines_b1.jsonl")
    p.add_argument("--scenario", help="Run single scenario only")
    args = p.parse_args()

    repo_root = Path(args.repo).resolve()
    out_path = repo_root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    scenarios = [args.scenario] if args.scenario else SCENARIOS

    print(f"B1 Baseline (zero-shot) — running {len(scenarios)} scenarios\n")
    results = []
    for sid in scenarios:
        print(f"  [{sid}] running agent ...", flush=True)
        r = run_b1_scenario(repo_root, sid)
        results.append(r)
        status = "COMMITTED" if r["committed"] else ("ERROR" if r["error"] else "NO-COMMIT")
        print(f"  [{sid}] {status} ({r['duration_s']}s)")
        if r.get("error"):
            print(f"    error: {r['error']}")
        if r.get("git_log"):
            print(f"    git: {r['git_log'].splitlines()[0]}")

    with out_path.open("w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    committed = sum(1 for r in results if r["committed"])
    print(f"\nB1 Summary: {committed}/{len(results)} committed")
    print(f"Output: {out_path}")
