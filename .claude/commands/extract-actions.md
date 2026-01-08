---
description: Extract action items from meeting notes and create tasks in Notion
allowed-tools: Read, Write, Grep, Glob, Notion
argument-hint: [path to meeting note or 'recent' for latest]
---

# Action Item Extraction Workflow

Extract commitments, tasks, and action items from meeting transcripts and create corresponding tasks in the appropriate Notion workspace.

## Invocation

```
/extract-actions recent              # Process most recent meeting
/extract-actions projects/opencivics/meetings/2026-01-07-sync.md  # Specific file
```

## Step 1: Identify Target File

If `$ARGUMENTS` is "recent" or empty:
- Find most recently modified `.md` file in `projects/*/meetings/` or `meetings/`
- Confirm with user before proceeding

If path provided:
- Verify file exists
- Read content

## Step 2: Load Project Context

From the meeting note's frontmatter `project` field:
- Extract linked project path
- Read that project's `PROJECT.md`
- Get `notion_workspace` and `notion_tasks_database` IDs

If no project linked:
- Ask user which Notion database to use
- Or skip Notion creation, output to markdown only

## Step 3: Extract Action Items

Scan transcript and summary for action-oriented language:

### Trigger Patterns
- "will [verb]" - commitment
- "[Name] to [verb]" - assignment
- "action item:" - explicit marker
- "TODO:" - explicit marker
- "needs to" - requirement
- "should [verb]" - suggestion/task
- "by [date]" - deadline indicator
- "let's" - commitment (needs context)

### Extraction Format
For each action item, capture:
```yaml
action:
  text: "The actual task description"
  assignee: "Person Name"  # null if unclear
  deadline: "2026-01-15"   # null if not mentioned
  context: "Brief context from meeting"
  confidence: high | medium | low
```

### Confidence Levels
- **High:** Explicit assignment with name, clear action verb
- **Medium:** Implied commitment, general "we will" statements
- **Low:** Suggestions, might-do items

## Step 4: User Confirmation

Present extracted action items in formatted list:

```markdown
## Extracted Action Items from [Meeting Title]

### High Confidence (will create in Notion)
1. **Benjamin** - Set up CI/CD pipeline for TrustGraph
   - Context: Discussed in technical planning section
   - Deadline: January 15, 2026

2. **Sarah** - Review governance proposal draft
   - Context: Final review before submission
   - Deadline: EOW

### Medium Confidence (confirm before creating)
3. **Team** - Schedule follow-up on funding strategy
   - Context: Mentioned briefly at end

### Low Confidence (skipped unless you confirm)
4. Consider adding metrics dashboard
   - No assignee identified
```

Ask: "Create the high-confidence items in Notion? (y/n/edit)"

## Step 5: Create Notion Tasks

For confirmed items, use Notion MCP to create tasks:

```json
{
  "parent": { "database_id": "[from PROJECT.md]" },
  "properties": {
    "Name": { "title": [{ "text": { "content": "[task text]" }}] },
    "Assignee": { "people": [{ "name": "[assignee]" }] },
    "Due Date": { "date": { "start": "[deadline]" } },
    "Source": { "rich_text": [{ "text": { "content": "Meeting: [meeting title]" }}] },
    "Status": { "select": { "name": "Not Started" } }
  }
}
```

## Step 6: Update Meeting Note

Add section to meeting note documenting extracted actions:

```markdown
## Action Items

Created in Notion on [date]:
- [ ] **Benjamin** - Set up CI/CD pipeline (#notion-task-id)
- [ ] **Sarah** - Review governance proposal draft

Not created:
- Consider adding metrics dashboard (no assignee)
```

## Step 7: Summary Output

Report results:
- Number of action items found
- Number created in Notion
- Number skipped
- Link to Notion database view

## Error Handling

### No Notion Access
- Output action items as markdown checklist in meeting note
- Suggest enabling Notion MCP

### No Project Context
- Use default/personal Notion database if configured
- Or output markdown only

### API Failures
- Log error
- Output items to markdown as fallback
- Suggest retry

## Notes

- Only high-confidence items are auto-created
- Medium/low require explicit confirmation
- All extractions are logged in the meeting note
- Duplicate detection: check if similar task exists before creating
