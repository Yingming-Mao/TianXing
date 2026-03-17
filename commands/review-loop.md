# Review Loop

Run an automated paper review and improvement cycle.

## Protocol

Follow these steps in order. If any step fails, handle according to the failure rules below.

### 1. Pre-check

```bash
python -m paper_review_tools.compile_paper
```

If compilation fails, stop and report. The paper must compile before review begins.

Check git status — the repo must be a git repository.

### 2. Read Current Status

```bash
python -m paper_review_tools.update_status --round 0 --phase init --message "Starting review loop"
```

If `status/current.json` exists, read it to determine the current round number. Otherwise start at round 1.

### 3. For each round (up to `review.max_rounds` from config.yaml):

#### 3a. Checkpoint

```bash
python -m paper_review_tools.checkpoint_repo --round N
```

#### 3b. Review

Read the full paper source and any experiment code. Produce a structured review following the guidelines in the `prompts/reviewer.md` prompt template from the paper-review-tools package.

Save the review:
```bash
python -m paper_review_tools.record_round --round N --type review --content-file /tmp/review.json
```

#### 3c. Plan

Based on the review, create an action plan following `prompts/planner.md`.

Save the plan:
```bash
python -m paper_review_tools.record_round --round N --type plan --content-file /tmp/plan.json
```

#### 3d. Execute Changes

Execute the planned actions by batch group (A first, then B, etc.).

For each batch:
- Apply the changes (edit LaTeX files, modify code if needed)
- Follow the rules in AGENT.md strictly (risk levels, banned phrases, etc.)
- Use `prompts/rewriter.md` guidelines for text changes

#### 3e. Validate

```bash
python -m paper_review_tools.compile_paper
python -m paper_review_tools.run_tests
```

**If validation fails:**
1. Attempt to fix the issue (one attempt only)
2. Re-validate
3. If still failing: rollback and stop this round
   ```bash
   python -m paper_review_tools.rollback_repo --target review-round-N-start
   ```

#### 3f. Record

Save a changes summary:
```bash
python -m paper_review_tools.record_round --round N --type changes --content-file /tmp/changes.md
```

Update status with the new score:
```bash
python -m paper_review_tools.update_status --round N --phase complete --score X.X
```

Notify:
```bash
python -m paper_review_tools.notify_status --level success --message "Round N complete, score: X.X" --round N
```

#### 3g. Continue or Stop?

Check stop conditions:
- **Target score reached**: score >= `review.target_score` → STOP (success)
- **Max rounds reached**: round >= `review.max_rounds` → STOP
- **Plateau detected**: last `review.stop_on_plateau` rounds had no score improvement → STOP
- **Consecutive failures**: `review.stop_on_fail` consecutive validation failures → STOP

If none triggered, proceed to round N+1.

### 4. Final Summary

Produce a final summary following `prompts/summarizer.md` and save:
```bash
python -m paper_review_tools.record_round --round N --type validation --content-file /tmp/summary.md
python -m paper_review_tools.notify_status --level info --message "Review loop complete after N rounds"
```

Report the final status to the user.
