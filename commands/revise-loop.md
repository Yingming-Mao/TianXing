# Revise Loop

Run the revision orchestration loop for a paper project.

## Protocol

This slash command is the Claude Code entry point for the revision system. It is a **UI layer** — the actual runtime logic lives in the Python orchestrator.

### 1. Pre-check

Verify the revision is initialized:

```bash
ls tianxing_revision/REVISION_SPEC.md revision/state.json
```

If not found, initialize first:

```bash
python -m tianxing.revision.revision_setup
```

Then ask the user to fill in the template files in `tianxing_revision/` before continuing.

### 2. Check Current State

```bash
python -m tianxing.revision.revision_state_cli --action get
```

Display the current phase, status, and any blockers to the user.

### 3. Run the Loop

If the state is not blocked and there's work to do:

```bash
python -m tianxing.revision.revision_loop --once
```

This runs a single iteration of the orchestration loop. Show the user what action was taken and the result.

### 4. Human Confirmation

If the state shows `blocked: true`, explain what needs confirmation and ask the user. When they confirm:

```bash
python -m tianxing.revision.revision_state_cli --action confirm
```

Then run the loop again.

### 5. Continue or Stop

After each iteration, check state again and ask the user if they want to continue, or if they want to modify any input files before the next step.

### Important Notes

- This command runs ONE iteration at a time, giving the user control at each step.
- For fully autonomous operation, users can run `tianxing revise` directly from the terminal.
- The `/revise-loop` command is for interactive, step-by-step execution within Claude Code.
- Always show the user what happened after each step.
- If an action fails, show the error and suggest next steps.
