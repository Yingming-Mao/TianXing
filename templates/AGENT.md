# Paper Review Agent — Project Rules

This project uses `TianXing` for automated paper review and improvement.

## Project Structure

```
paper/          — LaTeX source files
code/           — Experiment code
results/        — Experiment outputs (data, figures)
reviews/        — Auto-generated review artifacts
logs/           — Compilation and test logs
status/         — Review progress tracking
config.yaml              — Project configuration
experiment_map.json      — Paper↔code↔test↔result mappings (auto-generated, editable)
```

## Experiment Map

The file `experiment_map.json` maps paper sections to code, tests, and results bidirectionally. It is auto-generated on first run and updated each round. You can also edit it manually.

| Command | Usage |
|---------|-------|
| discover | `python -m tianxing.experiment_map --action discover` |
| query by ID | `python -m tianxing.experiment_map --action query --id "tab:results"` |
| query by path | `python -m tianxing.experiment_map --action query --path "code/train.py"` |
| validate | `python -m tianxing.experiment_map --action validate` |

**When reviewing**: Use the map to understand which code produces which tables/figures.
**When modifying code**: Query the map to find which tests to run and which paper sections to update.
**When a review targets a table/figure**: Query the map to find the responsible code.

## Tool Invocation

All tools are called via `python -m tianxing.<module>`. Every tool outputs JSON to stdout.

| Command | Usage |
|---------|-------|
| checkpoint | `python -m tianxing.checkpoint_repo --round N` |
| rollback | `python -m tianxing.rollback_repo --target TAG` |
| compile | `python -m tianxing.compile_paper` |
| test | `python -m tianxing.run_tests` |
| record | `python -m tianxing.record_round --round N --type TYPE --content-file PATH` |
| status | `python -m tianxing.update_status --round N --phase PHASE --score X` |
| notify | `python -m tianxing.notify_status --level info --message "..."` |
| metrics | `python -m tianxing.collect_metrics` |
| map | `python -m tianxing.experiment_map --action ACTION` |

## Paper Editing Rules

1. **Preserve LaTeX structure**: Do not remove or rename `\section`, `\subsection` etc. without explicit approval.
2. **Keep all citations**: Never remove `\cite{}` references. You may add new ones.
3. **Keep all figures/tables**: Do not delete `\begin{figure}` or `\begin{table}` environments. You may modify captions and content.
4. **Incremental edits**: Make focused changes; do not rewrite entire sections at once.
5. **Compile after edits**: Always run `python -m tianxing.compile_paper` after modifying .tex files.

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

1. **Always checkpoint before modifications**: `python -m tianxing.checkpoint_repo --round N`
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
