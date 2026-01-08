---
description: Extract action items from meetings and add them to person profiles
allowed-tools: Read, Write, Edit, Glob, Grep
argument-hint: [optional: specific meeting file or person file]
---

# Sync Tasks to Person Profiles

Extract action items from processed meetings and add them to the relevant person's profile.

## Overview

This command scans meetings for action items and:
1. Identifies the assignee for each task
2. Adds the task to that person's "Open Tasks" section
3. Links back to the source meeting
4. Avoids duplicates

---

## Workflow

### Step 1: Find Meetings with Action Items

Scan for meetings with action items:
- Look in `projects/*/meetings/*.md`
- Look in `meetings/**/*.md`
- Check for `## Action Items` section or action item tables

### Step 2: Parse Action Items

For each meeting, extract action items in these formats:

**Table format:**
```markdown
| Owner | Task | Due |
|---|---|---|
| [[people/Name]] | Task description | Due date |
```

**List format:**
```markdown
## Action Items
- [ ] Task description - @[[people/Name]] (due: date)
- [ ] Another task - @[[people/Name]]
```

**Extract:**
- Assignee (person name/link)
- Task description
- Due date (if present)
- Source meeting path
- Meeting date

### Step 3: For Each Person with Tasks

Read the person's profile file and check the "Open Tasks" section.

**If task already exists** (same description from same meeting): Skip it

**If task is new:** Add to "Open Tasks" section:

```markdown
## Open Tasks

- [ ] Complete the membership onboarding page ([[projects/opencivics/meetings/2026-01-08_launch-strategy|Source]]) - Due: Tuesday
```

### Step 4: Update Person File

Write the updated content back to the person file.

**Task format in person file:**
```markdown
- [ ] {Task description} ([[{meeting path}|{meeting date or title}]]) - Due: {date}
```

Or without due date:
```markdown
- [ ] {Task description} ([[{meeting path}|{meeting date}]])
```

---

## Task Lifecycle

### Adding Tasks
- Run `/sync-tasks` after `/ingest-meetings`
- Or run `/sync-tasks path/to/meeting.md` for a specific meeting

### Completing Tasks
User manually:
1. Change `- [ ]` to `- [x]` in the person file
2. Optionally move to "Completed Tasks" section

### Archiving Tasks
Periodically, move completed tasks:
```markdown
## Completed Tasks

- [x] Old task ([[meeting]]) - Completed: 2026-01-10
```

---

## Example

**Input meeting** (`projects/opencivics/meetings/2026-01-08_launch.md`):
```markdown
## Action Items

| Owner | Task | Due |
|---|---|---|
| [[people/Patricia Parkinson|Patricia]] | Complete onboarding page | Tuesday |
| [[people/Spencer Cavanaugh|Spencer]] | Review content | Wednesday |
```

**After running `/sync-tasks`:**

`people/Patricia Parkinson.md`:
```markdown
## Open Tasks

- [ ] Complete onboarding page ([[projects/opencivics/meetings/2026-01-08_launch|2026-01-08]]) - Due: Tuesday
```

`people/Spencer Cavanaugh.md`:
```markdown
## Open Tasks

- [ ] Review content ([[projects/opencivics/meetings/2026-01-08_launch|2026-01-08]]) - Due: Wednesday
```

---

## Parsing Patterns

### Table Row Pattern
```
| [[people/Name|Alias]] | Task text | Due date |
```

Extract:
- `Name` from wiki-link
- `Task text` 
- `Due date`

### List Item Pattern
```
- [ ] Task text - @[[people/Name]] (due: date)
- [ ] Task text @[[people/Name]]
- [ ] Task text - [[people/Name]] - Due: date
```

### Inline Assignment Pattern
```
[[people/Name]] will {task}
[[people/Name]] should {task}
[[people/Name]] needs to {task}
@[[people/Name]]: {task}
```

---

## Output Report

After syncing, report:
```
✅ Task Sync Complete

Meetings scanned: 5
Tasks found: 8
Tasks added: 6
Tasks skipped (duplicates): 2

Updates:
  📝 people/Patricia Parkinson.md (+2 tasks)
  📝 people/Spencer Cavanaugh.md (+1 task)
  📝 people/Marcus Johnson.md (+3 tasks)

Run `/sync-tasks` again after processing new meetings.
```

---

## Integration with Ingest

After running `/ingest-meetings`, suggest:
```
→ Meetings processed. Run /sync-tasks to update person task lists.
```

Or integrate directly by adding to the end of `/ingest-meetings`:
```
## Step 9: Sync Tasks (Optional)

If action items were extracted, offer to sync tasks to person profiles:
> Found 3 action items assigned to 2 people. Sync to their profiles? (y/n)
```

