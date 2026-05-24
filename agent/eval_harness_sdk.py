#!/usr/bin/env python3
"""
eval_harness_sdk.py — rulează agentul via Anthropic SDK pe toate scenariile.

Usage:
    python3 agent/eval_harness_sdk.py [--scenarios s1 s2 ...] [--runs N] [--log-dir agent/eval_logs]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

REPO_ROOT     = Path(__file__).parent.parent.resolve()
SCENARIOS_DIR = REPO_ROOT / "agent" / "scenarios"
AGENT_DIR     = REPO_ROOT / "agent"
MODEL         = "claude-sonnet-4-5"
MAX_TURNS     = 20   # safeguard anti-loop

# ── Tool definitions (aceleași ca în MCP server) ─────────────────────────────

TOOLS = [
    {
        "name": "get_job_logs",
        "description": "Citește error.log al scenariului curent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "ID-ul scenariului"}
            },
            "required": ["scenario_id"]
        }
    },
    {
        "name": "read_file",
        "description": "Citește conținutul unui fișier din repo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Calea relativă față de rădăcina repo-ului"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "run_static_check",
        "description": "Rulează un tool de analiză statică: hadolint, actionlint, mvn-validate, compose-config.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "enum": ["hadolint", "actionlint", "mvn-validate", "compose-config"]
                }
            },
            "required": ["tool"]
        }
    },
    {
        "name": "apply_patch",
        "description": "Aplică o comandă de fix (sed, echo, etc.) în worktree.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Comanda bash de aplicat"},
                "description": {"type": "string", "description": "Descrierea fix-ului"}
            },
            "required": ["command", "description"]
        }
    },
    {
        "name": "get_diff",
        "description": "Returnează git diff față de develop în worktree.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "run_validation",
        "description": "Rulează act -j build-and-test în worktree pentru a valida fix-ul.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "checkpoint",
        "description": "Marchează un checkpoint (CP1 sau CP2). În batch mode aprobat automat.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["CP1", "CP2"]},
                "summary": {"type": "string"},
                "details": {"type": "object"}
            },
            "required": ["type", "summary"]
        }
    },
    {
        "name": "commit_fix",
        "description": "Commitează fix-ul în worktree după CP2 aprobat.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Mesajul de commit"}
            },
            "required": ["message"]
        }
    }
]


# ── Tool executor ─────────────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict, worktree: Path, scenario_id: str) -> str:
    """Execută tool-ul cerut de agent și returnează rezultatul ca string."""

    if name == "get_job_logs":
        log_path = SCENARIOS_DIR / scenario_id / "error.log"
        if log_path.exists():
            return log_path.read_text(encoding="utf-8")
        return "ERROR: error.log not found"

    elif name == "read_file":
        file_path = worktree / inputs["path"]
        if not file_path.exists():
            return f"ERROR: {inputs['path']} not found"
        if file_path.is_dir():
            files = [str(f.relative_to(worktree)) for f in file_path.rglob("*") if f.is_file()]
            return f"DIRECTORY listing:\n" + "\n".join(files[:30])
        return file_path.read_text(encoding="utf-8")

    elif name == "run_static_check":
        tool = inputs["tool"]
        if tool == "hadolint":
            r = subprocess.run(["hadolint", "Dockerfile"],
                capture_output=True, text=True, cwd=worktree)
        elif tool == "actionlint":
            r = subprocess.run(["actionlint"],
                capture_output=True, text=True, cwd=worktree)
        elif tool == "mvn-validate":
            r = subprocess.run(["./mvnw", "-B", "-q", "validate"],
                capture_output=True, text=True, cwd=worktree, timeout=60)
        elif tool == "compose-config":
            r = subprocess.run(["docker", "compose", "config", "--quiet"],
                capture_output=True, text=True, cwd=worktree)
        else:
            return f"ERROR: unknown tool {tool}"
        out = (r.stdout + r.stderr).strip()
        return out if out else f"exit_code={r.returncode} (no output)"

    elif name == "apply_patch":
        cmd = inputs["command"]
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=worktree)
        if r.returncode != 0:
            return f"ERROR (exit {r.returncode}): {r.stderr[:300]}"
        # Stage toate modificările automat
        subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
        return f"OK: {inputs.get('description', cmd)}"

    elif name == "get_diff":
        # git diff HEAD include atât unstaged cât și staged (după git add)
        r = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True, cwd=worktree)
        return r.stdout if r.stdout.strip() else "No changes yet"

    elif name == "run_validation":
        r = subprocess.run(
            ["act", "-j", "build-and-test", "--no-cache-server"],
            capture_output=True, text=True, cwd=worktree, timeout=300
        )
        status = "PASS" if r.returncode == 0 else "FAIL"
        output = (r.stdout + r.stderr)[-2000:]
        return f"Validation: {status}\n{output}"

    elif name == "checkpoint":
        cp_type = inputs["type"]
        summary = inputs.get("summary", "")
        # BATCH MODE: auto-approve
        return f"{cp_type}: APPROVED (batch mode)\nSummary: {summary}"

    elif name == "commit_fix":
        msg = inputs["message"]
        subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
        r = subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True, text=True, cwd=worktree
        )
        if r.returncode == 0:
            return f"Committed: {msg}"
        return f"ERROR: stdout={r.stdout[:200]} stderr={r.stderr[:200]}"

    return f"ERROR: unknown tool {name}"


# ── Agent loop ────────────────────────────────────────────────────────────────

def run_agent_loop(scenario_id: str, worktree: Path, system_prompt: str) -> dict:
    """
    Rulează agentul cu SDK-ul Anthropic până la COMMIT sau MAX_TURNS.
    Returnează metrici brute.
    """
    client   = anthropic.Anthropic()
    messages = [
        {
            "role": "user",
            "content": (
                f"Scenario: {scenario_id}. "
                f"Read the error log at agent/scenarios/{scenario_id}/error.log "
                f"and begin from PHASE 1: INGEST."
            )
        }
    ]

    metrics = {
        "turns":          0,
        "tool_calls":     [],
        "phases_reached": [],
        "cp1_approved":   False,
        "cp2_approved":   False,
        "committed":      False,
        "validation_pass": False,
        "input_tokens":   0,
        "output_tokens":  0,
        "error":          None,
    }

    phase_markers = {
        "PHASE 1": "INGEST", "PHASE 2": "LOCALIZE", "PHASE 3": "DIAGNOSE",
        "PHASE 4": "PATCH",  "PHASE 5": "VALIDATE",  "PHASE 6": "COMMIT",
        "CP1": "CP1", "CP2": "CP2",
    }

    for turn in range(MAX_TURNS):
        metrics["turns"] = turn + 1

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )
        except Exception as e:
            metrics["error"] = str(e)
            break

        metrics["input_tokens"]  += response.usage.input_tokens
        metrics["output_tokens"] += response.usage.output_tokens

        # Detectăm faze din text
        for block in response.content:
            if hasattr(block, "text"):
                for marker, phase in phase_markers.items():
                    if marker in block.text and phase not in metrics["phases_reached"]:
                        metrics["phases_reached"].append(phase)

        # Stop dacă nu mai sunt tool calls
        if response.stop_reason == "end_turn":
            # Salvăm ultimul mesaj text pentru debugging
            for block in response.content:
                if hasattr(block, 'text') and block.text.strip():
                    metrics['last_message'] = block.text[-500:]
            break

        # Procesăm tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name   = block.name
            tool_inputs = block.input
            metrics["tool_calls"].append(tool_name)

            if tool_name in ('apply_patch', 'commit_fix'):
                metrics.setdefault('tool_details', []).append({tool_name: tool_inputs})
            result = execute_tool(tool_name, tool_inputs, worktree, scenario_id)
            if tool_name in ('apply_patch', 'commit_fix'):
                metrics['tool_details'][-1]['result'] = result[:200]

            # Metrici speciale
            if tool_name == "checkpoint":
                if tool_inputs.get("type") == "CP1":
                    metrics["cp1_approved"] = True
                elif tool_inputs.get("type") == "CP2":
                    metrics["cp2_approved"] = True
            elif tool_name == "run_validation" and "Validation: PASS" in result:
                metrics["validation_pass"] = True
            elif tool_name == "commit_fix":
                if result.startswith("Committed:"):
                    metrics["committed"] = True
                else:
                    metrics["commit_error"] = result

            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": block.id,
                "content":     result[:3000],  # limităm răspunsul
            })

        # Dacă CP2 a fost aprobat și există modificări → commit automat
        if metrics["cp2_approved"] and not metrics["committed"]:
            r = subprocess.run(["git", "diff", "--cached", "--quiet"],
                cwd=worktree, capture_output=True)
            r2 = subprocess.run(["git", "diff", "--quiet"],
                cwd=worktree, capture_output=True)
            if r.returncode != 0 or r2.returncode != 0:
                subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
                cr = subprocess.run(
                    ["git", "commit", "-m", f"fix: {scenario_id} (auto-committed after CP2)"],
                    cwd=worktree, capture_output=True, text=True
                )
                if cr.returncode == 0:
                    metrics["committed"] = True
                    break

        # Adăugăm răspunsul agentului și rezultatele tool-urilor în history
        messages.append({"role": "assistant", "content": response.content})
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        else:
            break  # niciun tool call → agent a terminat

    return metrics


# ── Worktree management ───────────────────────────────────────────────────────

def setup_worktree(scenario_id: str, run_idx: int) -> Path:
    branch = f"eval/{scenario_id}/run{run_idx}"
    path   = REPO_ROOT / ".eval_worktrees" / f"{scenario_id}_run{run_idx}"

    # Curățăm complet worktree-ul existent
    subprocess.run(["git", "worktree", "remove", "--force", str(path)],
        cwd=REPO_ROOT, capture_output=True)
    subprocess.run(["git", "branch", "-D", branch],
        cwd=REPO_ROOT, capture_output=True)
    if path.exists():
        shutil.rmtree(path)

    r = subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(path), "develop"],
        cwd=REPO_ROOT, capture_output=True, text=True
    )
    if r.returncode != 0:
        raise RuntimeError(f"worktree add failed: {r.stderr}")
    return path


def cleanup_worktree(scenario_id: str, run_idx: int):
    branch = f"eval/{scenario_id}/run{run_idx}"
    path   = REPO_ROOT / ".eval_worktrees" / f"{scenario_id}_run{run_idx}"
    subprocess.run(["git", "worktree", "remove", "--force", str(path)],
        cwd=REPO_ROOT, capture_output=True)
    subprocess.run(["git", "branch", "-D", branch],
        cwd=REPO_ROOT, capture_output=True)


# ── Scenario runner ───────────────────────────────────────────────────────────

def run_scenario(scenario_id: str, run_idx: int, log_dir: Path, system_prompt: str) -> dict:
    print(f"  run {run_idx+1} ...", end=" ", flush=True)
    start = datetime.now(timezone.utc)

    result = {
        "scenario_id": scenario_id,
        "run_idx":     run_idx,
        "timestamp":   start.isoformat(),
        "expected":    json.loads((SCENARIOS_DIR / scenario_id / "expected_category.json").read_text())
                       if (SCENARIOS_DIR / scenario_id / "expected_category.json").exists() else {},
    }

    try:
        worktree = setup_worktree(scenario_id, run_idx)

        # Aplică mutația și o commitează în worktree
        # mutate.sh calculează REPO_ROOT din locația scriptului, deci îl copiem în worktree
        mutate_src = SCENARIOS_DIR / scenario_id / "mutate.sh"
        mutate_dst = worktree / "agent" / "scenarios" / scenario_id / "mutate.sh"
        mutate_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mutate_src, mutate_dst)
        r = subprocess.run(["bash", str(mutate_dst)], cwd=worktree,
            capture_output=True, text=True)
        if r.returncode != 0:
            result["error"] = f"mutate failed: {r.stderr[:200]}"
            print("❌ mutate failed")
            return result
        # Commitează mutația ca baseline — agentul trebuie să o reverseze
        subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"mutation: {scenario_id}"],
            cwd=worktree, capture_output=True)

        # Generează error.log dacă nu există
        error_log_src = SCENARIOS_DIR / scenario_id / "error.log"
        if not error_log_src.exists():
            print(f"    [generating error.log via act...]", end=" ", flush=True)
            act_result = subprocess.run(
                ["act", "-j", "build-and-test", "--no-cache-server"],
                capture_output=True, text=True, cwd=worktree, timeout=300
            )
            error_log_src.parent.mkdir(parents=True, exist_ok=True)
            error_log_src.write_text(act_result.stdout + act_result.stderr, encoding="utf-8")
            print("done")

        # Copia error.log în worktree
        error_log_dst = worktree / "agent" / "scenarios" / scenario_id / "error.log"
        error_log_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(error_log_src, error_log_dst)

        # Rulează agentul
        metrics = run_agent_loop(scenario_id, worktree, system_prompt)
        result.update(metrics)

        duration = (datetime.now(timezone.utc) - start).total_seconds()
        result["duration_s"] = round(duration, 1)

        status = "✅" if metrics.get("committed") else "❌"
        print(f"{status} ({duration:.0f}s, turns={metrics['turns']}, "
              f"committed={metrics['committed']}, validation={metrics['validation_pass']})")

    except Exception as e:
        result["error"] = str(e)
        print(f"💥 {e}")
    finally:
        try:
            cleanup_worktree(scenario_id, run_idx)
        except Exception:
            pass

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def discover_scenarios() -> list[str]:
    return sorted(d.name for d in SCENARIOS_DIR.iterdir()
                  if d.is_dir() and (d / "mutate.sh").exists())


def main():
    parser = argparse.ArgumentParser(description="DevOps Agent SDK Evaluation Harness")
    parser.add_argument("--scenarios", nargs="*")
    parser.add_argument("--runs",     type=int, default=3)
    parser.add_argument("--log-dir",  default="agent/eval_logs")
    parser.add_argument("--dry-run",  action="store_true")
    args = parser.parse_args()

    system_prompt = (AGENT_DIR / "system_prompt_batch.md").read_text(encoding="utf-8")
    scenarios     = args.scenarios or discover_scenarios()
    log_dir       = REPO_ROOT / args.log_dir
    results_file  = log_dir / "results_sdk.jsonl"

    print(f"🤖 Model    : {MODEL}")
    print(f"📦 Scenarii : {len(scenarios)}")
    print(f"🔁 Rulări   : {args.runs}")
    print(f"📄 Output   : {results_file}")

    if args.dry_run:
        for s in scenarios:
            print(f"  {s}")
        return

    log_dir.mkdir(parents=True, exist_ok=True)

    total = len(scenarios) * args.runs
    committed = 0

    with open(results_file, "a", encoding="utf-8") as out:
        for scenario_id in scenarios:
            expected = json.loads((SCENARIOS_DIR / scenario_id / "expected_category.json").read_text()) \
                       if (SCENARIOS_DIR / scenario_id / "expected_category.json").exists() else {}
            print(f"\n📦 {scenario_id} (cat: {expected.get('category','?')})")

            for run_idx in range(args.runs):
                result = run_scenario(scenario_id, run_idx, log_dir, system_prompt)
                out.write(json.dumps(result) + "\n")
                out.flush()
                if result.get("committed"):
                    committed += 1

    print(f"\n{'='*50}")
    print(f"🎯 Committed: {committed}/{total} ({100*committed//max(total,1)}%)")
    print(f"📄 Rezultate: {results_file}")


if __name__ == "__main__":
    main()
