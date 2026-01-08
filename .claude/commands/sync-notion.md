---
description: Sync action items to Notion task databases for configured projects
allowed-tools: Read, Write, Glob, Grep, mcp__notion__search, mcp__notion__get-database, mcp__notion__query-database, mcp__notion__create-page, mcp__notion__update-page
argument-hint: [path/to/meeting.md or --all for batch sync]
---

# Sync Tasks to Notion

Push action items from meetings to Notion task databases for projects with Notion integration configured.

## Prerequisites

- Notion MCP server must be configured in Claude Code
- Project must have `notion_workspace` and `notion_tasks_database` in PROJECT.md
- Meeting must have action items extracted

---

## Project Configuration

Projects that want Notion integration need these fields in `PROJECT.md`:

```yaml
---
name: "OpenCivics"
notion_workspace: "OpenCivics Workspace"
notion_tasks_database: "abc123-def456-..."  # Database ID
notion_page_id: "xyz789-..."                # Optional: parent page
---
```

### Finding Your Notion Database ID

1. Open the Notion database in your browser
2. Copy the URL: `https://notion.so/workspace/abc123def456...`
3. The ID is the long string after the workspace name (remove hyphens or keep them)

---

## Workflow

### Step 1: Read Meeting & Project

1. Read the meeting file to get:
   - Action items (from table or list)
   - Project link
   - Meeting date and title

2. Read the linked project's `PROJECT.md` to get:
   - `notion_tasks_database` ID
   - `notion_workspace` name

### Step 2: Check Notion Configuration

If project doesn't have Notion configured:
```
⚠️ Project "OpenCivics" doesn't have Notion integration configured.

To enable, add to projects/opencivics/PROJECT.md:
  notion_workspace: "Your Workspace Name"
  notion_tasks_database: "your-database-id"

[S]kip / [C]onfigure now / [A]bort:
```

### Step 3: Connect to Notion Database

Use MCP to verify database access:

```
mcp__notion__get-database
- database_id: {notion_tasks_database}
```

Verify the database has required properties:
- `Name` or `Title` (title property)
- `Status` (select: To Do, In Progress, Done)
- `Due Date` (date)
- `Assignee` (person or text)
- `Source` (URL or text - for meeting link)

### Step 4: Check for Duplicates

Query existing tasks to avoid duplicates:

```
mcp__notion__query-database
- database_id: {notion_tasks_database}
- filter: {
    "property": "Source",
    "rich_text": {
      "contains": "{meeting filename}"
    }
  }
```

### Step 5: Create Tasks in Notion

For each new action item:

```
mcp__notion__create-page
- parent: { "database_id": "{notion_tasks_database}" }
- properties: {
    "Name": { "title": [{ "text": { "content": "{task description}" }}] },
    "Status": { "select": { "name": "To Do" }},
    "Due Date": { "date": { "start": "{due date}" }},
    "Assignee": { "rich_text": [{ "text": { "content": "{person name}" }}] },
    "Source": { "url": "obsidian://open?vault={vault}&file={meeting path}" },
    "Project": { "select": { "name": "{project name}" }},
    "Created From": { "rich_text": [{ "text": { "content": "Hyperflow" }}] }
  }
```

### Step 6: Update Meeting File

Add Notion sync status to meeting frontmatter:

```yaml
notion_synced:
  database: "abc123-def456"
  tasks_created: 3
  synced_at: 2026-01-08T10:30:00
  task_ids:
    - "notion-page-id-1"
    - "notion-page-id-2"
```

---

## Example Session

```
User: /sync-notion projects/opencivics/meetings/2026-01-08_launch-strategy.md

Claude: 📋 Syncing tasks to Notion

Meeting: "Open Civics Launch Strategy"
Project: OpenCivics
Notion Database: Tasks (abc123...)

Found 2 action items:
1. "Complete the membership onboarding page" - Patricia - Due: Tuesday
2. "Review launch timeline" - Spencer - Due: Friday

Checking for existing tasks in Notion...
✓ No duplicates found

Creating tasks in Notion...
✅ Created: "Complete the membership onboarding page"
   → https://notion.so/abc123...
✅ Created: "Review launch timeline"
   → https://notion.so/def456...

Meeting file updated with notion_synced metadata.

Summary:
  Tasks created: 2
  Database: OpenCivics Tasks
```

---

## Batch Sync

Sync all meetings with action items:

```
/sync-notion --all
```

Or for a specific project:
```
/sync-notion --project opencivics
```

---

## Task Properties Mapping

| Meeting Field | Notion Property | Type |
|---------------|-----------------|------|
| Task description | Name/Title | Title |
| Assignee | Assignee | Person/Text |
| Due date | Due Date | Date |
| Meeting link | Source | URL |
| Project name | Project | Select |
| Status | Status | Select (default: "To Do") |
| Priority | Priority | Select (if available) |

---

## Handling Missing Properties

If the Notion database is missing required properties:

```
⚠️ Notion database missing required properties:
   Missing: "Due Date", "Assignee"

Options:
1. Create properties automatically
2. Map to existing properties
3. Skip these fields
4. Abort

Choice:
```

If user chooses to map:
```
Map "Due Date" to which existing property?
Available: "Deadline", "Target Date", "When"

Enter property name:
```

---

## Two-Way Sync (Future)

For bidirectional sync, the system can:

1. **Notion → Vault**: Pull task status updates back to person files
2. **Mark completed**: When task is done in Notion, update person's "Completed Tasks"

```
/sync-notion --pull
```

---

## Integration with Pipeline

The `/run-pipeline` command includes Notion sync as Stage 3b:

```
Stage 3: Sync Tasks
  ├── 3a: Update person profiles (/sync-tasks)
  └── 3b: Push to Notion (/sync-notion) [if configured]
```

---

## Troubleshooting

### "Notion MCP not available"
Ensure the Notion MCP server is configured in Claude Code settings.

### "Database not found"
- Verify the database ID is correct
- Check that the Notion integration has access to the database
- Ensure the database isn't in a private page

### "Permission denied"
The Notion integration needs:
- Read access to the database
- Write access to create pages
- Access to the workspace

### "Property type mismatch"
The database property types must match:
- Title property for task name
- Date property for due dates
- Select/Multi-select for status

---

## See Also

- `/sync-tasks` - Sync to person profiles (vault-based)
- `/run-pipeline` - Full workflow including Notion
- [Notion API Docs](https://developers.notion.com/)

