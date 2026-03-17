# Paper Review Agent — Project Rules

This project uses `paper-review-tools` for automated paper review and improvement.

## Project Structure

```
paper/          — LaTeX source files
code/           — Experiment code
results/        — Experiment outputs (data, figures)
reviews/        — Auto-generated review artifacts
logs/           — Compilation and test logs
status/         — Review progress tracking
config.yaml     — Project configuration
```

## Tool Invocation

All tools are called via `python -m paper_review_tools.<module>`. Every tool outputs JSON to stdout.

| Command | Usage |
|---------|-------|
| checkpoint | `python -m paper_review_tools.checkpoint_repo --round N` |
| rollback | `python -m paper_review_tools.rollback_repo --target TAG` |
| compile | `python -m paper_review_tools.compile_paper` |
| test | `python -m paper_review_tools.run_tests` |
| record | `python -m paper_review_tools.record_round --round N --type TYPE --content-file PATH` |
| status | `python -m paper_review_tools.update_status --round N --phase PHASE --score X` |
| notify | `python -m paper_review_tools.notify_status --level info --message "..."` |
| metrics | `python -m paper_review_tools.collect_metrics` |

## Paper Editing Rules

1. **Preserve LaTeX structure**: Do not remove or rename `\section`, `\subsection` etc. without explicit approval.
2. **Keep all citations**: Never remove `\cite{}` references. You may add new ones.
3. **Keep all figures/tables**: Do not delete `\begin{figure}` or `\begin{table}` environments. You may modify captions and content.
4. **Incremental edits**: Make focused changes; do not rewrite entire sections at once.
5. **Compile after edits**: Always run `python -m paper_review_tools.compile_paper` after modifying .tex files.

## Writing Style — De-AI Rules

The following phrases and patterns are **banned**. They signal AI-generated text:

### Banned Hedging / Filler
- "It is worth noting that..."
- "It should be noted that..."
- "Importantly, ..."
- "Notably, ..."
- "Interestingly, ..."
- "In this regard, ..."
- "In summary, ..." (at the start of paragraphs that are not summaries)
- "Overall, ..."
- "Specifically, ..." (when not actually specifying)
- "Furthermore, ..." / "Moreover, ..." (excessive chaining)

### Banned Overclaiming
- "groundbreaking" / "revolutionary" / "paradigm-shifting"
- "novel" (use only if truly first-of-its-kind)
- "state-of-the-art" (only if actually SOTA with evidence)

### Banned Vague Quantifiers
- "significantly" (use only with statistical significance)
- "dramatically" / "substantially" / "remarkably"

### Style Goals
- Use direct, active voice
- Let results speak for themselves
- Be precise: replace vague words with numbers
- Write like a domain expert, not a press release
- Vary sentence structure; avoid repetitive patterns

## Safety Rules

1. **Always checkpoint before modifications**: `python -m paper_review_tools.checkpoint_repo --round N`
2. **Rollback on failure**: If compilation or tests fail after one fix attempt, rollback immediately.
3. **Never force-push**: Git operations must be non-destructive beyond the managed tags.
4. **Record everything**: Every round must produce a record via `record_round`.

## Modification Risk Levels

| Risk | Examples | Rule |
|------|----------|------|
| Low | Fix typos, improve wording, add transitions | Execute freely |
| Medium | Rewrite paragraphs, restructure arguments, modify figures | Execute with compile check |
| High | Add/remove sections, change methodology description, alter results presentation | Require explicit approval |

## Stop Conditions

The review loop must stop when any of these conditions is met:
- Target score reached (config: `review.target_score`)
- Maximum rounds reached (config: `review.max_rounds`)
- Score plateau detected (config: `review.stop_on_plateau` consecutive rounds with no improvement)
- Consecutive validation failures (config: `review.stop_on_fail`)
