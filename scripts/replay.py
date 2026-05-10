#!/usr/bin/env python3
"""
Session Replay — citește agent/logs/audit.jsonl și afișează sesiunea colorat.
Utilizare:
  python3 scripts/replay.py                        # ultimul audit.jsonl
  python3 scripts/replay.py path/to/audit.jsonl    # fișier specific
  python3 scripts/replay.py --html output.html     # export HTML
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Culori ANSI
R  = "\033[31m"  # roșu
G  = "\033[32m"  # verde
Y  = "\033[33m"  # galben
B  = "\033[34m"  # albastru
M  = "\033[35m"  # magenta
C  = "\033[36m"  # cyan
W  = "\033[37m"  # alb
BO = "\033[1m"   # bold
RS = "\033[0m"   # reset

PHASE_COLOR = {
    "IDLE": W, "INGEST": C, "LOCALIZE": B,
    "DIAGNOSE": M, "PATCH": Y, "VALIDATE": Y, "COMMIT": G
}

EVENT_COLOR = {
    "SESSION_CONTEXT_SET": C,
    "DIAGNOSIS": M,
    "PATCH_APPLIED": Y,
    "DYNAMIC_VALIDATION": Y,
    "ITERATION_INCREMENT": R,
    "CHECKPOINT_CP1": B,
    "CHECKPOINT_CP1_DECISION": B,
    "CHECKPOINT_CP2": B,
    "CHECKPOINT_CP2_DECISION": B,
    "COMMIT_DONE": G,
    "VALIDATION_FAILED": R,
    "PATCH_REJECTED": R,
}

HTML_EVENT_COLOR = {
    "SESSION_CONTEXT_SET": "#00bcd4",
    "DIAGNOSIS": "#ce93d8",
    "PATCH_APPLIED": "#fff176",
    "DYNAMIC_VALIDATION": "#fff176",
    "ITERATION_INCREMENT": "#ef9a9a",
    "CHECKPOINT_CP1": "#90caf9",
    "CHECKPOINT_CP1_DECISION": "#90caf9",
    "CHECKPOINT_CP2": "#90caf9",
    "CHECKPOINT_CP2_DECISION": "#90caf9",
    "COMMIT_DONE": "#a5d6a7",
    "VALIDATION_FAILED": "#ef9a9a",
    "PATCH_REJECTED": "#ef9a9a",
}


def fmt_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return ts


def fmt_payload(payload: dict, indent: int = 4) -> str:
    skip = {"diagnosis", "details", "diff"}  # câmpuri voluminoase — trunchiem
    lines = []
    for k, v in payload.items():
        if k in skip and isinstance(v, (dict, str)) and len(str(v)) > 120:
            lines.append(f"{' ' * indent}{k}: <...{len(str(v))} chars>")
        else:
            lines.append(f"{' ' * indent}{k}: {json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines)


def replay_terminal(events: list[dict]) -> None:
    scenario = None
    print(f"\n{BO}{'─' * 60}{RS}")
    print(f"{BO}  SESSION REPLAY  —  {len(events)} events{RS}")
    print(f"{BO}{'─' * 60}{RS}\n")

    for e in events:
        ts         = fmt_ts(e.get("timestamp", ""))
        event_type = e.get("event_type", "UNKNOWN")
        phase      = e.get("phase", "")
        scen       = e.get("scenario_id") or ""
        payload    = e.get("payload", {})

        if scen and scen != scenario:
            scenario = scen
            print(f"\n{BO}{G}▶ SCENARIO: {scenario}{RS}\n")

        ec   = EVENT_COLOR.get(event_type, W)
        pc   = PHASE_COLOR.get(phase, W)
        p_str = f"{pc}[{phase}]{RS}" if phase else ""

        print(f"{W}{ts}{RS}  {ec}{BO}{event_type:<30}{RS}  {p_str}")

        if payload:
            # Succes/failure highlight
            if "success" in payload:
                flag = f"{G}✅ success{RS}" if payload["success"] else f"{R}❌ failed{RS}"
                print(f"    {flag}")
            if "exit_code" in payload and "success" not in payload:
                color = G if payload["exit_code"] == 0 else R
                print(f"    exit_code: {color}{payload['exit_code']}{RS}")
            if "exhausted" in payload and payload["exhausted"]:
                print(f"    {R}{BO}⚠ ITERATION LIMIT REACHED{RS}")
            if "decision" in payload:
                color = G if payload["decision"] == "APPROVED" else R
                print(f"    decision: {color}{BO}{payload['decision']}{RS}")

            # Payload complet (trunchiat)
            formatted = fmt_payload(payload)
            if formatted:
                print(f"{W}{formatted}{RS}")

        print()

    print(f"{BO}{'─' * 60}{RS}\n")


def replay_html(events: list[dict], output_path: Path) -> None:
    rows = []
    for e in events:
        ts         = fmt_ts(e.get("timestamp", ""))
        event_type = e.get("event_type", "UNKNOWN")
        phase      = e.get("phase", "")
        scen       = e.get("scenario_id") or ""
        payload    = e.get("payload", {})
        color      = HTML_EVENT_COLOR.get(event_type, "#ffffff")

        payload_html = json.dumps(payload, indent=2, ensure_ascii=False)
        rows.append(f"""
        <tr style="background:{color}22">
          <td style="color:#aaa;white-space:nowrap">{ts}</td>
          <td><strong>{event_type}</strong></td>
          <td>{phase}</td>
          <td>{scen}</td>
          <td><pre style="margin:0;font-size:11px">{payload_html}</pre></td>
        </tr>""")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Session Replay</title>
<style>
  body {{ font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
  h1 {{ color: #ce93d8; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th {{ background: #333; padding: 8px; text-align: left; color: #fff; }}
  td {{ padding: 6px 10px; border-bottom: 1px solid #333; vertical-align: top; }}
  pre {{ background: #2d2d2d; padding: 6px; border-radius: 4px; white-space: pre-wrap; }}
</style>
</head>
<body>
<h1>🔁 Session Replay — {len(events)} events</h1>
<table>
  <thead>
    <tr><th>Time</th><th>Event</th><th>Phase</th><th>Scenario</th><th>Payload</th></tr>
  </thead>
  <tbody>
    {"".join(rows)}
  </tbody>
</table>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    print(f"HTML exportat: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="DevOps Agent Session Replay")
    parser.add_argument("logfile", nargs="?", default="agent/logs/audit.jsonl")
    parser.add_argument("--html", metavar="OUTPUT", help="Exportă în HTML")
    args = parser.parse_args()

    log_path = Path(args.logfile)
    if not log_path.exists():
        print(f"ERROR: {log_path} nu există.", file=sys.stderr)
        sys.exit(1)

    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as ex:
                print(f"WARN: linie invalidă ignorată: {ex}", file=sys.stderr)

    if not events:
        print("Log gol — niciun eveniment de afișat.")
        return

    if args.html:
        replay_html(events, Path(args.html))
    else:
        replay_terminal(events)


if __name__ == "__main__":
    main()
