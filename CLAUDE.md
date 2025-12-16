# CLAUDE.md - Gira Usage Guide for Claude

This guide helps Claude AI agents understand how to use Gira for project management and ticket tracking in the **Consoul** project.

## 🎯 What is Gira?

Gira is a Git-native project management tool that stores all project data as JSON files in `.gira/`, enabling version control for project management data and seamless AI collaboration.

## 🚦 Workflow States Quick Reference

**IMPORTANT**: Use these exact status names to avoid errors:

| Status | Description | Usage |
|--------|-------------|-------|
| `todo` | To Do tickets | Default status for new tickets |
| `in_progress` | In Progress tickets | Maximum 5 tickets (WIP limit) |
| `review` | Review tickets | Maximum 5 tickets (WIP limit) |
| `done` | Done tickets | Final status |

⚠️ **Common Status Names**:
The valid statuses for this project are: `todo`, `in_progress`, `review`, `done`.
Use `gira status list` to see all available statuses.


## 📋 Essential Gira Commands

### Viewing Project Status
```bash
# See the kanban board with all tickets
gira board

# List all tickets with status and priority
gira ticket list

# View epics and their progress
gira epic list

# Check current sprint status
gira sprint list
```

### Working with Tickets
```bash
# Move a ticket to in-progress when starting work
gira ticket move TICKET-ID in_progress --force

# Update a ticket with progress notes
gira ticket update TICKET-ID --description "Implementation details..."

# Move completed ticket to done
gira ticket move TICKET-ID done --force

# Add comments for detailed progress tracking
gira comment add TICKET-ID -c "Progress update message"

# Alternative: Use echo for non-interactive confirmation
echo "y" | gira ticket move TICKET-ID in_progress
```

### Creating New Tickets
```bash
# Create a bug ticket (automatically goes to backlog)
gira ticket create "Fix issue description" --type bug --priority high --status backlog

# Create a feature ticket linked to an epic
gira ticket create "Add new feature" --type feature --epic EPIC-001 --status backlog

# Create a task ticket
gira ticket create "Update documentation" --type task --priority medium --status backlog

# Get machine-readable output for processing
gira ticket create "New ticket" --type feature --format json
```

## 🤖 Agent-Friendly Commands

### Non-Interactive Operations
```bash
# Skip confirmations with --force flag
gira ticket move TICKET-ID in_progress --force
gira ticket move TICKET-ID done --force

# Use echo for confirmation prompts
echo "y" | gira ticket move TICKET-ID in_progress

# Get JSON output for machine processing
gira ticket list --format json
gira ticket show TICKET-ID --format json
gira board --format json
```

## 🚀 Complete Workflow Examples

### Basic Bug Fix Workflow
```bash
# 1. Create bug ticket
gira ticket create "Fix authentication login failures" --type bug --priority high --status backlog

# 2. Start work (move to in-progress)
gira ticket move SOUL-1 in_progress --force

# 3. Add progress comment
gira comment add SOUL-1 -c "Investigated JWT token expiration issue"

# 4. Complete work
gira ticket move SOUL-1 done --force

# 5. Verify completion
gira ticket show SOUL-1
```

### Epic Management Workflow
```bash
# Create epic
gira epic create "User Management System" --description "Complete user authentication and profile features"

# Create tickets linked to epic
gira ticket create "Implement user registration" --type feature --epic EPIC-001 --status backlog
gira ticket create "Add password reset functionality" --type feature --epic EPIC-001 --status backlog
gira ticket create "Create profile editing interface" --type feature --epic EPIC-001 --status backlog

# Check epic progress
gira epic show EPIC-001
```

## 📝 Git Integration

### Commit Message Format

**With Gira Ticket:**
```bash
git commit -m "feat(TICKET-ID): implement feature description

- Add detailed implementation notes
- Include test coverage information
- Document any breaking changes

Gira: TICKET-ID"
```

