#!/usr/bin/env python3
"""
MCP Server pentru DevOps Agent Demo
Tool-uri: get_job_logs, write_audit_event, run_static_check,
          request_approval, run_validation, apply_patch, get_diff
"""

import asyncio
import os
import os
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

REPO_ROOT   = Path(__file__).parent.parent
WORKTREE_PATH = REPO_ROOT / ".patch-worktree"
_iteration_state: dict = {"count": 0, "max": 3}
_session_state: dict = {"scenario_id": None, "phase": "IDLE"}

def _write_audit(event_type: str, payload: dict) -> None:
    log_dir = REPO_ROOT / "agent" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "audit.jsonl", "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "phase": _session_state["phase"],
            "scenario_id": _session_state["scenario_id"],
            "payload": payload
        }) + "\n")

app = Server("devops-agent-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_job_logs",
            description="Citește logurile unui job CI sau ale unui container Docker",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "enum": ["docker", "file"],
                        "description": "Sursa logurilor: 'docker' pentru container activ, 'file' pentru fișier local"
                    },
                    "target": {
                        "type": "string",
                        "description": "Numele containerului Docker SAU calea către fișierul de log"
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Numărul de linii de returnat (default: 100)",
                        "default": 100
                    }
                },
                "required": ["source", "target"]
            }
        ),
        Tool(
            name="write_audit_event",
            description="Scrie un eveniment în audit log-ul JSONL al sesiunii curente",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Tipul evenimentului (ex: DIAGNOSIS, PATCH_PROPOSAL, CHECKPOINT)"
                    },
                    "payload": {
                        "type": "object",
                        "description": "Date suplimentare despre eveniment"
                    }
                },
                "required": ["event_type", "payload"]
            }
        ),
        Tool(
            name="run_static_check",
            description="Rulează lintere statice: hadolint (Dockerfile), actionlint (GitHub Actions), mvn validate",
            inputSchema={
                "type": "object",
                "properties": {
                    "checks": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["hadolint", "actionlint", "mvn_validate"]
                        },
                        "description": "Lista de checks de rulat"
                    }
                },
                "required": ["checks"]
            }
        ),
        Tool(
            name="request_approval",
            description="Solicită aprobare umană la un checkpoint (CP1 sau CP2). Blochează până la răspuns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "checkpoint": {
                        "type": "string",
                        "enum": ["CP1", "CP2"],
                        "description": "CP1 = aprobare plan de fix, CP2 = aprobare commit final"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Rezumatul a ceea ce agentul vrea să facă"
                    },
                    "details": {
                        "type": "object",
                        "description": "Detalii tehnice (diff, comenzi propuse, etc.)"
                    }
                },
                "required": ["checkpoint", "summary"]
            }
        ),
        Tool(
            name="run_validation",
            description="Rulează pipeline-ul de validare complet cu 'act'. Returnează exit code și output.",
            inputSchema={
                "type": "object",
                "properties": {
                    "job": {
                        "type": "string",
                        "description": "Numele job-ului GitHub Actions de rulat (default: build-and-test)",
                        "default": "build-and-test"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Directorul de lucru (default: root repo)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="apply_patch",
            description=(
                "Creează un git worktree izolat și aplică patch_hint-ul din diagnoză. "
                "Worktree-ul e la .patch-worktree/ față de rădăcina repo-ului. "
                "Returnează success/failure și output-ul comenzii."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "patch_hint": {
                        "type": "string",
                        "description": "Comanda shell de aplicat (din câmpul proposed_fix.patch_hint al diagnozei)"
                    },
                    "scenario_id": {
                        "type": "string",
                        "description": "ID-ul scenariului activ (folosit doar pentru audit)"
                    }
                },
                "required": ["patch_hint", "scenario_id"]
            }
        ),
        Tool(
            name="get_diff",
            description=(
                "Returnează git diff --stat + diff complet din worktree-ul de patch. "
                "Apelează după apply_patch, înainte de CP2."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_iteration_state",
            description=(
                "Returnează numărul curent de iterații de validare și limita maximă. "
                "Apelează înainte de fiecare retry pentru a verifica dacă mai poți încerca."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="reset_iteration_counter",
            description="Resetează contorul de iterații la 0. Apelează la începutul fiecărui scenariu nou.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="increment_iteration_counter",
            description=(
                "Incrementează contorul de iterații cu 1. "
                "Apelează după fiecare validation failure (static sau dynamic), "
                "înainte de a decide dacă reîncerci sau abandonezi."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Motivul incrementării (ex: 'hadolint failed', 'act exit code 1')"
                    }
                },
                "required": ["reason"]
            }
        ),
        Tool(
            name="set_session_context",
            description=(
                "Setează contextul sesiunii curente: scenario_id și faza activă. "
                "Apelează la fiecare tranziție de fază (INGEST, LOCALIZE, DIAGNOSE, PATCH, VALIDATE, COMMIT). "
                "Toate evenimentele de audit scrise după acest apel vor include automat contextul setat."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario_id": {
                        "type": "string",
                        "description": "ID-ul scenariului activ (ex: dockerfile-001)"
                    },
                    "phase": {
                        "type": "string",
                        "enum": ["IDLE", "INGEST", "LOCALIZE", "DIAGNOSE", "PATCH", "VALIDATE", "COMMIT"],
                        "description": "Faza curentă a state machine-ului"
                    }
                },
                "required": ["scenario_id", "phase"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    # ── get_job_logs ──────────────────────────
    if name == "get_job_logs":
        source = arguments["source"]
        target = arguments["target"]
        lines  = arguments.get("lines", 100)

        if source == "docker":
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), target],
                capture_output=True, text=True
            )
            output = result.stdout + result.stderr
        else:
            path = REPO_ROOT / target
            if not path.exists():
                output = f"ERROR: fișierul {path} nu există"
            else:
                with open(path) as f:
                    all_lines = f.readlines()
                output = "".join(all_lines[-lines:])

        return [TextContent(type="text", text=output or "(log gol)")]

    # ── write_audit_event ─────────────────────
    elif name == "write_audit_event":
        event_type = arguments["event_type"]
        payload    = arguments["payload"]

        if event_type == "DIAGNOSIS":
            import jsonschema as _js
            schema_path = REPO_ROOT / "agent" / "schemas" / "diagnosis.schema.json"
            with open(schema_path) as sf:
                schema = json.load(sf)
            try:
                _js.validate(instance=payload, schema=schema)
            except _js.ValidationError as ve:
                return [TextContent(
                    type="text",
                    text="❌ SCHEMA VALIDATION FAILED for DIAGNOSIS payload:\n"
                         + ve.message
                         + "\nPath: " + str(list(ve.absolute_path))
                         + "\nCorrect your JSON and retry."
                )]

        _write_audit(event_type, payload)
        return [TextContent(type="text", text=f"✅ Eveniment scris: {event_type}")]

    # ── run_static_check ──────────────────────
    elif name == "run_static_check":
        checks  = arguments["checks"]
        results = {}

        # Rulează în worktree dacă există, altfel în repo root
        target_dir = WORKTREE_PATH if WORKTREE_PATH.exists() else REPO_ROOT

        for check in checks:
            if check == "hadolint":
                dockerfile = target_dir / "Dockerfile"
                if not dockerfile.exists():
                    results["hadolint"] = {"exit_code": 1, "output": f"ERROR: Dockerfile nu există în {target_dir}"}
                    continue
                r = subprocess.run(
                    ["hadolint", str(dockerfile)],
                    capture_output=True, text=True
                )
                results["hadolint"] = {
                    "exit_code": r.returncode,
                    "output": (r.stdout + r.stderr).strip() or "✅ Nicio problemă găsită"
                }
            elif check == "actionlint":
                r = subprocess.run(
                    ["actionlint"],
                    capture_output=True, text=True,
                    cwd=str(target_dir)
                )
                results["actionlint"] = {
                    "exit_code": r.returncode,
                    "output": (r.stdout + r.stderr).strip() or "✅ Nicio problemă găsită"
                }
            elif check == "mvn_validate":
                r = subprocess.run(
                    ["./mvnw", "validate", "-q"],
                    capture_output=True, text=True,
                    cwd=str(target_dir)
                )
                results["mvn_validate"] = {
                    "exit_code": r.returncode,
                    "output": (r.stdout + r.stderr).strip() or "✅ POM valid"
                }
            elif check == "docker_compose_config":
                r = subprocess.run(
                    ["docker", "compose", "config", "--quiet"],
                    capture_output=True, text=True,
                    cwd=str(target_dir)
                )
                results["docker_compose_config"] = {
                    "exit_code": r.returncode,
                    "output": (r.stdout + r.stderr).strip() or "✅ docker-compose valid"
                }

        # Rezumat global: PASS doar dacă toți exit_code == 0
        all_passed = all(v["exit_code"] == 0 for v in results.values())
        summary = "✅ STATIC_PASS" if all_passed else "❌ STATIC_FAIL"

        return [TextContent(type="text", text=json.dumps({
        "summary": summary,
        "all_passed": all_passed,
        "target_dir": str(target_dir),
        "results": results
        }, indent=2))]

    # ── request_approval ──────────────────────
    elif name == "request_approval":
        checkpoint = arguments["checkpoint"]
        summary    = arguments["summary"]
        details    = arguments.get("details", {})

        # La CP2 injectăm automat diff-ul dacă worktree-ul există
        if checkpoint == "CP2" and WORKTREE_PATH.exists():
            diff_result = subprocess.run(
                ["git", "diff"],
                capture_output=True, text=True,
                cwd=str(WORKTREE_PATH)
            )
            if diff_result.stdout.strip():
                details["diff"] = diff_result.stdout

        print(f"\n{'='*60}", flush=True)
        print(f"🔴 CHECKPOINT {checkpoint} — APROBARE NECESARĂ", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"\n📋 Rezumat: {summary}\n", flush=True)
        if details:
            if "diff" in details:
                print(f"📄 Diff:\n{details['diff']}", flush=True)
            other = {k: v for k, v in details.items() if k != "diff"}
            if other:
                print(f"📎 Detalii:\n{json.dumps(other, indent=2)}\n", flush=True)
        print(f"{'='*60}", flush=True)

        _write_audit(f"CHECKPOINT_{checkpoint}", {"summary": summary, "details": details, "status": "PENDING"})

        batch_flag = Path(REPO_ROOT) / ".batch_mode"
        if os.environ.get("BATCH_MODE") in ("1", "true", "True") or batch_flag.exists():
            print(f"[BATCH] Auto-approving {checkpoint}", flush=True)
            answer = "y"
        else:
            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(
                None,
                lambda: input(f"\n➡️  Aprobați {checkpoint}? [y/n]: ").strip().lower()
            )

        approved = answer in ("y", "yes", "da")
        status   = "APPROVED" if approved else "REJECTED"

        _write_audit(f"CHECKPOINT_{checkpoint}_DECISION", {"decision": status})

        return [TextContent(type="text", text=f"{checkpoint}: {status}")]

    # ── run_validation ────────────────────────
    elif name == "run_validation":
        job = arguments.get("job", "build-and-test")

        if "working_dir" in arguments:
            working_dir = arguments["working_dir"]
        elif WORKTREE_PATH.exists():
            working_dir = str(WORKTREE_PATH)
        else:
            working_dir = str(REPO_ROOT)

        try:
            result = subprocess.run(
                ["act", "-j", job, "--no-cache-server"],
                capture_output=True, text=True,
                cwd=working_dir,
                timeout=300
            )
            output = result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout
            success = result.returncode == 0

            # Audit
            log_dir = REPO_ROOT / "agent" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            _write_audit("DYNAMIC_VALIDATION", {
                "job": job,
                "working_dir": working_dir,
                "exit_code": result.returncode,
                "success": success
            })

            return [TextContent(type="text", text=json.dumps({
                "exit_code": result.returncode,
                "success": success,
                "working_dir": working_dir,
                "output_tail": output,
                "stderr_tail": result.stderr[-500:] if result.stderr else ""
            }, indent=2))]

        except subprocess.TimeoutExpired:
            return [TextContent(type="text", text=json.dumps({
                "exit_code": -1,
                "success": False,
                "working_dir": working_dir,
                "output_tail": "TIMEOUT după 300s",
                "stderr_tail": ""
            }, indent=2))]
        

    # ── apply_patch ───────────────────────────
    elif name == "apply_patch":
        patch_hint  = arguments["patch_hint"]
        scenario_id = arguments["scenario_id"]

        # Curățăm worktree-ul vechi dacă există
        if WORKTREE_PATH.exists():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(WORKTREE_PATH)],
                cwd=str(REPO_ROOT), capture_output=True
            )
            if WORKTREE_PATH.exists():
                shutil.rmtree(WORKTREE_PATH)

        # Creăm worktree nou pe branch-ul curent
        wt_result = subprocess.run(
            ["git", "worktree", "add", str(WORKTREE_PATH), "HEAD"],
            capture_output=True, text=True,
            cwd=str(REPO_ROOT)
        )
        if wt_result.returncode != 0:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": "Nu s-a putut crea worktree",
                "stderr": wt_result.stderr
            }))]

        # Aplicăm patch_hint în worktree
        patch_result = subprocess.run(
            patch_hint,
            shell=True,
            capture_output=True, text=True,
            cwd=str(WORKTREE_PATH)
        )

        success = patch_result.returncode == 0

        # Audit
        log_dir  = REPO_ROOT / "agent" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        _write_audit("PATCH_APPLIED", {
            "scenario_id": scenario_id,
            "patch_hint": patch_hint,
            "success": success,
            "stdout": patch_result.stdout,
            "stderr": patch_result.stderr,
            "worktree": str(WORKTREE_PATH)
        })

        return [TextContent(type="text", text=json.dumps({
            "success": success,
            "patch_hint": patch_hint,
            "stdout": patch_result.stdout,
            "stderr": patch_result.stderr,
            "worktree": str(WORKTREE_PATH)
        }, indent=2))]

    # ── get_diff ──────────────────────────────
    elif name == "get_diff":
        if not WORKTREE_PATH.exists():
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": "Worktree-ul nu există. Apelează apply_patch mai întâi."
            }))]

        stat_result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True,
            cwd=str(WORKTREE_PATH)
        )
        diff_result = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True,
            cwd=str(WORKTREE_PATH)
        )

        has_changes = bool(diff_result.stdout.strip())

        return [TextContent(type="text", text=json.dumps({
            "has_changes": has_changes,
            "stat": stat_result.stdout,
            "diff": diff_result.stdout
        }, indent=2))]

    elif name == "get_iteration_state":
        return [TextContent(type="text", text=json.dumps({
            "current": _iteration_state["count"],
            "max": _iteration_state["max"],
            "remaining": _iteration_state["max"] - _iteration_state["count"],
            "exhausted": _iteration_state["count"] >= _iteration_state["max"]
        }, indent=2))]

    elif name == "reset_iteration_counter":
        _iteration_state["count"] = 0
        return [TextContent(type="text", text=json.dumps({
            "reset": True,
            "current": 0,
            "max": _iteration_state["max"]
        }, indent=2))]
    
    elif name == "increment_iteration_counter":
        reason = arguments.get("reason", "unspecified")
        _iteration_state["count"] += 1

        # Audit
        log_dir = REPO_ROOT / "agent" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        _write_audit("ITERATION_INCREMENT", {
            "reason": reason,
            "count_after": _iteration_state["count"],
            "max": _iteration_state["max"],
            "exhausted": _iteration_state["count"] >= _iteration_state["max"]
        })

        return [TextContent(type="text", text=json.dumps({
            "count": _iteration_state["count"],
            "max": _iteration_state["max"],
            "remaining": _iteration_state["max"] - _iteration_state["count"],
            "exhausted": _iteration_state["count"] >= _iteration_state["max"]
        }, indent=2))]
    
    elif name == "set_session_context":
        _session_state["scenario_id"] = arguments["scenario_id"]
        _session_state["phase"] = arguments["phase"]
        _write_audit("SESSION_CONTEXT_SET", {
            "scenario_id": _session_state["scenario_id"],
            "phase": _session_state["phase"]
        })
        return [TextContent(type="text", text=json.dumps({
            "scenario_id": _session_state["scenario_id"],
            "phase": _session_state["phase"]
        }, indent=2))]
    
    else:
        return [TextContent(type="text", text=f"ERROR: tool necunoscut '{name}'")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())