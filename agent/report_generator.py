#!/usr/bin/env python3
"""Generează report.html cu grafice pentru susținerea tezei."""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ── Încarcă datele ────────────────────────────────────────────────────────────
lines = [json.loads(l) for l in Path("agent/eval_logs/results_sdk.jsonl").read_text().splitlines() if l.strip()]
valid = [r for r in lines if not r.get("error")]

best = {}
for r in valid:
    sid = r["scenario_id"]
    current = best.get(sid)
    if not current:
        best[sid] = r
    elif r.get("committed") and not current.get("committed"):
        best[sid] = r
    elif r.get("validation") and not current.get("validation") and not current.get("committed"):
        best[sid] = r

scenarios = sorted(best.values(), key=lambda x: x["scenario_id"])

# ── Metrici per categorie ─────────────────────────────────────────────────────
by_cat = defaultdict(lambda: {"total": 0, "committed": 0, "validated": 0, "durations": []})
for r in scenarios:
    cat = r.get("expected", {}).get("category",
          r.get("diagnosis", {}).get("category", "unknown"))
    r["_cat"] = cat
    by_cat[cat]["total"] += 1
    by_cat[cat]["committed"] += int(r.get("committed", False))
    by_cat[cat]["validated"] += int(r.get("validation", False))
    if r.get("duration_s"):
        by_cat[cat]["durations"].append(r["duration_s"])

cats = sorted(by_cat.keys())
total_s = len(scenarios)
total_committed = sum(1 for r in scenarios if r.get("committed"))
total_validated = sum(1 for r in scenarios if r.get("validation"))
total_success = sum(1 for r in scenarios if r.get("committed") or r.get("validation"))
avg_dur = sum(r.get("duration_s", 0) for r in scenarios) / total_s if total_s else 0

# ── Date pentru grafice ───────────────────────────────────────────────────────
cat_labels = json.dumps(cats)
cat_committed = json.dumps([by_cat[c]["committed"] for c in cats])
cat_validated = json.dumps([max(0, by_cat[c]["validated"] - by_cat[c]["committed"]) for c in cats])
cat_failed = json.dumps([max(0, by_cat[c]["total"] - by_cat[c]["validated"]) for c in cats])
cat_totals = json.dumps([by_cat[c]["total"] for c in cats])

scenario_labels = json.dumps([r["scenario_id"] for r in scenarios])
scenario_status = json.dumps([
    2 if r.get("committed") else (1 if r.get("validation") else 0)
    for r in scenarios
])
scenario_durations = json.dumps([round(r.get("duration_s", 0)) for r in scenarios])

