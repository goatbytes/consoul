# GEMINI.md - Gira Usage Guide for Gemini

This guide helps Gemini AI agents understand how to use Gira for project management and ticket tracking in the **Consoul** project. Gemini's large context window makes it ideal for analyzing project-wide patterns and managing complex tasks.

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


## 🔍 Leveraging Gemini's Strengths with Gira

### Large-Scale Project Analysis

Gemini's large context window is perfect for analyzing entire project structures and ticket relationships:

#### 1. Project-Wide Ticket Analysis
```bash
# Export all tickets for comprehensive analysis
gira export tickets --format json > all-tickets.json

# View all tickets with their relationships
gira ticket list --format json | jq '.'

# Analyze ticket patterns and dependencies
gira epic list --show-progress
```

#### 2. Batch Ticket Operations
```bash
# Process multiple tickets based on criteria
gira ticket list --status backlog --priority high --format json | \
  jq -r '.[].id' | while read -r ticket; do
    gira ticket show "$ticket"
  done

# Find related tickets across epics
for epic in $(gira epic list --format json | jq -r '.[].id'); do
    echo "Epic: $epic"
    gira epic show "$epic"
done
```

#### 3. Comprehensive Progress Analysis
```bash
# Generate project statistics
gira ticket list --format json | \
  jq '[.[] | select(.status == "done")] | length' # Count completed tickets

# Analyze velocity across sprints
gira sprint list --format json | \
  jq '.[] | {name: .name, completed: .completed_points}'
```

## 🤖 Agent-Friendly Commands for Gemini

### Non-Interactive Operations
```bash
# Skip confirmations with --force flag
gira ticket move TICKET-ID in_progress --force
gira ticket move TICKET-ID done --force

# Use echo for confirmation prompts
echo "y" | gira ticket move TICKET-ID in_progress

# Batch operations with JSON processing
gira ticket list --status backlog --format json | \
  jq -r '.[].id' | head -5 | \
  while read ticket; do echo "y" | gira ticket move "$ticket" ready; done
```

### Complete Workflow Examples
```bash
# Basic bug fix workflow
gira ticket create "Fix authentication issue" --type bug --priority high --status backlog
gira ticket move SOUL-1 in_progress --force
gira comment add SOUL-1 -c "Investigated root cause"
gira ticket move SOUL-1 done --force

# Epic creation and management
gira epic create "User Management" --description "Complete user system"
gira ticket create "User registration" --type feature --epic EPIC-001 --status backlog
gira ticket create "Password reset" --type feature --epic EPIC-001 --status backlog
gira epic show EPIC-001
```

## 📋 Essential Gira Commands for Gemini

### Viewing Project Information
```bash
# View the kanban board with all tickets
gira board

# List all tickets with detailed information
gira ticket list

# View epics and their progress
gira epic list --show-progress

# Check sprint status and velocity
gira sprint list
```

### Managing Complex Tasks
```bash
# View all tickets in an epic
gira epic show EPIC-001

# Create subtasks for large features
gira ticket create "Implement component A" --type task --epic EPIC-001
gira ticket create "Implement component B" --type task --epic EPIC-001

# Batch update tickets
for ticket in $(gira ticket list --status backlog --assignee me --format json | jq -r '.[].id'); do
    echo "y" | gira ticket move "$ticket" in_progress
done
```

## 🚀 Gemini-Specific Workflows

### 1. Multi-Ticket Analysis Workflow
```bash
# Export tickets for analysis
gira export tickets --format json > tickets.json

# Analyze patterns in ticket data
gira ticket list --format json | \
  jq 'group_by(.type) | map({type: .[0].type, count: length})'

# Find tickets without epics
gira ticket list --format json | \
  jq '.[] | select(.epic == null) | .id'
```

### 2. Progress Tracking Across Epics
```bash
# Generate epic progress report
for epic in $(gira epic list --format json | jq -r '.[].id'); do
    echo "Epic: $epic"
    gira epic show "$epic" | grep -E "(Progress|Status)"
done

# Track sprint velocity
gira sprint list --format json | \
  jq 'map({sprint: .name, velocity: .completed_points})'
```

### 3. Dependency Analysis
```bash
# Find blocked tickets
gira ticket list --status blocked

# Analyze ticket relationships
gira ticket list --format json | \
  jq '.[] | select(.blocked_by != null) | {id: .id, blocked_by: .blocked_by}'

# Create dependency report
gira comment add TICKET-ID << EOF
Dependency Analysis:
- Blocked tickets: [list]
- Critical path items: [list]
- Recommended unblocking order: [list]
EOF
```

## 📊 Using Gira for Project Analytics

