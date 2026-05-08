#!/usr/bin/env python3
"""
MCP Server pentru DevOps Agent Demo
Tool-uri: get_job_logs, write_audit_event, run_static_check, request_approval, run_validation
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Directorul rădăcină al repo-ului (părintele directorului mcp/)
REPO_ROOT = Path(__file__).parent.parent

app = Server("devops-agent-mcp")


# ─────────────────────────────────────────────
# Tool 1: get_job_logs
# ─────────────────────────────────────────────
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
        )
    ]


# ─────────────────────────────────────────────
# Handler tool-uri
# ─────────────────────────────────────────────
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

        # Schema validation for DIAGNOSIS events
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

        log_dir = REPO_ROOT / "agent" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "audit.jsonl"
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": payload
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
        return [TextContent(type="text", text=f"✅ Eveniment scris: {event_type}")]
    # ── run_static_check ──────────────────────
    elif name == "run_static_check":
        checks  = arguments["checks"]
        results = {}

        for check in checks:
            if check == "hadolint":
                r = subprocess.run(
                    ["hadolint", str(REPO_ROOT / "Dockerfile")],
                    capture_output=True, text=True
                )
                results["hadolint"] = {
                    "exit_code": r.returncode,
                    "output": r.stdout + r.stderr or "✅ Nicio problemă găsită"
                }

            elif check == "actionlint":
                r = subprocess.run(
                    ["actionlint"],
                    capture_output=True, text=True,
                    cwd=str(REPO_ROOT)
                )
                results["actionlint"] = {
                    "exit_code": r.returncode,
                    "output": r.stdout + r.stderr or "✅ Nicio problemă găsită"
                }

            elif check == "mvn_validate":
                r = subprocess.run(
                    ["./mvnw", "validate", "-q"],
                    capture_output=True, text=True,
                    cwd=str(REPO_ROOT)
                )
                results["mvn_validate"] = {
                    "exit_code": r.returncode,
                    "output": r.stdout + r.stderr or "✅ POM valid"
                }

        return [TextContent(type="text", text=json.dumps(results, indent=2))]

    # ── request_approval ──────────────────────
    elif name == "request_approval":
        checkpoint = arguments["checkpoint"]
        summary    = arguments["summary"]
        details    = arguments.get("details", {})

        print(f"\n{'='*60}", flush=True)
        print(f"🔴 CHECKPOINT {checkpoint} — APROBARE NECESARĂ", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"\n📋 Rezumat: {summary}\n", flush=True)
        if details:
            print(f"📎 Detalii:\n{json.dumps(details, indent=2)}\n", flush=True)
        print(f"{'='*60}", flush=True)

        # Scrie și în audit log
        log_dir  = REPO_ROOT / "agent" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "audit.jsonl"
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": f"CHECKPOINT_{checkpoint}",
            "payload": {"summary": summary, "details": details, "status": "PENDING"}
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

        # Citește răspunsul de la utilizator
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(
            None,
            lambda: input(f"\n➡️  Aprobați {checkpoint}? [y/n]: ").strip().lower()
        )

        approved = answer in ("y", "yes", "da")
        status   = "APPROVED" if approved else "REJECTED"

        # Update audit log cu decizia
        event["payload"]["status"] = status
        with open(log_file, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": f"CHECKPOINT_{checkpoint}_DECISION",
                "payload": {"decision": status}
            }) + "\n")

        return [TextContent(
            type="text",
            text=f"{checkpoint}: {status}"
        )]

    # ── run_validation ────────────────────────
    elif name == "run_validation":
        job         = arguments.get("job", "build-and-test")
        working_dir = arguments.get("working_dir", str(REPO_ROOT))

        result = subprocess.run(
            ["act", "-j", job, "--no-cache-server"],
            capture_output=True, text=True,
            cwd=working_dir,
            timeout=300
        )

        output = result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout
        return [TextContent(type="text", text=json.dumps({
            "exit_code": result.returncode,
            "success": result.returncode == 0,
            "output_tail": output,
            "stderr_tail": result.stderr[-500:] if result.stderr else ""
        }, indent=2))]

    else:
        return [TextContent(type="text", text=f"ERROR: tool necunoscut '{name}'")]


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
