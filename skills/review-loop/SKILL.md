# Review Loop — Detailed Skill Guide

This is the comprehensive reference for the automated paper review loop. The slash command `review-loop.md` provides the step-by-step protocol; this document provides the detailed strategy and guidelines.

## Architecture

The review loop is a cycle of: **Review → Plan → Checkpoint → Modify → Validate → Record**

Each round aims to improve the paper's quality score across five dimensions:
1. **Clarity**: Are claims precise and unambiguous?
2. **Narrative**: Does the paper tell a compelling, logical story?
3. **Experimental Design**: Do experiments adequately support claims?
4. **AI Flavor**: Does the writing sound natural (not AI-generated)?
5. **Readability**: Is the prose well-crafted and easy to follow?

## SubAgent Dispatch Strategy

The review loop can dispatch work to specialized subagents for parallelism:

### When to use subagents
- **Batch A actions** (low-risk text changes): Can dispatch a rewriter subagent per section
- **Independent validations**: Compile check and test run can happen in parallel
- **Multi-file reviews**: Reading paper source and code can happen in parallel

### When NOT to use subagents
- **High-risk structural changes**: Must be done sequentially with validation between each
- **Changes with dependencies**: If action B depends on action A, run sequentially
- **Final summary**: Needs all round data, must run after everything else

### SubAgent prompts
Use the prompt templates in the `prompts/` directory:
- `reviewer.md` — for the review phase
- `planner.md` — for creating the action plan
- `rewriter.md` — for executing text changes
- `summarizer.md` — for round summaries

## De-AI Strategy (Key Differentiator)

This is the primary value proposition of this tool. The AI flavor dimension should receive special attention.

### Phase 1: Detection
During review, scan for all 50+ patterns listed in `prompts/rewriter.md`. Produce an explicit list with:
- Exact text matched
- Location (file, section, approximate line)
- Severity (obvious AI tell vs. borderline)

### Phase 2: Prioritized Replacement
1. **Obvious AI tells first** (hedging phrases, overclaiming) — these are easy wins
2. **Structural patterns next** (repetitive "First... Second..." lists, robotic enumeration)
3. **Subtle patterns last** (passive voice overuse, vague quantifiers) — higher risk of changing meaning

### Phase 3: Voice Calibration
After mechanical replacement, read the modified sections for:
- Consistency of voice (don't introduce a different kind of artificiality)
- Technical accuracy (did the rewrite change any claims?)
- Flow (do the replacements read naturally in context?)

## Failure Handling Strategy

### Compilation Failure
1. Parse the error log to identify the issue
2. Common fixes: missing closing brace, broken reference, bad figure path
3. Apply fix and recompile
4. If the fix doesn't work → rollback the entire round
5. Do NOT attempt multiple speculative fixes

### Test Failure
1. Check if the failure is related to paper changes (unlikely but possible if code was modified)
2. If tests were passing before this round, the failure is likely from our changes
3. Revert the specific code change that caused the failure
4. Re-run tests
5. If still failing → rollback

### Score Regression
If a round's score is lower than the previous round in any dimension:
- Note the regression in the round summary
- If overall score decreased → consider rollback
- If only AI flavor decreased (can happen when making other changes) → flag for next round

## Configuration Deep Dive

### `review.stop_on_plateau`
Tracks the last N rounds' overall scores. If the max improvement across these rounds is < 0.1, trigger plateau stop. This prevents endless micro-improvements.

### `review.stop_on_fail`
Tracks consecutive validation (compile + test) failures. Distinct from individual-round fix attempts — this counts rounds where the final state was a rollback.

### `git.auto_checkpoint`
When true, the system automatically commits and tags before each round. When false, it only tags (useful if the user wants to manage their own commits).

## Output Artifacts

After a complete loop, the user's project will contain:

```
reviews/
├── round-01-review.md      # Structured review
├── round-01-plan.md         # Action plan
├── round-01-changes.md      # What was changed
├── round-01-validation.md   # Round summary
├── round-02-review.md
├── ...
status/
├── current.json             # Latest status
└── history.jsonl            # Full history
logs/
├── latex/                   # Compilation logs
├── tests/                   # Test logs
└── notifications/           # Notification records
```

## Best Practices

1. **Start with a compilable paper**: The tool assumes the paper compiles at the start.
2. **Have tests if you have code**: Even basic smoke tests help catch regressions.
3. **Review the AI's review**: The generated reviews are starting points, not gospel.
4. **Commit between manual and auto changes**: Don't mix human edits with auto-review rounds.
5. **Check diff after each round**: Use `git diff review-round-N-start..HEAD` to see exactly what changed.
