# Review Loop

Run an automated paper review and improvement cycle.

## Protocol

Follow these steps in order. If any step fails, handle according to the failure rules below.

**Important**: When writing JSON content to temp files (reviews, plans, etc.), use the **Write tool** to create the file, then pass the file path to `tianxing.record_round`. Do NOT use bash heredoc (`cat <<EOF`) to write JSON — it triggers shell security warnings.

### 1. Pre-check

```bash
python -m tianxing.compile_paper
```

If compilation fails, stop and report. The paper must compile before review begins.

Check git status — the repo must be a git repository.

### 1b. Experiment Map

If `experiment_map.enabled` is true in config, discover or update the experiment map:

```bash
python -m tianxing.experiment_map --action discover
```

This scans the project and builds a bidirectional mapping between paper sections, code files, test commands, and result files. If `experiment_map.json` already exists, new entries are merged without removing user-added ones.

Read the map and keep it available for the rest of the loop — it tells you which code produces which tables/figures, which tests verify which code, and which paper sections need updating when code changes.

### 2. Read Current Status

```bash
python -m tianxing.update_status --round 0 --phase init --message "Starting review loop"
```

If `status/current.json` exists, read it to determine the current round number. Otherwise start at round 1.

### 3. For each round (up to `review.max_rounds` from config.yaml):

#### 3a. Checkpoint

```bash
python -m tianxing.checkpoint_repo --round N
```

#### 3b. Fetch Venue Guidelines (round 1 only)

Read `review.venue` from `config.yaml`. **If venue is empty, stop the loop and ask the user to set it** — reviewing without a target venue produces meaningless scores.

On the first round, use WebSearch to find the target venue's official reviewer guidelines and call for papers. Search queries like:
- `"{venue name}" reviewer guidelines {year}`
- `"{venue name}" call for papers {year}`
- `"{venue name}" review criteria`

Use WebFetch to read the most relevant results. Extract and save the key review criteria to `/tmp/venue_guidelines.md` so they are available for all rounds. This file should contain:
- The venue's stated evaluation criteria and their relative importance
- Any specific requirements (page limits, formatting, blind review rules)
- What the venue considers grounds for acceptance vs rejection

If the search fails or returns no useful results, proceed with the venue name alone but note the limitation in the review output.

#### 3c. Review

Read the full paper source and any experiment code. **Use the experiment map** to understand which code files produce which tables/figures/results. Produce a structured review following the guidelines in the `prompts/reviewer.md` prompt template from the TianXing package. **Pass the target venue AND the fetched venue guidelines** (`/tmp/venue_guidelines.md`) to the reviewer so it can calibrate scoring to that venue's actual standards. When flagging issues with specific tables or figures, include the map entity ID (e.g. `tab:results`) in the issue's `location` field.

Save the review:
```bash
python -m tianxing.record_round --round N --type review --content-file /tmp/review.json
```

#### 3d. Plan

Based on the review, create an action plan following `prompts/planner.md`. **Use the experiment map** to populate `target_files` — when a review issue targets a table/figure, query the map to find the code that produces it, related tests, and result files.

Save the plan:
```bash
python -m tianxing.record_round --round N --type plan --content-file /tmp/plan.json
```

#### 3e. Execute Changes

Execute the planned actions by batch group (A first, then B, etc.).

For each batch:
- Apply the changes (edit LaTeX files, modify code if needed)
- Follow the rules in AGENT.md strictly (risk levels, banned phrases, etc.)
- Use `prompts/rewriter.md` guidelines for text changes

#### 3f. Validate

```bash
python -m tianxing.compile_paper
```

Only run tests if code files were modified in this round. Use the experiment map to find which specific tests to run for the modified files:
```bash
python -m tianxing.experiment_map --action query --path "path/to/modified/file.py"
```
Then run only the related test commands. If no map entry exists, fall back to the global test command (if `tests.enabled` is true):
```bash
python -m tianxing.run_tests
```

**If validation fails:**
1. Attempt to fix the issue (one attempt only)
2. Re-validate
3. If still failing: rollback and stop this round
   ```bash
   python -m tianxing.rollback_repo --target review-round-N-start
   ```

#### 3g. Record

Save a changes summary:
```bash
python -m tianxing.record_round --round N --type changes --content-file /tmp/changes.md
```

Update status with the new score:
```bash
python -m tianxing.update_status --round N --phase complete --score X.X
```

Notify:
```bash
python -m tianxing.notify_status --level success --message "Round N complete, score: X.X" --round N
```

#### 3h. Continue or Stop?

Check stop conditions:
- **Target score reached**: score >= `review.target_score` → STOP (success)
- **Max rounds reached**: round >= `review.max_rounds` → STOP
- **Plateau detected**: last `review.stop_on_plateau` rounds had no score improvement → STOP
- **Consecutive failures**: `review.stop_on_fail` consecutive validation failures → STOP

If none triggered, proceed to round N+1.

### 4. Final Summary

Produce a final summary following `prompts/summarizer.md` and save:
```bash
python -m tianxing.record_round --round N --type validation --content-file /tmp/summary.md
python -m tianxing.notify_status --level info --message "Review loop complete after N rounds"
```

Report the final status to the user.
