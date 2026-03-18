# Revision Writeback

You are updating the paper text based on verified experiment results and the master plan.

## What you must do

### Draft mode (`mode: "draft"`)

1. Generate candidate text updates for each section in the plan's `sections_to_update`.
2. For each update, check that it's supported by verified claims.
3. Write draft text to `revision/artifacts/writeback_draft_<section>.tex`.
4. Mark these as "provisional" in the task registry.

### Final mode (`mode: "final"`)

1. Only use VERIFIED claims from the claim registry.
2. Update the actual paper files:
   - Abstract — if claims changed
   - Results sections — with new numbers and analysis
   - Discussion — reflecting new findings
   - Captions — for updated tables/figures
   - Introduction — if the story arc changed
3. Ensure consistency across all sections.
4. Update task statuses to "completed".

## Rules

- **NEVER write claims that aren't verified.** If a claim is "pending" or "contradicted", do not include it in the paper.
- If a contradicted claim was in the original paper, flag it for human review rather than silently removing it.
- Preserve the paper's writing style and voice.
- Update all cross-references (table numbers, figure references, equation references).
- After final writeback, the paper must still compile.

## What you must write

### Draft mode
- `revision/artifacts/writeback_draft_*.tex` — candidate text
- `revision/task_registry.json` — mark draft tasks as "completed"

### Final mode
- Actual paper `.tex` files — with updated text
- `revision/task_registry.json` — mark final writeback tasks as "completed"

## Output format

Stdout:
- "Drafting writeback for Section 3 (Results)..."
- "Using 4 verified claims, skipping 1 pending"
- "Writeback complete. Updated: abstract, section 3, section 4, table 2 caption"
