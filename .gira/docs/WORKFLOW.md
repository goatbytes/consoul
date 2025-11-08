# Scrum Workflow Guide for Consoul

## Overview
This project uses the Scrum workflow with sprint-based development cycles.

## Workflow States
1. **Backlog** - All tickets waiting to be worked on
2. **Sprint Backlog** - Tickets selected for the current sprint
3. **In Progress** - Actively being worked on (WIP limit: 5)
4. **Code Review** - Awaiting review (WIP limit: 3)
5. **Testing** - In QA/testing phase (WIP limit: 3)
6. **Done** - Completed tickets

## Common Commands

### Sprint Management
```bash
# Create a new sprint
gira sprint create "Sprint {number}" --duration 14

# Add tickets to sprint
gira ticket update SOUL-1 SOUL-2 --sprint SPRINT-ID

# View sprint progress
gira sprint show SPRINT-ID
```

### Daily Workflow
```bash
# Move ticket to in progress
gira ticket move SOUL-1 "in progress"

# After completing work
gira ticket move SOUL-1 review

# After review approval
gira ticket move SOUL-1 testing

# After testing passes
gira ticket move SOUL-1 done
```

## Best Practices
- Keep tickets small and focused (1-3 days of work)
- Update story points before sprint planning
- Move tickets through all stages (no skipping)
- Close sprint and conduct retrospective
