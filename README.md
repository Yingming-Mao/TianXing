# TianXing

English | [中文](README_CN.md)

Automated paper review, improvement, and revision tools for [Claude Code](https://claude.ai/claude-code). Install once, use across all your paper projects.

### Two Modes, Full Paper Lifecycle

| | **Review** (`/review-loop`) | **Revise** (`tianxing revise`) |
|---|---|---|
| When | Before submission — self-polish | After reviews — address reviewer comments |
| How | Single Claude Code session | Python orchestrator + Claude as worker |
| Experiments | No new experiments | Runs new experiments (background, resumable) |
| Duration | Minutes | Hours to days |
| Safety | Git checkpoint + rollback | Claim-gated writeback + human confirmation |

```
Write draft → review-loop (polish) → Submit → Get reviews → revise (address comments) → Resubmit
```

### Why TianXing?

- **Venue-calibrated review** — scoring adapts to your target venue's actual standards (auto-fetched from the web). Works for ML conferences, OR journals, energy/power systems, and more.
- **Substance over polish** — technical soundness and novelty carry 45% of the score weight. Surface-level text fixes alone won't inflate your rating.
- **Experiment-aware** — auto-built knowledge graph maps paper sections ↔ code ↔ tests ↔ results. When a table is weak, the agent traces it back to the code that produced it.
- **Safe by default** — git checkpoints before every round, automatic rollback on failure, risk-tiered modifications. Revision writeback is gated by verified claims only.

## Installation

```bash
git clone https://github.com/Yingming-Mao/TianXing.git
cd TianXing
pip install -e .
```

Requires Python >= 3.8 and [Claude Code](https://claude.ai/claude-code) installed.

## Quick Start: Review Loop (Pre-Submission)

### 1. Initialize your paper project

```bash
cd /path/to/your-paper-project
bash /path/to/TianXing/scripts/setup_project.sh
```

### 2. Configure

Edit `config.yaml` in your paper project:

```yaml
review:
  venue: "NeurIPS 2026"        # your target venue — the reviewer calibrates to its standards
  # venue: "Applied Energy"    # energy/power systems
  # venue: "Operations Research"  # OR/management science
  # venue: "IEEE TSG"          # smart grid / power systems
  # if left empty, the agent reads your paper and infers the best-fit venue

compile:
  main_file: "paper/main.tex"

project:
  env: "myenv"                # conda env name (or path, or venv python path; leave empty for current env)
```

### 3. Run

Open Claude Code in your paper project:

```
/review-loop
```

## Quick Start: Revision (Post-Review)

### 1. Initialize revision scaffolding

```bash
cd /path/to/your-paper-project
tianxing revise-setup
```

This creates two directories:

```
tianxing_revision/              ← You fill these in
  REVISION_SPEC.md              ← Reviewer comments + revision goals (main file)
  SUCCESS_CRITERIA.md           ← What "done" looks like
  CLAIMS_TO_PRESERVE.md        ← Core claims that must survive the revision
  EXPERIMENT_RULES.yaml         ← Experiment rules (smoke first, confirm before full runs)
  EXECUTION_ENV.yaml            ← Runtime environment (conda/GPU/proxy)
  OPERATOR_NOTES.md             ← Runtime notes you can edit anytime
  MANUAL_OVERRIDES.yaml         ← Skip phases, force reruns, etc.

revision/                       ← Managed by the system (don't edit)
  state.json                    ← Phase state machine
  knowledge_state.json          ← System's understanding of the paper
  master_plan.json              ← Active revision plan
  task_registry.json            ← Task tracking
  result_registry.json          ← Experiment run tracking
  claim_registry.json           ← Paper claim verification status
  ...
```

### 2. Fill in your revision spec

Edit `tianxing_revision/REVISION_SPEC.md` with reviewer comments and goals:

```markdown
# Revision Specification

## Reviewer Comments

### Reviewer 1
- Lacks large-scale experiment (1000 EVs)
- Baseline in Table 1 is unfair

### Reviewer 2
- Narrative unclear, restructure introduction
- Add ablation study

## Revision Goals
- Add 1000-EV experiment to strengthen scalability claim
- Rewrite intro with service-envelope framing
- Add ablation to isolate component contributions

## New Story Arc
From "we propose a method" to "service-envelope is a scalable EV charging framework"
```

Edit `tianxing_revision/CLAIMS_TO_PRESERVE.md` with claims that must not be lost:

```markdown
## Core Claims
1. Service envelope reduces charging cost by 15% (Table 1)
2. Method converges within 50 iterations (Figure 3)
```

Check `tianxing_revision/EXECUTION_ENV.yaml` if your experiments need a specific conda env or GPU.

### 3. Run

**Interactive (recommended for first use)** — step by step in Claude Code:

```
/revise-loop
```

**Autonomous** — Python orchestrator drives the full loop:

```bash
tianxing revise
```

**Check status anytime:**

```bash
tianxing revise-state --action get
```

**Confirm when the system asks** (e.g., before full experiment runs):

```bash
tianxing revise-state --action confirm
```

### How Revision Works

The system runs an observe–reason–act loop:

```
INIT → AUDIT → PLAN → IMPLEMENT → SMOKE_TEST → [human confirm] → FULL_RUN → VERIFY → WRITEBACK → FINALIZE
```

- **Python orchestrator** owns runtime: state machine, experiment scheduling, monitoring
- **Claude Code** owns cognition: audits the paper, plans changes, writes code/text, verifies results
- **File system** is the shared protocol: all state in `revision/*.json`, no reliance on stdout

Key safety features:
- Full experiment runs require human confirmation
- Only **verified** claims are written back to the paper
- Claude workers get per-role minimal permissions (auditor can't edit code, verifier can't edit paper)
- All state persists to disk — crash and resume anytime

## Tools

All tools output structured JSON and are invoked via `tianxing <command>` or `python -m tianxing.<module>`.

| Tool | Purpose |
|------|---------|
| `checkpoint_repo` | Create git checkpoint before modifications |
| `rollback_repo` | Roll back to a previous checkpoint |
| `compile_paper` | Compile LaTeX and report errors/warnings |
| `run_tests` | Run project tests (when code is modified and tests are enabled) |
| `record_round` | Save review artifacts (review, plan, changes) |
| `update_status` | Track review progress and scores |
| `notify_status` | Log notifications |
| `collect_metrics` | Scan results directory for metrics |
| `experiment_map` | Auto-discover and query paper↔code↔test↔result mappings |
| `revise-setup` | Initialize revision directory structure and templates |
| `revise` | Run the revision orchestration loop |
| `revise-state` | Inspect/manage revision state (get, confirm, reset) |

## Project Structure

```
tianxing/                Python package (pip-installable)
  revision/             Revision orchestrator modules
commands/               Claude Code slash commands (review-loop, revise-loop)
prompts/                Agent prompt templates (reviewer, planner, rewriter, 6 revision roles)
skills/                 Detailed skill prompts
templates/              Files copied to user projects (AGENT.md, .gitignore)
scripts/                Project initialization script
tests/                  Test suite (73 tests)
```

## Experiment Map

TianXing automatically builds and maintains an `experiment_map.json` that bidirectionally maps:

- **Paper sections** (sections, tables, figures) ↔ **Code files** that produce them
- **Code files** ↔ **Test commands** that verify them
- **Code files** ↔ **Result files** (data, figures) they produce

```bash
tianxing map --action discover   # scan and generate
tianxing map --action query --id "tab:results"   # find related code/tests
tianxing map --action query --path "code/train.py"  # find related tests/sections
```

## Configuration

See `config.example.yaml` for all options. Key settings:

- `review.venue` — target venue (e.g. `"NeurIPS 2026"`, `"Applied Energy"`, `"IEEE TSG"`). If empty, the agent infers from paper content.
- `project.env` — experiment runtime environment: conda env name, path, or venv python path
- `review.max_rounds` — maximum improvement rounds (default: 3)
- `review.target_score` — stop when this score is reached (default: 7.0)
- `compile.main_file` — path to your main .tex file
- `tests.enabled` — enable test runner (default: false)

## License

MIT
