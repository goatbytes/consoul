# AGENTS.md - Gira Usage Guide for AI Agents

This guide provides comprehensive instructions for AI agents working with Gira, the Git-native project management tool, specifically for the **Consoul** project.

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


## 🚀 Quick Start

### Initial Setup
```bash
# Check if Gira is initialized
ls .gira/

# View project configuration
cat .gira/config.json

# View the board
gira board
```

### Essential Commands
```bash
# View all tickets
gira ticket list

# Check ticket details
gira ticket show TICKET-ID

# Move ticket to in-progress
gira ticket move TICKET-ID in_progress --force

# Add progress update
gira comment add TICKET-ID
```

## 📋 Core Workflows

### 1. Starting Work on a Ticket
```bash
# Find available tickets
gira ticket list --status backlog

# Assign ticket to yourself
gira ticket update TICKET-ID --assignee me

# Move to in-progress
gira ticket move TICKET-ID in_progress --force

# Add initial comment
gira comment add TICKET-ID --message "Starting work on this ticket"
```

### 2. During Development
```bash
# Update ticket description with progress
gira ticket update TICKET-ID --description "Implemented X, working on Y"

# If blocked
gira ticket move TICKET-ID blocked
gira comment add TICKET-ID --message "Blocked by: [reason]"

# Check related tickets
gira ticket list --epic EPIC-ID
```

### 3. Completing Work
```bash
# Move to done
gira ticket move TICKET-ID done --force

# Add completion summary
gira comment add TICKET-ID --message "Completed: [summary of changes]"

# After approval, move to done
gira ticket move TICKET-ID done
```

## 🔄 Ticket Lifecycle

### Status Flow
```
todo → in_progress → review → done
```

### Status Descriptions
- **todo**: To Do tickets
- **in_progress**: In Progress tickets (WIP limit: 5)
- **review**: Review tickets (WIP limit: 5)
- **done**: Done tickets


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

### Dependency Management Workflow
```bash
# Create dependent tickets
gira ticket create "Setup database schema" --type task --priority high --status backlog
gira ticket create "Implement user CRUD operations" --type feature --priority medium --status backlog

# Add dependency relationship
gira ticket add-dep SOUL-2 SOUL-1

# Check dependency
gira ticket deps SOUL-2
```

## 📝 Git Integration

### Commit Message Format
```bash
# With Gira ticket
git commit -m "type(TICKET-ID): brief description

- Detailed change 1
- Detailed change 2

Gira: TICKET-ID"

# Without specific ticket
git commit -m "type: brief description

- Detailed changes

Relates-to: general context"
```

### Commit Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `style`: Formatting changes
- `chore`: Maintenance tasks

## 🔍 Finding and Filtering

### Search Tickets
```bash
# By status
gira ticket list --status in_progress

# By priority
gira ticket list --priority high

# By assignee
gira ticket list --assignee me

# Combine filters
gira ticket list --status backlog --priority high --type bug
```

### Code Integration
```bash
# Find tickets that modified files
gira ticket blame src/

# Check specific file
gira ticket blame src/main.py

# Get JSON output
gira ticket blame src/ --json
```

## 📊 Project Organization

### Epics
```bash
# List all epics
gira epic list

# View epic details with tickets
gira epic show EPIC-001

# Create ticket in epic
gira ticket create "New feature" --epic EPIC-001
```

### Sprints
```bash
# View current sprint
gira sprint current

# List all sprints
gira sprint list

# Show sprint details
gira sprint show SPRINT-001
```

## 💡 Best Practices

### 1. Always Update Status
- Move tickets promptly when state changes
- Don't leave tickets in "in progress" indefinitely
- Use "blocked" status with explanation

### 2. Document Everything
- Add comments for significant decisions
- Update ticket descriptions with progress
- Include context in commit messages

### 3. Check Before Acting
```bash
# Always check current state first
gira ticket show TICKET-ID

# Verify no one else is working on it
gira ticket list --status in_progress --assignee all
```

### 4. Link Related Work
- Reference ticket IDs in commits
- Use epics to group related tickets
- Mention related tickets in comments

## 🛠️ Advanced Usage

### Batch Operations
```bash
# Process multiple tickets
for ticket in TICKET-1 TICKET-2 TICKET-3; do
    echo "y" | gira ticket move "$ticket" in_progress
done

# Export for analysis
gira export tickets --format json > tickets.json
```

### Reporting
```bash
# Get project statistics
gira ticket list --format json | jq 'group_by(.status) | map({status: .[0].status, count: length})'

# Check velocity
gira sprint show SPRINT-001 --format json | jq '.completed_points'
```

## 🚨 Common Issues

### Ticket Not Found
```bash
# List all tickets
gira ticket list

# Search by keyword
gira ticket list | grep -i "search term"
```

### Understanding Workflow
```bash
# Check available statuses
gira board

# View workflow config
cat .gira/config.json | jq '.workflow'
```

### Merge Conflicts in .gira/
```bash
# Tickets are stored as separate JSON files
# In case of conflicts, check both versions
git status
git diff .gira/board/

# Usually safe to keep both tickets
git add .gira/
git commit -m "chore: resolve gira merge conflict"
```

## 📚 Quick Reference

### Most Used Commands
```bash
gira board                          # View kanban board
gira ticket list                    # List all tickets
gira ticket show ID                 # Show ticket details
gira ticket move ID STATUS          # Change status
gira ticket update ID --field VALUE # Update ticket
gira comment add ID                 # Add comment
gira epic list                      # List epics
gira sprint current                 # Current sprint
```

### Useful Aliases
```bash
alias gb='gira board'
alias gt='gira ticket'
alias gtl='gira ticket list'
alias gtm='gira ticket move'
alias gts='gira ticket show'
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

---

*This guide helps AI agents work effectively with Gira's Git-native project management system.*
