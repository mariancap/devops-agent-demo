#!/usr/bin/env python3
"""Convertește un audit log CLI → entry în results_sdk.jsonl"""
import json, sys
from pathlib import Path
from datetime import datetime, timezone

def convert(scenario_id: str, audit_jsonl: Path, main_audit: Path, out_jsonl: Path):
    events = [json.loads(l) for l in audit_jsonl.read_text().splitlines() if l.strip()]
    session_end = next((e for e in events if e['event'] == 'SESSION_END'), {}).get('details', {})

    # Date din agent/logs/audit.jsonl
    mevents = [json.loads(l) for l in main_audit.read_text().splitlines() if l.strip()]
    scenario_events = [e for e in mevents if e.get('scenario_id') == scenario_id]

    committed = any(e.get('event_type') == 'COMMIT_DONE' for e in scenario_events)
    if not committed:
        import subprocess
        r = subprocess.run(
            ['git', 'ls-remote', '--heads', 'origin', f'experiment/{scenario_id}'],
            capture_output=True, text=True
        )
        committed = bool(r.stdout.strip())
    validated = any(e.get('event_type') == 'VALIDATION_RESULT' and
                    e.get('payload', {}).get('success') for e in scenario_events)
    diagnosis = next((e['payload']['diagnosis'] for e in reversed(scenario_events)
                      if e.get('event_type') == 'DIAGNOSIS'), {})

    # expected_category
    exp_file = Path(f"agent/scenarios/{scenario_id}/expected_category.json")
    expected = json.loads(exp_file.read_text()) if exp_file.exists() else {}

    # Număr de turns din OUTPUT events
    turns = sum(1 for e in events if e.get('event') == 'PHASE_TRANSITION')

    record = {
        "scenario_id": scenario_id,
        "committed": committed,
        "validation": validated,
        "turns": max(turns, 1),
        "duration_s": session_end.get('duration_s', 0),
        "tokens": 0,
        "source": "cli_oauth",
        "expected": expected,
        "diagnosis": diagnosis,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    with open(out_jsonl, 'a') as f:
        f.write(json.dumps(record) + '\n')

    print(f"  ✅ {scenario_id}: committed={committed}, validated={validated}")
    return record

if __name__ == "__main__":
    scenario_id = sys.argv[1]
    # Găsim cel mai recent audit log pentru scenariul dat
    logs = sorted(Path("agent/eval_logs").glob(f"audit_{scenario_id}_*.jsonl"))
    if not logs:
        print(f"❌ No audit log for {scenario_id}")
        sys.exit(1)
    convert(scenario_id, logs[-1],
            Path("agent/logs/audit.jsonl"),
            Path("agent/eval_logs/results_sdk.jsonl"))
