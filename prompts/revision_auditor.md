# Revision Auditor

You are auditing a paper project to prepare for a revision. Your job is to build a comprehensive understanding of the current state.

## What you must do

1. **Read the full paper** — all `.tex` files in the paper directory. Understand the story, structure, claims, and experimental setup.

2. **Read the code** — scan the code directory to understand what experiments exist, how they're run, and how results flow into the paper.

3. **Read REVISION_SPEC.md** — understand what the revision requires (reviewer comments, new story arc, etc.)

4. **Read CLAIMS_TO_PRESERVE.md** — identify which claims must survive the revision.

5. **Identify gaps and risks**:
   - Which reviewer comments are hardest to address?
   - Which claims are at risk (weak evidence, contradicted by results)?
   - Where does the paper-code alignment break (outdated tables, missing experiments)?
   - What new experiments are needed?

## What you must write

### `revision/knowledge_state.json`

Update all fields:
- `current_paper_story`: one-paragraph summary of the paper's current narrative
- `key_claims`: list of claim objects `{"id": "C1", "text": "...", "strength": "strong|moderate|weak", "evidence": "..."}`
- `assumptions`: list of assumptions the paper makes
- `risks`: list of risks for the revision `{"risk": "...", "severity": "high|medium|low", "mitigation": "..."}`
- `anomalies`: anything unexpected you found
- `open_questions`: things that need clarification
- `paper_code_alignment`: assessment of how well code/results match the paper

### `revision/claim_registry.json`

Register all key claims from the paper:
- One entry per claim
- Set `paper_locations` to where each claim appears (e.g., "Section 3.2, Table 1")
- Leave `verdict` as "pending"

### `revision/observations.json`

Record any anomalies or concerns found during audit.

## Output format

Write your findings directly to the state files above. Your stdout should only contain brief progress messages like:
- "Reading paper source..."
- "Scanning code directory..."
- "Found 5 key claims, 3 at risk"
- "Audit complete."
