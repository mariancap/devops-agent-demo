# SUBMISSION.md — Instrucțiuni pentru Comisia de Dizertație

> **Titlul tezei:**  
> Agentic CI/CD Remediation with Claude Code: A Human-in-the-Loop System for Diagnosing and Fixing Pipeline Failures in Containerised Build Workflows

> **Autor:** Marian Cap
> **An:** 2026  
> **Repository:** https://github.com/mariancap/devops-agent-demo  
> **Tag:** `final-release`

---

## Accesul rapid la artefacte

| Artefact | Locație | Descriere |
|----------|---------|-----------|
| Raport benchmark | `report.html` | Deschide în orice browser — rezultate complete, grafice interactive |
| Concluzii | `CONCLUSIONS.md` | 5 findings principale, limitări, contribuții |
| Arhitectură | `ARCHITECTURE.md` | Pipeline complet, MCP tools, design decisions |
| Date brute | `agent/eval_logs/results_sdk.jsonl` | 28 runs, format JSONL |
| Audit logs | `agent/eval_logs/*.jsonl` | Log-uri per-sesiune cu toate evenimentele agentului |

---

## Reproducibilitatea rezultatelor

### Opțiunea 1 — Vizualizare fără rulare (recomandat pentru comisie)

Deschide direct `report.html` din repo (nu necesită nicio instalare):

```bash
git clone https://github.com/mariancap/devops-agent-demo.git
cd devops-agent-demo
git checkout final-release
# Deschide report.html în browser
```

Raportul conține toate rezultatele, graficele și analiza, generate din datele commituite în `agent/eval_logs/`.

### Opțiunea 2 — Smoke test complet (verificare setup, ~5 minute)

```bash
git clone https://github.com/mariancap/devops-agent-demo.git
cd devops-agent-demo
git checkout final-release
export ANTHROPIC_API_KEY="sk-ant-..."   # cheia dvs. Anthropic
make setup
make check-env
make bench-smoke                         # rulează 3 scenarii
```

### Opțiunea 3 — Benchmark complet (reproductibilitate totală, ~30 minute)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
make bench
```

---

## Structura contribuțiilor tehnice

### 1. Agentul de remediere (core)
- **Fișiere:** `agent/system_prompt.md`, `agent/audit_wrapper.py`, `mcp/server.py`
- **Ce face:** Diagnostichează și remediază eșecuri CI/CD prin 8 faze + 2 checkpoints umane
- **Contribuție:** Arhitectura HITL cu audit complet și izolare prin git worktree

### 2. Benchmark-ul de evaluare
- **Fișiere:** `agent/scenarios/` (28 scenarii), `agent/eval_harness_sdk.py`
- **Ce face:** Injectează mutații reproductibile și evaluează automat succesul remediei
- **Contribuție:** Dataset nou de 28 scenarii eșalonate pe 6 categorii

### 3. Baseline comparisons
- **Fișiere:** `agent/run_baseline_b1.py`, `agent/run_baseline_b2.py`, `agent/eval_logs/baselines_b*.jsonl`
- **Ce face:** Compară agentul față de zero-shot (B1) și static-only (B2)
- **Contribuție:** Demonstrează că arhitectura structurată aduce +46.4pp față de zero-shot

### 4. Raportarea și analiza
- **Fișiere:** `report.html`, `CONCLUSIONS.md`, `ARCHITECTURE.md`
- **Ce face:** Vizualizare completă, error analysis, concluzii academice

---

## Rezultate principale

```
Agent (full system):   27/28 scenarii  =  96.4%
B2 (static-only):       3/6  scenarii  =  50.0%
B1 (zero-shot):         1/6  scenarii  =  16.7%
```

Singurul eșec al agentului: `docker-compose-001` — session timeout (3733s).  
Toate celelalte 5 categorii: 100% success rate.

---

## Întrebări frecvente pentru comisie

**Q: De ce Claude Sonnet 4.6 și nu Opus?**  
A: Sonnet 4.6 este modelul recomandat pentru agentic workflows — echilibru cost/capabilitate. Studiul se concentrează pe arhitectură, nu pe alegerea modelului.

**Q: Cum se garantează reproducibilitatea dacă LLM-ul este non-determinist?**  
A: Mutațiile și criteriile de succes sunt deterministe (git diff exact). Non-determinismul LLM afectează *calea* spre fix, nu *corectitudinea* fixului. Datele commituite sunt autoritative; o nouă rulare produce ±1 scenariu din 28.

**Q: Ce înseamnă „human-in-the-loop" concret?**  
A: Agentul se oprește la CP1 (după diagnoză) și CP2 (după patch) și așteaptă aprobare explicită. În modul benchmark, aprobarea e automată; în modul interactiv, un inginer DevOps validează înainte de commit.

**Q: Există riscul că agentul modifică codul greșit și commitează?**  
A: Nu — patch-ul e aplicat într-un git worktree izolat. Commit-ul în branch-ul principal se face doar după ambele checkpoints și o validare CI (re-rulare `act`).

---

## Contactul autorului

Marian Cap  
GitHub: [@mariancap](https://github.com/mariancap)  
Repository: https://github.com/mariancap/devops-agent-demo

---

*Ultima actualizare: iunie 2026 — tag `final-release`*
