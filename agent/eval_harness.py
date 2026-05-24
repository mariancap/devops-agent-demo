#!/usr/bin/env python3
"""
eval_harness.py — rulează agentul automat pe toate scenariile și colectează metrici brute.

Usage:
    python3 agent/eval_harness.py [--scenarios s1 s2 ...] [--runs N] [--log-dir agent/eval_logs]

Ce face:
    1. Descoperă toate scenariile din agent/scenarios/
    2. Pentru fiecare scenariu, rulează de N ori:
       a. Creează un worktree curat
       b. Aplică mutate.sh
       c. Copiază error.log în worktree
       d. Rulează audit_wrapper.py cu BATCH_MODE=1
       e. Colectează rezultatul (success/fail, faze atinse, durata)
    3. Scrie rezultatele în agent/eval_logs/results.jsonl
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.parent.resolve()
SCENARIOS_DIR = REPO_ROOT / "agent" / "scenarios"
AGENT_DIR    = REPO_ROOT / "agent"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def discover_scenarios() -> list[str]:
    """Returnează lista sorted a tuturor scenariilor din agent/scenarios/."""
    return sorted(
        d.name for d in SCENARIOS_DIR.iterdir()
        if d.is_dir() and (d / "mutate.sh").exists()
    )


def load_expected(scenario_id: str) -> dict:
    """Citește expected_category.json pentru un scenariu."""
    path = SCENARIOS_DIR / scenario_id / "expected_category.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def setup_worktree(scenario_id: str, run_idx: int) -> Path:
    """
    Creează un git worktree izolat pentru un run.
    Branch-ul temporar: eval/<scenario_id>/run<N>
    """
    branch = f"eval/{scenario_id}/run{run_idx}"
    worktree_path = REPO_ROOT / ".eval_worktrees" / f"{scenario_id}_run{run_idx}"

    # Curăță dacă există deja
    if worktree_path.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=REPO_ROOT, capture_output=True
        )

    # Șterge branch-ul temporar dacă există
    subprocess.run(
        ["git", "branch", "-D", branch],
        cwd=REPO_ROOT, capture_output=True
    )

    # Creează worktree pe un branch nou din develop
    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path), "develop"],
        cwd=REPO_ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {result.stderr}")

    return worktree_path


def cleanup_worktree(scenario_id: str, run_idx: int):
    """Șterge worktree-ul și branch-ul temporar."""
    branch = f"eval/{scenario_id}/run{run_idx}"
    worktree_path = REPO_ROOT / ".eval_worktrees" / f"{scenario_id}_run{run_idx}"

    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_path)],
        cwd=REPO_ROOT, capture_output=True
    )
    subprocess.run(
        ["git", "branch", "-D", branch],
        cwd=REPO_ROOT, capture_output=True
    )


def apply_mutation(scenario_id: str, worktree_path: Path) -> bool:
    """Rulează mutate.sh în worktree. Returnează True dacă a reușit."""
    mutate_script = SCENARIOS_DIR / scenario_id / "mutate.sh"
    result = subprocess.run(
        ["bash", str(mutate_script)],
        cwd=str(worktree_path),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  mutate.sh failed: {result.stderr[:200]}")
        return False
    return True


def copy_error_log(scenario_id: str, worktree_path: Path):
    """Copiază error.log pre-generat în worktree (în agent/scenarios/<id>/)."""
    src = SCENARIOS_DIR / scenario_id / "error.log"
    dst_dir = worktree_path / "agent" / "scenarios" / scenario_id
    dst_dir.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(src, dst_dir / "error.log")


def run_agent(scenario_id: str, worktree_path: Path, log_dir: Path) -> dict:
    """
    Rulează audit_wrapper.py cu BATCH_MODE=1.
    Returnează dict cu: exit_code, duration_s, final_phase, log_path.
    """
    env = os.environ.copy()
    env["BATCH_MODE"] = "1"
    # MCP server-ul trebuie să lucreze în worktree
    env["WORKTREE_PATH"] = str(worktree_path)

    log_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            sys.executable,
            str(AGENT_DIR / "audit_wrapper.py"),
            "--scenario", scenario_id,
            "--log-dir", str(log_dir),
            "--system-prompt", str(AGENT_DIR / "system_prompt.md"),
        ],
        cwd=str(worktree_path),
        capture_output=True, text=True,
        env=env,
        timeout=300
    )

    # Găsește fișierul de log generat (cel mai recent pentru acest scenariu)
    logs = sorted(log_dir.glob(f"audit_{scenario_id}_*.jsonl"))
    log_path = str(logs[-1]) if logs else None

    return {
        "exit_code":   result.returncode,
        "stdout":      result.stdout[-2000:],   # ultimele 2000 chars
        "stderr":      result.stderr[-500:],
        "log_path":    log_path,
    }


def parse_audit_log(log_path: str | None) -> dict:
    """
    Extrage metrici brute din JSONL-ul de audit.
    Returnează: phases_reached, iterations, duration_s, success, final_phase.
    """
    if not log_path or not Path(log_path).exists():
        return {"phases_reached": [], "iterations": 0, "duration_s": 0,
                "success": False, "final_phase": "UNKNOWN"}

    phases_reached = []
    iterations     = 0
    duration_s     = 0.0
    success        = False
    final_phase    = "UNKNOWN"

    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = event.get("event", "")
            phase = event.get("phase", "")

            if etype == "PHASE_TRANSITION":
                to_phase = event["details"].get("to", phase)
                if to_phase not in phases_reached:
                    phases_reached.append(to_phase)
                if to_phase == "PATCH":
                    iterations += 1

            elif etype == "SESSION_END":
                d = event.get("details", {})
                duration_s  = d.get("duration_s", 0.0)
                success     = d.get("success", False)
                final_phase = d.get("final_phase", phase)
                iterations  = d.get("iterations", iterations)

    return {
        "phases_reached": phases_reached,
        "iterations":     iterations,
        "duration_s":     duration_s,
        "success":        success,
        "final_phase":    final_phase,
    }


def run_scenario(scenario_id: str, run_idx: int, log_dir: Path) -> dict:
    """Rulează un scenariu o singură dată și returnează rezultatul complet."""
    print(f"  run {run_idx+1} ...", end=" ", flush=True)
    start = datetime.now(timezone.utc)

    result = {
        "scenario_id": scenario_id,
        "run_idx":     run_idx,
        "timestamp":   now_iso(),
        "worktree_ok": False,
        "mutate_ok":   False,
        "agent_exit":  -1,
        "log_path":    None,
    }

    try:
        worktree_path = setup_worktree(scenario_id, run_idx)
        result["worktree_ok"] = True

        if not apply_mutation(scenario_id, worktree_path):
            print("❌ mutate failed")
            return result
        result["mutate_ok"] = True

        copy_error_log(scenario_id, worktree_path)

        # Flag file pentru BATCH_MODE în MCP server
        batch_flag = REPO_ROOT / ".batch_mode"
        batch_flag.touch()
        try:
            agent_result = run_agent(scenario_id, worktree_path, log_dir)
        finally:
            batch_flag.unlink(missing_ok=True)
        result.update(agent_result)

        audit_metrics = parse_audit_log(agent_result["log_path"])
        result.update(audit_metrics)

        status = "✅" if result.get("success") else "❌"
        print(f"{status} ({result.get('duration_s', 0):.0f}s, phase={result.get('final_phase')})")

    except subprocess.TimeoutExpired:
        result["error"] = "TIMEOUT"
        print("⏱️  TIMEOUT")
    except Exception as e:
        result["error"] = str(e)
        print(f"💥 ERROR: {e}")
    finally:
        try:
            cleanup_worktree(scenario_id, run_idx)
        except Exception:
            pass

    return result


def main():
    parser = argparse.ArgumentParser(description="DevOps Agent Evaluation Harness")
    parser.add_argument("--scenarios", nargs="*",
        help="Scenariile de rulat (default: toate)")
    parser.add_argument("--runs", type=int, default=3,
        help="Numărul de rulări per scenariu (default: 3)")
    parser.add_argument("--log-dir", default="agent/eval_logs",
        help="Director pentru log-uri (default: agent/eval_logs)")
    parser.add_argument("--dry-run", action="store_true",
        help="Afișează ce ar rula fără să execute")
    args = parser.parse_args()

    scenarios = args.scenarios or discover_scenarios()
    log_dir   = REPO_ROOT / args.log_dir
    results_file = log_dir / "results.jsonl"

    print(f"🔍 Scenarii: {len(scenarios)}")
    print(f"🔁 Rulări/scenariu: {args.runs}")
    print(f"📁 Log dir: {log_dir}")
    print(f"📄 Rezultate: {results_file}")

    if args.dry_run:
        print("\n[DRY RUN] Scenarii care ar fi rulate:")
        for s in scenarios:
            print(f"  {s}")
        return

    log_dir.mkdir(parents=True, exist_ok=True)

    total     = len(scenarios) * args.runs
    completed = 0
    successes = 0

    with open(results_file, "a", encoding="utf-8") as out:
        for scenario_id in scenarios:
            expected = load_expected(scenario_id)
            print(f"\n📦 {scenario_id} (cat: {expected.get('category', '?')})")

            for run_idx in range(args.runs):
                result = run_scenario(scenario_id, run_idx, log_dir)
                result["expected"] = expected
                out.write(json.dumps(result) + "\n")
                out.flush()

                completed += 1
                if result.get("success"):
                    successes += 1

    print(f"\n{'='*50}")
    print(f"✅ Completate: {completed}/{total}")
    print(f"🎯 Success rate: {successes}/{completed} ({100*successes//max(completed,1)}%)")
    print(f"📄 Rezultate: {results_file}")


if __name__ == "__main__":
    main()
