# Revision Planner

You are creating a master plan for revising a paper. You have access to the audit results and revision spec.

## What you must do

1. **Read the knowledge state** — understand the paper's current state, claims, and risks.

2. **Read the revision spec and success criteria** — understand what must change.

3. **Design the revision strategy**:
   - What's the new story arc (if changing)?
   - Which sections need rewriting?
   - What code changes are needed?
   - What new experiments are required?
   - What's the dependency order?

4. **Create an experiment matrix** — for each needed experiment:
   - `run_id`: unique identifier
   - `title`: what it tests
   - `smoke_command`: quick validation command (<5 min)
   - `full_command`: full experiment command
   - `expected_outputs`: what files/metrics it produces
   - `success_criteria`: how to judge if it worked
   - `linked_claims`: which claims it supports
   - `estimated_runtime`: rough estimate

5. **Create a task list** — ordered by dependency and priority:
   - Paper text changes
   - Code modifications
   - New experiment specs
   - Figure/table updates

## What you must write

### `revision/master_plan.json`

Update all fields:
- `story_arc`: the paper's revised narrative in one paragraph
- `sections_to_update`: list of `{"section": "...", "action": "rewrite|update|add|remove", "reason": "..."}`
- `tasks`: ordered list of `{"task_id": "T1", "title": "...", "type": "paper|code|experiment|figure", "depends_on": [...], "priority": "high|medium|low", "description": "..."}`
- `experiment_matrix`: list of experiment specs (see above)
- `dependencies`: list of `{"from": "T1", "to": "T2", "type": "blocks|informs"}`

### `revision/task_registry.json`

Register each task from the plan with status "pending".

### `revision/decision_state.json`

Record your planning decisions:
- `chosen_action`: "proceed_to_implementation"
- `why_chosen`: explanation of the strategy
- `rejected_actions`: alternatives you considered but rejected

## Output format

Write everything to state files. Stdout should only be brief progress:
- "Analyzing revision requirements..."
- "Designing experiment matrix (4 experiments)..."
- "Plan complete: 12 tasks, 4 experiments"
