package com.thesis.demo.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.ResponseEntity;
import org.springframework.http.MediaType;

@RestController
public class HomeController {

    @GetMapping(value = "/", produces = MediaType.TEXT_HTML_VALUE)
    public ResponseEntity<String> home() {
        String html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>devops-agent-demo</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #e6edf3; font-family: 'JetBrains Mono', 'Fira Code', monospace; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 2rem; }
  .container { max-width: 720px; width: 100%; }
  .badge { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; padding: 4px 12px; border-radius: 20px; background: rgba(35,134,54,0.15); color: #3fb950; border: 1px solid rgba(63,185,80,0.3); margin-bottom: 1.5rem; font-family: sans-serif; }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: #3fb950; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.4; } }
  h1 { font-size: 28px; font-weight: 600; margin-bottom: 0.5rem; color: #e6edf3; }
  .subtitle { font-size: 14px; color: #8b949e; line-height: 1.6; margin-bottom: 2rem; font-family: sans-serif; }
  .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 2rem; }
  .metric { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1rem 1.25rem; }
  .metric-label { font-size: 11px; color: #8b949e; margin-bottom: 8px; font-family: sans-serif; text-transform: uppercase; letter-spacing: .05em; }
  .metric-value { font-size: 26px; font-weight: 600; color: #e6edf3; }
  .metric-sub { font-size: 12px; color: #8b949e; margin-top: 4px; font-family: sans-serif; }
  .section-label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: .05em; font-family: sans-serif; margin-bottom: 10px; }
  .endpoints { display: flex; flex-direction: column; gap: 6px; margin-bottom: 2rem; }
  .endpoint { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: #161b22; border: 1px solid #30363d; border-radius: 6px; font-size: 13px; }
  .method { font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; min-width: 50px; text-align: center; font-family: sans-serif; }
  .get { background: rgba(31,111,235,.15); color: #79c0ff; border: 1px solid rgba(31,111,235,.3); }
  .post { background: rgba(35,134,54,.15); color: #3fb950; border: 1px solid rgba(35,134,54,.3); }
  .patch { background: rgba(187,128,9,.15); color: #e3b341; border: 1px solid rgba(187,128,9,.3); }
  .path { flex: 1; color: #e6edf3; }
  .desc { font-size: 12px; color: #8b949e; font-family: sans-serif; }
  .footer { display: flex; align-items: center; justify-content: space-between; padding-top: 1.5rem; border-top: 1px solid #30363d; font-size: 12px; color: #8b949e; font-family: sans-serif; }
  .footer a { color: #79c0ff; text-decoration: none; }
  .footer a:hover { text-decoration: underline; }
  .thesis-tag { background: rgba(188,140,255,.15); color: #d2a8ff; border: 1px solid rgba(188,140,255,.3); padding: 3px 10px; border-radius: 4px; font-size: 11px; }
</style>
</head>
<body>
<div class="container">
  <div class="badge"><span class="dot"></span>live · devops-agent-demo.onrender.com</div>
  <h1>devops-agent-demo</h1>
  <p class="subtitle">Task Management REST API — Spring Boot 3.5 · PostgreSQL · Java 21<br>CI/CD remediation agent benchmark substrate · Master's thesis, Marian Capotă 2026</p>

  <div class="metrics">
    <div class="metric">
      <div class="metric-label">Agent success rate</div>
      <div class="metric-value">96.4%</div>
      <div class="metric-sub">27 / 28 scenarios</div>
    </div>
    <div class="metric">
      <div class="metric-label">Benchmark scenarios</div>
      <div class="metric-value">28</div>
      <div class="metric-sub">6 failure categories</div>
    </div>
    <div class="metric">
      <div class="metric-label">vs zero-shot (B1)</div>
      <div class="metric-value">+79.7pp</div>
      <div class="metric-sub">16.7% → 96.4%</div>
    </div>
  </div>

  <div class="section-label">API endpoints</div>
  <div class="endpoints">
    <div class="endpoint"><span class="method get">GET</span><span class="path">/api/tasks</span><span class="desc">list all tasks</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/api/tasks/{id}</span><span class="desc">get task by id</span></div>
    <div class="endpoint"><span class="method post">POST</span><span class="path">/api/tasks</span><span class="desc">create task</span></div>
    <div class="endpoint"><span class="method patch">PATCH</span><span class="path">/api/tasks/{id}/status</span><span class="desc">update task status</span></div>
    <div class="endpoint"><span class="method get">GET</span><span class="path">/actuator/health</span><span class="desc">health check</span></div>
  </div>

  <div class="footer">
    <span class="thesis-tag">dizertație 2026</span>
    <a href="https://github.com/mariancap/devops-agent-demo" target="_blank">github.com/mariancap/devops-agent-demo</a>
  </div>
</div>
</body>
</html>
""";
        return ResponseEntity.ok(html);
    }
}