**Without Gira Ticket (Fallback):**
```bash
git commit -m "refactor: improve code organization

- Extract common functions
- Reduce code duplication
- Improve maintainability

Relates-to: general improvements"
```

**Multiple Tickets:**
```bash
git commit -m "test(TICKET-1,TICKET-2): improve test coverage

- Add comprehensive unit tests
- Implement integration testing
- Increase coverage metrics

Gira: TICKET-1, TICKET-2"
```

## 🔍 Finding and Tracking Work

### Search Commands
```bash
# Filter tickets by status
gira ticket list --status in_progress

# Filter by priority
gira ticket list --priority high

# Filter by type
gira ticket list --type bug

# Combine filters
gira ticket list --status backlog --priority high --type feature

# Get JSON output for processing
gira ticket list --status in_progress --format json
```

### Understanding Code Context
```bash
# Find tickets that modified a file
gira ticket blame src/main.py

# Find tickets for specific lines
gira ticket blame src/main.py -L 10,20

# Get JSON output for processing
gira ticket blame src/main.py --json
```

## 💡 Claude-Specific Tips

### Using TodoWrite with Gira
When working on complex tasks, you can use Claude's TodoWrite tool to track subtasks while linking them to Gira tickets:

1. Create a todo list for breaking down a Gira ticket
2. Reference the ticket ID in your todos
3. Update the Gira ticket as you complete todos

### Progress Documentation
Claude should be particularly detailed when using `gira comment add`:
- Document technical decisions
- Explain implementation approaches
- Note any challenges or blockers
- Reference related code changes

### Handling Multiple Tickets
When working on related tickets:
```bash
# View all tickets in an epic
gira epic show EPIC-001

# List tickets with dependencies
gira ticket show TICKET-ID  # Check the description for dependencies
```

## 🚨 Common Scenarios

### Blocked Ticket
```bash
# Mark as blocked
gira ticket move TICKET-ID blocked

# Add blocking reason
gira comment add TICKET-ID
# Explain what's blocking progress
```

### Finding Related Work
```bash
# Search by keyword in titles
gira ticket list | grep -i "authentication"

# View epic progress
gira epic list
gira epic show EPIC-001
```

### Sprint Work
```bash
# View current sprint
gira sprint current

# List sprint tickets
gira sprint show SPRINT-ID
```

## 📊 Progress Tracking

### Daily Updates
```bash
# Check your assigned tickets
gira ticket list --assignee me

# View in-progress work
gira ticket list --status in_progress

# Update ticket progress
gira comment add TICKET-ID
```

### Ticket Lifecycle
1. `todo` → `in_progress` → `review` → `done`
2. Use proper status names to avoid errors (run `gira status list`)
3. Add comments at each transition

## 🔧 Common Issues & Solutions

| Error | Solution |
|-------|----------|
| "Invalid status 'todo'" | Use `backlog` instead |
| "Invalid status 'review'" | Use `done` instead |
| Command hangs on confirmation | Add `--force` flag or use `echo "y" \|` |
| "No such ticket" | Check ticket ID format (SOUL-123) |
| Interactive command issues | Use `--force` flags for automation |

## ✅ Command Verification

After each operation, verify success:

```bash
# After creating ticket
gira ticket show TICKET-ID

# After moving ticket
gira board

# After adding comment
gira ticket show TICKET-ID

# Check overall project status
gira ticket list
```

## 🛠️ Best Practices for Claude

1. **Always Check Current State**: Run `gira ticket show TICKET-ID` before starting work
2. **Document Thoroughly**: Use comments to explain your approach and decisions
3. **Update Regularly**: Move tickets through the workflow as you progress
4. **Reference in Commits**: Always include ticket IDs in commit messages
5. **Break Down Complex Work**: Create subtasks for large tickets
6. **Never Run the TUI**: Don't run `consoul` or TUI apps from chat sessions. Ask the user to test instead.

---

*This guide helps Claude work effectively with Gira's Git-native project management system.*
