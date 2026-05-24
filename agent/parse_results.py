#!/usr/bin/env python3
"""
parse_results.py — citește results_sdk.jsonl și produce metrici agregate + SQLite.
Usage:
    python3 agent/parse_results.py [--results agent/eval_logs/results_sdk.jsonl]
"""

import argparse
import json
import sqlite3
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).parent.parent.resolve()


def load_results(path: Path) -> list[dict]:
    results = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return results


def compute_metrics(results: list[dict]) -> dict:
    total     = len(results)
    committed = sum(1 for r in results if r.get("committed"))
    validated = sum(1 for r in results if r.get("validation_pass"))
    cp1_ok    = sum(1 for r in results if r.get("cp1_approved"))
    cp2_ok    = sum(1 for r in results if r.get("cp2_approved"))
    errors    = sum(1 for r in results if r.get("error"))

    turns_list = [r["turns"] for r in results if r.get("turns")]
    tokens_in  = [r.get("input_tokens", 0) for r in results]
    tokens_out = [r.get("output_tokens", 0) for r in results]
    durations  = [r.get("duration_s", 0) for r in results]

    by_category = defaultdict(lambda: {"total": 0, "committed": 0, "validated": 0})
    for r in results:
        cat = r.get("expected", {}).get("category", "unknown")
        by_category[cat]["total"]     += 1
        by_category[cat]["committed"] += int(r.get("committed", False))
        by_category[cat]["validated"] += int(r.get("validation_pass", False))

    def avg(lst): return round(sum(lst) / len(lst), 2) if lst else 0
    def pct(n, d): return round(100 * n / d, 1) if d else 0

    return {
        "total_runs":           total,
        "remediation_success":  committed,
        "remediation_rate_pct": pct(committed, total),
        "validation_pass":      validated,
        "validation_rate_pct":  pct(validated, total),
        "cp1_approval_rate":    pct(cp1_ok, total),
        "cp2_approval_rate":    pct(cp2_ok, total),
        "errors":               errors,
        "avg_turns":            avg(turns_list),
        "avg_input_tokens":     avg(tokens_in),
        "avg_output_tokens":    avg(tokens_out),
        "avg_duration_s":       avg(durations),
        "total_input_tokens":   sum(tokens_in),
        "total_output_tokens":  sum(tokens_out),
        "by_category":          dict(by_category),
    }


def save_to_sqlite(results: list[dict], metrics: dict, db_path: Path):
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id     TEXT,
            run_idx         INTEGER,
            category        TEXT,
            timestamp       TEXT,
            committed       INTEGER,
            validation_pass INTEGER,
            cp1_approved    INTEGER,
            cp2_approved    INTEGER,
            turns           INTEGER,
            duration_s      REAL,
            input_tokens    INTEGER,
            output_tokens   INTEGER,
            error           TEXT
        );
        CREATE TABLE IF NOT EXISTS metrics_summary (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    for r in results:
        expected = r.get("expected", {})
        cur.execute("""
            INSERT INTO runs (
                scenario_id, run_idx, category, timestamp,
                committed, validation_pass, cp1_approved, cp2_approved,
                turns, duration_s, input_tokens, output_tokens, error
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            r.get("scenario_id"), r.get("run_idx"),
            expected.get("category", "unknown"), r.get("timestamp"),
            int(r.get("committed", False)), int(r.get("validation_pass", False)),
            int(r.get("cp1_approved", False)), int(r.get("cp2_approved", False)),
            r.get("turns", 0), r.get("duration_s", 0),
            r.get("input_tokens", 0), r.get("output_tokens", 0),
            r.get("error"),
        ))
    for key, val in metrics.items():
        if key != "by_category":
            cur.execute("INSERT OR REPLACE INTO metrics_summary VALUES (?,?)",
                (key, str(val)))
    conn.commit()
    conn.close()


def print_report(metrics: dict):
    print("\n" + "="*55)
    print("  EVALUATION RESULTS SUMMARY")
    print("="*55)
    print(f"  Total runs          : {metrics['total_runs']}")
    print(f"  Remediation rate    : {metrics['remediation_success']}/{metrics['total_runs']} "
          f"({metrics['remediation_rate_pct']}%)")
    print(f"  Validation rate     : {metrics['validation_pass']}/{metrics['total_runs']} "
          f"({metrics['validation_rate_pct']}%)")
    print(f"  CP1 approval rate   : {metrics['cp1_approval_rate']}%")
    print(f"  CP2 approval rate   : {metrics['cp2_approval_rate']}%")
    print(f"  Avg turns/run       : {metrics['avg_turns']}")
    print(f"  Avg duration        : {metrics['avg_duration_s']}s")
    print(f"  Total tokens        : {metrics['total_input_tokens'] + metrics['total_output_tokens']:,}")
    print(f"  Errors              : {metrics['errors']}")
    print("\n  Per categorie:")
    print(f"  {'Categorie':<20} {'Success':>8} {'Validated':>10} {'Rate':>8}")
    print("  " + "-"*48)
    for cat, m in sorted(metrics["by_category"].items()):
        rate = f"{round(100*m['committed']/m['total'])}%" if m['total'] else "-"
        print(f"  {cat:<20} {m['committed']:>4}/{m['total']:<3} "
              f"{m['validated']:>4}/{m['total']:<6} {rate:>7}")
    print("="*55)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="agent/eval_logs/results_sdk.jsonl")
    args = parser.parse_args()

    results_path = REPO_ROOT / args.results
    if not results_path.exists():
        print(f"❌ Nu găsesc: {results_path}")
        return

    print(f"📄 Citesc: {results_path}")
    results = load_results(results_path)
    print(f"   {len(results)} run-uri găsite")

    metrics = compute_metrics(results)
    print_report(metrics)

    db_path = results_path.parent / "eval_results.db"
    save_to_sqlite(results, metrics, db_path)
    print(f"\n💾 SQLite: {db_path}")


if __name__ == "__main__":
    main()