### Generate Reports
```bash
# Ticket distribution by status
gira ticket list --format json | \
  jq 'group_by(.status) | map({status: .[0].status, count: length})'

# Priority analysis
gira ticket list --format json | \
  jq 'group_by(.priority) | map({priority: .[0].priority, count: length})'

# Assignee workload
gira ticket list --format json | \
  jq 'group_by(.assignee) | map({assignee: .[0].assignee, tickets: length})'
```

## 🔧 Best Practices for Large-Scale Gira Operations

### 1. Batch Processing
```bash
# Process tickets in batches
gira ticket list --status todo --format json | \
  jq -r '.[].id' | \
  xargs -I {} gira ticket update {} --label "needs-review"
```

### 2. Progress Documentation
```bash
# Add comprehensive progress update
gira comment add TICKET-ID << EOF
Progress Update:
- Analyzed X tickets
- Identified Y patterns
- Created Z new subtasks
- Next steps: [list actions]
EOF
```

### 3. Automated Ticket Creation
```bash
# Create multiple related tickets
for component in "auth" "api" "database" "frontend"; do
    gira ticket create "Refactor $component module" \
      --type task \
      --epic EPIC-001 \
      --priority medium
done
```

## 🎯 Task Types Well-Suited for Gemini

With its large context window, Gemini excels at:

1. **Project-Wide Analysis**: Understanding relationships across all tickets and epics
2. **Batch Operations**: Processing multiple tickets simultaneously
3. **Pattern Recognition**: Identifying trends in ticket data
4. **Comprehensive Reporting**: Generating detailed project analytics
5. **Migration Planning**: Analyzing large sets of tickets for reorganization
6. **Workflow Optimization**: Suggesting improvements based on historical data

## 📈 Working with Gira Data

### Export and Analysis
```bash
# Export all project data
gira export all --output project-backup/

# Export specific data types
gira export tickets --format json > tickets.json
gira export epics --format json > epics.json
gira export sprints --format json > sprints.json

# Analyze exported data
cat tickets.json | jq 'length' # Total ticket count
cat epics.json | jq '.[] | {id: .id, progress: .progress}'
```

### Import Operations
```bash
# Import tickets from JSON
gira import tickets tickets.json

# Import from CSV
gira import tickets tickets.csv --format csv
```

## 💡 Gemini-Specific Tips

### Using JSON Output
Gemini works well with structured data:
```bash
# Get all ticket data in JSON
gira ticket list --format json > all-tickets.json

# Get specific fields
gira ticket list --format json | \
  jq '.[] | {id: .id, title: .title, status: .status, assignee: .assignee}'
```

### Parallel Processing
```bash
# Process multiple tickets in parallel
gira ticket list --status "in progress" --format json | \
  jq -r '.[].id' | \
  parallel -j 4 'gira ticket show {}'
```

### Historical Analysis
```bash
# Analyze ticket completion patterns
gira ticket list --status done --format json | \
  jq '.[] | select(.completed_at != null) | .completed_at' | \
  sort | uniq -c
```

## 🔍 Git Integration with Gira

### Finding Related Code Changes
```bash
# Find commits related to tickets
git log --grep="Gira:" --oneline

# Find tickets that modified specific files
gira ticket blame src/

# Get detailed blame information
gira ticket blame src/ --json > blame-report.json
```

### Commit Message Integration
```bash
# Proper format with Gira ticket
git commit -m "feat(TICKET-123): add bulk processing feature

- Implement batch ticket updates
- Add progress tracking
- Include error handling

Gira: TICKET-123"
```

## 🚨 Common Scenarios for Gemini

### Large Epic Management
```bash
# Analyze epic with many tickets
gira epic show EPIC-001 > epic-details.txt

# Find incomplete tickets in epic
gira ticket list --epic EPIC-001 --format json | \
  jq '.[] | select(.status != "done") | {id: .id, title: .title}'
```

### Sprint Planning
```bash
# Analyze unassigned high-priority tickets
gira ticket list --status backlog --priority high --assignee none

# Calculate sprint capacity
gira ticket list --sprint SPRINT-001 --format json | \
  jq '[.[] | .story_points // 0] | add'
```

## 🔧 Common Issues & Solutions

| Error | Solution |
|-------|----------|
| "Invalid status 'todo'" | Use `backlog` instead |
| "Invalid status 'review'" | Use `done` instead |
| Command hangs on confirmation | Add `--force` flag or use `echo "y" \|` |
| "No such ticket" | Check ticket ID format (SOUL-123) |
| Interactive command issues | Use `--force` flags for automation |
| JSON parsing errors | Ensure `--format json` is used |

## ✅ Command Verification

After batch operations, verify success:

```bash
# After batch ticket moves
gira board

# After creating multiple tickets
gira ticket list --format json | jq 'length'

# After epic operations
gira epic show EPIC-ID

# Check overall project health
gira ticket list --status in_progress --format json | jq 'length'
```

---

*This guide helps Gemini work effectively with Gira's Git-native project management system, leveraging its large context window for comprehensive project analysis.*