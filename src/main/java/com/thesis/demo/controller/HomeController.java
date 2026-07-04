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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #f6f8fa; color: #1a1f2e; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 2rem; }
  .container { max-width: 740px; width: 100%; background: #ffffff; border-radius: 12px; border: 1px solid #d0d7de; padding: 2.5rem; box-shadow: 0 1px 3px rgba(0,0,0,.07); }
  .badge { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500; padding: 4px 12px; border-radius: 20px; background: #dafbe1; color: #1a7f37; border: 1px solid #aceebb; margin-bottom: 1.5rem; }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: #1a7f37; animation: pulse 2s infinite; flex-shrink: 0; }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.4; } }
  h1 { font-size: 24px; font-weight: 700; margin-bottom: 0.4rem; color: #1a1f2e; letter-spacing: -.3px; }
  .subtitle { font-size: 14px; color: #57606a; line-height: 1.6; margin-bottom: 2rem; }
  .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 2rem; }
  .metric { background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 8px; padding: 1rem 1.25rem; }
  .metric-label { font-size: 11px; font-weight: 600; color: #57606a; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .05em; }
  .metric-value { font-size: 28px; font-weight: 700; color: #1a1f2e; letter-spacing: -.5px; }
  .metric-value.accent { color: #0969da; }
  .metric-sub { font-size: 12px; color: #57606a; margin-top: 3px; }
  .section-label { font-size: 11px; font-weight: 600; color: #57606a; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 10px; }
  .endpoints { display: flex; flex-direction: column; gap: 6px; margin-bottom: 2rem; }
  .endpoint { display: flex; align-items: center; gap: 10px; padding: 9px 14px; background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px; font-size: 13px; }
  .method { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; min-width: 52px; text-align: center; font-family: 'SF Mono', 'Fira Code', monospace; }
  .get  { background: #ddf4ff; color: #0550ae; border: 1px solid #a5d6fb; }
  .post { background: #dafbe1; color: #1a7f37; border: 1px solid #aceebb; }
  .patch{ background: #fff8c5; color: #7d4e00; border: 1px solid #f5c518; }
  .path { flex: 1; color: #1a1f2e; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; }
  .desc { font-size: 12px; color: #57606a; }
  .footer { display: flex; align-items: center; justify-content: space-between; padding-top: 1.5rem; border-top: 1px solid #d0d7de; font-size: 12px; color: #57606a; }
  .footer a { color: #0969da; text-decoration: none; font-weight: 500; }
  .footer a:hover { text-decoration: underline; }
  .thesis-tag { background: #fbefff; color: #8250df; border: 1px solid #d8b9f8; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  @media (max-width: 520px) { .metrics { grid-template-columns: 1fr; } .container { padding: 1.5rem; } h1 { font-size: 20px; } }
</style>
</head>
<body>
<div class="container">
  <div class="badge"><span class="dot"></span>live · devops-agent-demo.onrender.com</div>
  <h1>devops-agent-demo</h1>
  <p class="subtitle">Task Management REST API — Spring Boot 3.5 · PostgreSQL · Java 21<br>CI/CD remediation agent benchmark substrate · Master's thesis, Marian Cap 2026</p>

  <div class="metrics">
    <div class="metric">
      <div class="metric-label">Agent success rate</div>
      <div class="metric-value accent">96.4%</div>
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
    <span class="thesis-tag">disertație 2026</span>
    <a href="https://github.com/mariancap/devops-agent-demo" target="_blank">github.com/mariancap/devops-agent-demo</a>
  </div>
</div>
</body>
</html>
""";
        return ResponseEntity.ok(html);
    }
}
