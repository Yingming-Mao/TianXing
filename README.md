# Paper Review Tools

English | [中文](README_CN.md)

Automated paper review and improvement tools for [Claude Code](https://claude.ai/claude-code). This is an **independent tool repository** — install it once, then use it across your paper projects.

The system runs a Review → Plan → Modify → Validate → Record loop to iteratively improve your paper. Key focus: **removing AI-generated writing patterns** and improving narrative quality.

## Installation

```bash
git clone https://github.com/yourname/paper-review-tools.git
cd paper-review-tools
pip install -e .
```

## Quick Start

### 1. Initialize your paper project

```bash
cd /path/to/your-paper-project
bash /path/to/paper-review-tools/scripts/setup_project.sh
```

This creates the required directory structure and copies config templates.

### 2. Configure

Edit `config.yaml` in your paper project to match your setup:

```yaml
compile:
  main_file: "paper/main.tex"
tests:
  command: "pytest"
  smoke_test_dir: "code/tests"
```

### 3. Run the review loop

Open Claude Code in your paper project and run:

```
/review-loop
```

## Tools

All tools output structured JSON and are invoked via `python -m paper_review_tools.<module>`.

| Tool | Purpose |
|------|---------|
| `checkpoint_repo` | Create git checkpoint before modifications |
| `rollback_repo` | Roll back to a previous checkpoint |
| `compile_paper` | Compile LaTeX and report errors/warnings |
| `run_tests` | Run project tests |
| `record_round` | Save review artifacts (review, plan, changes) |
| `update_status` | Track review progress and scores |
| `notify_status` | Log notifications |
| `collect_metrics` | Scan results directory for metrics |

You can also use the CLI: `paper-review-tools <command> [args]`

## Project Structure

```
paper_review_tools/     Python package (pip-installable)
commands/               Claude Code slash command
skills/                 Detailed skill prompts
prompts/                SubAgent prompt templates (reviewer, planner, rewriter, summarizer)
templates/              Files copied to user projects (AGENT.md, .gitignore)
scripts/                Project initialization script
```

## How It Works

Each review round:

1. **Checkpoint** — tags the current git state
2. **Review** — analyzes paper for clarity, narrative, experimental design, AI flavor, readability
3. **Plan** — prioritizes improvements by impact/risk ratio
4. **Modify** — applies changes (low-risk batched, high-risk isolated)
5. **Validate** — compiles paper, runs tests; rolls back on failure
6. **Record** — saves artifacts, updates scores, checks stop conditions

The loop stops when: target score is reached, max rounds exceeded, score plateaus, or validation keeps failing.

## Configuration

See `config.example.yaml` for all options. Key settings:

- `review.max_rounds` — maximum improvement rounds (default: 3)
- `review.target_score` — stop when this score is reached (default: 8.0)
- `review.stop_on_plateau` — stop after N rounds with no improvement
- `compile.main_file` — path to your main .tex file
- `tests.command` — test runner command

## License

MIT
