---
description: Sync state and coordinate tasks between Agent Personas (Antigravity & Copilot equivalent).
---
This workflow is used to synchronize development state between multiple AI agents working on the same repository. It creates a shared `AGENT_HANDOFF.md` file to log completed tasks, architectural decisions, and next steps.

1. check for existing handoff file
    - Check if `.agent/AGENT_HANDOFF.md` exists.
    - If it exists, read its content to understand the current state.
    - If it does not exist, create it with the following template:

```markdown
# Agent Handoff Log

## Current Phase
[Phase Name, e.g., Phase 0: Consolidation]

## Latest Status Update
- **Date:** [YYYY-MM-DD]
- **Agent:** [Agent Name]
- **Action:** [Brief summary of what was done]
- **Key Decision:** [Architectural choice made]

## Immediate Next Steps
1. [Task 1]
2. [Task 2]

## Blockers / Questions
- [Any issues preventing progress]
```

2. updates state
    - Append your latest actions and decisions to the "Latest Status Update" section.
    - Update "Immediate Next Steps" based on your progress.
    - Clear or add to "Blockers / Questions".

3. commit handoff
    - Commit the changes to `AGENT_HANDOFF.md` with a clear message: "chore: update agent handoff status".
