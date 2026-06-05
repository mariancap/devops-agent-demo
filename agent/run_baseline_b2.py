#!/usr/bin/env python3
"""
B2 Baseline — Static-only evaluation (hadolint + actionlint + mvn validate).
Runs each scenario's mutate.sh on a temp copy of the repo, then runs static checks.
No agent involved.
"""

import json
import subprocess
import tempfile
import shutil
import time
from pathlib import Path

SCENARIOS = [
    "dockerfile-001",
    "docker-compose-001",
    "github-actions-001",
    "maven-001",
    "application-001",
    "mixed-001",
]


def run_cmd(cmd, cwd, timeout=60):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)


def evaluate_scenario_b2(repo_root: Path, scenario_id: str) -> dict:
    scenario_dir = repo_root / "agent" / "scenarios" / scenario_id
    expected_path = scenario_dir / "expected_category.json"
    expected = json.loads(expected_path.read_text()) if expected_path.exists() else {}
    category = expected.get("category", "unknown")

    result = {
        "scenario_id": scenario_id,
        "baseline": "B2",
        "category": category,
        "checks_run": [],
        "issues_found": [],
        "detected": False,
        "detection_tool": None,
        "duration_s": 0.0,
        "notes": "",
    }

    t0 = time.time()

    with tempfile.TemporaryDirectory(prefix=f"b2_{scenario_id}_") as tmpdir:
        wt = Path(tmpdir) / "wt"
        shutil.copytree(repo_root, wt, ignore=shutil.ignore_patterns(".git"))
        git_dir = repo_root / ".git"
        if git_dir.exists():
            shutil.copytree(git_dir, wt / ".git")

        mutate_sh = scenario_dir / "mutate.sh"
        rc, out, err = run_cmd(["bash", str(mutate_sh)], cwd=wt)
        if rc != 0:
            result["notes"] = f"mutate.sh failed: {err[:200]}"
            result["duration_s"] = round(time.time() - t0, 2)
            return result

        detected = False

        # hadolint — Dockerfile
        if category in ("dockerfile", "mixed"):
            if (wt / "Dockerfile").exists():
                rc, out, err = run_cmd(["hadolint", "Dockerfile"], cwd=wt)
                issues = (out + err).strip()
                result["checks_run"].append("hadolint")
                if rc != 0 and issues:
                    result["issues_found"].append({"tool": "hadolint", "output": issues[:500]})
                    detected = True
                    result["detection_tool"] = "hadolint"

        # actionlint — GitHub Actions
        if category in ("github-actions", "mixed"):
            if (wt / ".github" / "workflows" / "ci.yml").exists():
                rc, out, err = run_cmd(["actionlint", ".github/workflows/ci.yml"], cwd=wt)
                issues = (out + err).strip()
                result["checks_run"].append("actionlint")
                if rc != 0 and issues:
                    result["issues_found"].append({"tool": "actionlint", "output": issues[:500]})
                    if not detected:
                        detected = True
                        result["detection_tool"] = "actionlint"

        # docker compose config — docker-compose
        if category in ("docker-compose", "mixed"):
            rc, out, err = run_cmd(["docker", "compose", "config", "--quiet"], cwd=wt, timeout=30)
            result["checks_run"].append("docker compose config")
            if rc != 0:
                issues = (out + err).strip()
                result["issues_found"].append({"tool": "docker compose config", "output": issues[:500]})
                if not detected:
                    detected = True
                    result["detection_tool"] = "docker compose config"

        # mvn validate — Maven
        if category in ("maven", "mixed"):
            rc, out, err = run_cmd(
                ["mvn", "validate", "-q", "--no-transfer-progress"], cwd=wt, timeout=120
            )
            result["checks_run"].append("mvn validate")
            if rc != 0:
                issues = (out + err).strip()
                result["issues_found"].append({"tool": "mvn validate", "output": issues[:500]})
                if not detected:
                    detected = True
                    result["detection_tool"] = "mvn validate"

        # application — no static tool
        if category == "application":
            result["checks_run"].append("none (no static tool covers Java app logic)")
            result["notes"] = "No static tool covers Java application logic mutations."

    result["detected"] = detected
    result["duration_s"] = round(time.time() - t0, 2)
    return result


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=".", help="Path to repo root")
    p.add_argument("--out", default="agent/eval_logs/baselines_b2.jsonl")
    args = p.parse_args()

    repo_root = Path(args.repo).resolve()
    out_path = repo_root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"B2 Baseline — running {len(SCENARIOS)} scenarios\n")
    results = []
    for sid in SCENARIOS:
        print(f"  [{sid}] ...", end=" ", flush=True)
        r = evaluate_scenario_b2(repo_root, sid)
        results.append(r)
        status = "DETECTED" if r["detected"] else "MISSED"
        tool = r.get("detection_tool") or "-"
        print(f"{status} via {tool} ({r['duration_s']}s)")

    with out_path.open("w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    detected = sum(1 for r in results if r["detected"])
    print(f"\nB2 Summary: {detected}/{len(results)} detected")
    print(f"Output: {out_path}")
