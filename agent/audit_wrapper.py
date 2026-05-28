#!/usr/bin/env python3
"""
audit_wrapper.py — wraps a Claude Code session and writes an append-only JSONL audit log.

Usage:
    python3 agent/audit_wrapper.py --scenario <scenario-id> --log-dir agent/logs

What it does:
    1. Starts Claude Code as a subprocess with the system prompt
    2. Passes stdin/stdout through to the terminal (interactive session)
    3. Intercepts every line of output and writes it to a JSONL audit log
    4. Detects phase transitions by scanning for known keywords
    5. On exit, writes a final summary event
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


# ── Phase keywords Claude Code emits in its output ──────────────────────────
PHASE_MARKERS = {
    "PHASE 1: INGEST":      "INGEST",
    "PHASE 2: LOCALIZE":    "LOCALIZE",
    "PHASE 3: DIAGNOSE":    "DIAGNOSE",
    "CHECKPOINT 1":         "CP1",
    "PHASE 4: PATCH":       "PATCH",
    "PHASE 5: VALIDATE":    "VALIDATE",
    "CHECKPOINT 2":         "CP2",
    "PHASE 6: COMMIT":      "COMMIT",
}


def now_iso() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def write_event(log_file, event_type: str, phase: str, details: dict):
    """Append a single JSON event to the audit log."""
    event = {
        "timestamp": now_iso(),
        "event":     event_type,
        "phase":     phase,
        "details":   details,
    }
    log_file.write(json.dumps(event) + "\n")
    log_file.flush()   # write immediately — never buffer audit events


def detect_phase(line: str, current_phase: str) -> str:
    """Check if a line signals a phase transition; return new phase if so."""
    for marker, phase_name in PHASE_MARKERS.items():
        if marker in line:
            return phase_name
    return current_phase


def build_claude_command(scenario_id: str, system_prompt_path: str) -> list[str]:
    """Build the Claude Code CLI invocation."""
    return [
        "claude",
        "--mcp-config", str(Path(system_prompt_path).parent.parent / ".claude.json"),
        "--dangerously-skip-permissions",
        "--system-prompt", system_prompt_path.replace("system_prompt.md", "system_prompt_batch.md") if os.environ.get("BATCH_MODE") in ("1", "true", "True") or (Path(system_prompt_path).parent.parent / ".batch_mode").exists() else system_prompt_path,
        "--print",                  # non-interactive / headless output
        f"Scenario: {scenario_id}. Read the error log at agent/scenarios/{scenario_id}/error.log and begin from PHASE 1: INGEST.",
    ]


def run(scenario_id: str, log_dir: str, system_prompt_path: str, dry_run: bool):
    """Main entry point: launch Claude Code and stream + log its output."""

    os.makedirs(log_dir, exist_ok=True)

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path    = os.path.join(log_dir, f"audit_{scenario_id}_{timestamp}.jsonl")

    print(f"[audit_wrapper] Scenario  : {scenario_id}")
    print(f"[audit_wrapper] Log file  : {log_path}")
    print(f"[audit_wrapper] Dry run   : {dry_run}")
    print("-" * 60)

    cmd = build_claude_command(scenario_id, system_prompt_path)

    if dry_run:
        print(f"[audit_wrapper] DRY RUN — would execute: {' '.join(cmd)}")
        return

    current_phase   = "INIT"
    iteration       = 0
    start_time      = datetime.now(timezone.utc)

    with open(log_path, "a", encoding="utf-8") as log_file:

        # ── SESSION START event ──────────────────────────────────────────
        write_event(log_file, "SESSION_START", current_phase, {
            "scenario_id":       scenario_id,
            "system_prompt":     system_prompt_path,
            "command":           cmd,
        })

        # ── Launch Claude Code subprocess ────────────────────────────────
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge stderr into stdout
            env={**os.environ, "ANTHROPIC_API_KEY": ""},
            text=True,
            bufsize=1,                  # line-buffered
        )

        # ── Stream output line by line ───────────────────────────────────
        assert process.stdout is not None, "stdout should be PIPE"
        for raw_line in process.stdout:
            line = raw_line.rstrip()

            # Print to terminal so the operator can follow along
            print(line)

            # Detect phase transitions
            new_phase = detect_phase(line, current_phase)
            if new_phase != current_phase:
                write_event(log_file, "PHASE_TRANSITION", new_phase, {
                    "from":      current_phase,
                    "to":        new_phase,
                    "trigger":   line,
                })
                current_phase = new_phase

                if new_phase == "PATCH":
                    iteration += 1

            # Log every line as an OUTPUT event
            write_event(log_file, "OUTPUT", current_phase, {"line": line})

        process.wait()
        exit_code   = process.returncode
        end_time    = datetime.now(timezone.utc)
        duration_s  = (end_time - start_time).total_seconds()

        # ── SESSION END event ────────────────────────────────────────────
        write_event(log_file, "SESSION_END", current_phase, {
            "exit_code":    exit_code,
            "iterations":   iteration,
            "duration_s":   round(duration_s, 2),
            "final_phase":  current_phase,
            "success":      exit_code == 0,
        })

    print("-" * 60)
    print(f"[audit_wrapper] Session ended. Exit code: {exit_code}")
    print(f"[audit_wrapper] Duration : {duration_s:.1f}s  |  Iterations: {iteration}")
    print(f"[audit_wrapper] Audit log: {log_path}")

    sys.exit(exit_code)


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude Code audit wrapper")

    parser.add_argument("--scenario",
        required=True,
        help="Scenario ID, e.g. 'dockerfile-001'")

    parser.add_argument("--log-dir",
        default="agent/logs",
        help="Directory where JSONL audit logs are written (default: agent/logs)")

    parser.add_argument("--system-prompt",
        default="agent/system_prompt.md",
        help="Path to the system prompt file (default: agent/system_prompt.md)")

    parser.add_argument("--dry-run",
        action="store_true",
        help="Print the command that would be run without executing it")

    args = parser.parse_args()

    run(
        scenario_id        = args.scenario,
        log_dir            = args.log_dir,
        system_prompt_path = args.system_prompt,
        dry_run            = args.dry_run,
    )