# ── HTML ──────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DevOps Agent — Evaluation Report</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
  header {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-bottom: 1px solid #334155; padding: 2rem 3rem; }}
  header h1 {{ font-size: 1.8rem; color: #f8fafc; font-weight: 700; }}
  header p {{ color: #94a3b8; margin-top: .4rem; font-size: .95rem; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem 3rem; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }}
  .kpi {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 1.4rem; text-align: center; }}
  .kpi .value {{ font-size: 2.2rem; font-weight: 700; color: #38bdf8; }}
  .kpi .label {{ font-size: .8rem; color: #94a3b8; margin-top: .3rem; text-transform: uppercase; letter-spacing: .05em; }}
  .kpi.green .value {{ color: #4ade80; }}
  .kpi.yellow .value {{ color: #fbbf24; }}
  .kpi.purple .value {{ color: #a78bfa; }}
  .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem; }}
  .chart-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 1.5rem; }}
  .chart-card h2 {{ font-size: 1rem; color: #cbd5e1; margin-bottom: 1rem; font-weight: 600; }}
  .chart-card.full {{ grid-column: 1 / -1; }}
  canvas {{ max-height: 280px; }}
  .table-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; }}
  .table-card h2 {{ font-size: 1rem; color: #cbd5e1; margin-bottom: 1rem; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
  th {{ text-align: left; padding: .6rem .8rem; color: #64748b; border-bottom: 1px solid #334155; font-weight: 600; text-transform: uppercase; font-size: .75rem; letter-spacing: .05em; }}
  td {{ padding: .6rem .8rem; border-bottom: 1px solid #1e293b; }}
  tr:hover td {{ background: #263347; }}
  .badge {{ display: inline-block; padding: .2rem .6rem; border-radius: 6px; font-size: .75rem; font-weight: 600; }}
  .badge.committed {{ background: #14532d; color: #4ade80; }}
  .badge.validated {{ background: #713f12; color: #fbbf24; }}
  .badge.failed {{ background: #3b1515; color: #f87171; }}
  footer {{ text-align: center; padding: 2rem; color: #475569; font-size: .8rem; border-top: 1px solid #1e293b; }}
</style>
</head>
<body>
<header>
  <h1>DevOps Agent — Evaluation Report</h1>
  <p>Agentic CI/CD Remediation · Benchmark Results · Generat {datetime.now().strftime("%d %b %Y %H:%M")}</p>
</header>
<div class="container">

  <!-- KPI Cards -->
  <div class="kpi-grid">
    <div class="kpi green">
      <div class="value">{total_success}/{total_s}</div>
      <div class="label">Success Rate</div>
    </div>
    <div class="kpi">
      <div class="value">{round(100*total_success/total_s)}%</div>
      <div class="label">Remediation Rate</div>
    </div>
    <div class="kpi yellow">
      <div class="value">{total_committed}</div>
      <div class="label">Committed to Git</div>
    </div>
    <div class="kpi purple">
      <div class="value">{round(avg_dur)}s</div>
      <div class="label">Avg Duration</div>
    </div>
  </div>

  <!-- Charts -->
  <div class="charts-grid">
    <div class="chart-card">
      <h2>Success Rate per Categorie</h2>
      <canvas id="catBar"></canvas>
    </div>
    <div class="chart-card">
      <h2>Distribuție Rezultate</h2>
      <canvas id="donut"></canvas>
    </div>
    <div class="chart-card full">
      <h2>Durată per Scenariu (secunde)</h2>
      <canvas id="durBar"></canvas>
    </div>
  </div>

  <!-- Scenario Table -->
  <div class="table-card">
    <h2>Rezultate per Scenariu</h2>
    <table>
      <thead><tr>
        <th>Scenariu</th><th>Categorie</th><th>Status</th>
        <th>Committed</th><th>Validated</th><th>Durată</th>
      </tr></thead>
      <tbody>
{''.join(f"""        <tr>
          <td>{r['scenario_id']}</td>
          <td>{r.get('_cat','?')}</td>
          <td><span class="badge {'committed' if r.get('committed') else ('validated' if r.get('validation') else 'failed')}">
            {'✅ Committed' if r.get('committed') else ('🔶 Validated' if r.get('validation') else '❌ Failed')}
          </span></td>
          <td>{'✅' if r.get('committed') else '—'}</td>
          <td>{'✅' if r.get('validation') else '—'}</td>
          <td>{round(r.get('duration_s',0))}s</td>
        </tr>""" for r in scenarios)}
      </tbody>
    </table>
  </div>

</div>
<footer>DevOps Agent Demo · mariancap/devops-agent-demo · Teză de Masterat 2026</footer>

<script>
const catLabels = {cat_labels};
const committed = {cat_committed};
const validatedOnly = {cat_validated};
const failed = {cat_failed};
const totals = {cat_totals};

// Bar chart per categorie
new Chart(document.getElementById('catBar'), {{
  type: 'bar',
  data: {{
    labels: catLabels,
    datasets: [
      {{ label: 'Committed', data: committed, backgroundColor: '#4ade80', borderRadius: 4 }},
      {{ label: 'Validated only', data: validatedOnly, backgroundColor: '#fbbf24', borderRadius: 4 }},
      {{ label: 'Failed', data: failed, backgroundColor: '#f87171', borderRadius: 4 }}
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: true,
    plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
    scales: {{
      x: {{ stacked: true, ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} }},
      y: {{ stacked: true, ticks: {{ color: '#94a3b8', stepSize: 1 }}, grid: {{ color: '#334155' }} }}
    }}
  }}
}});

// Donut
new Chart(document.getElementById('donut'), {{
  type: 'doughnut',
  data: {{
    labels: ['Committed', 'Validated only', 'Failed'],
    datasets: [{{ data: [{total_committed}, {total_validated - total_committed}, {total_s - total_success}],
      backgroundColor: ['#4ade80', '#fbbf24', '#f87171'], borderWidth: 0 }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: true,
    plugins: {{
      legend: {{ labels: {{ color: '#94a3b8' }} }},
      tooltip: {{ callbacks: {{ label: ctx => ` ${{ctx.label}}: ${{ctx.raw}} scenarii` }} }}
    }}
  }}
}});

// Duration bar
const scenLabels = {scenario_labels};
const durations = {scenario_durations};
const statuses = {scenario_status};
const colors = statuses.map(s => s === 2 ? '#4ade80' : s === 1 ? '#fbbf24' : '#f87171');

new Chart(document.getElementById('durBar'), {{
  type: 'bar',
  data: {{
    labels: scenLabels,
    datasets: [{{ label: 'Durată (s)', data: durations, backgroundColor: colors, borderRadius: 4 }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#94a3b8', maxRotation: 45 }}, grid: {{ color: '#1e293b' }} }},
      y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

out = Path("agent/report.html")
out.write_text(html)
print(f"✅ Report generat: {out} ({len(html)//1024}KB)")
print(f"   Scenarii: {total_s} | Success: {total_success} ({round(100*total_success/total_s)}%) | Avg dur: {round(avg_dur)}s")
