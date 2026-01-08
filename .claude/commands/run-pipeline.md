---
description: Run the complete Hyperflow pipeline - sync, ingest, tasks, calendar, and followups
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, mcp__google-calendar__list-calendars, mcp__google-calendar__list-events, mcp__google-calendar__update-event, mcp__google-calendar__create-event, mcp__gmail__send-email, mcp__gmail__create-draft, mcp__notion__query-database, mcp__notion__create-page
argument-hint: [--all | --since DATE | --skip-calendar | --skip-email | --draft-only]
---

# Hyperflow Pipeline

**The Master Orchestrator** - Runs the complete meeting-to-knowledge workflow from start to finish.

## Overview

This command coordinates all Hyperflow stages in sequence:

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYPERFLOW PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │ 1. SYNC      │ ──► │ 2. INGEST    │ ──► │ 3a. TASKS    │    │
│  │ /sync-meetily│     │ /ingest-     │     │ /sync-tasks  │    │
│  │              │     │  meetings    │     │ (profiles)   │    │
│  └──────────────┘     └──────────────┘     └──────┬───────┘    │
│         │                    │                    │             │
│         ▼                    ▼                    ▼             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │ Pull from    │     │ Extract      │     │ 3b. NOTION   │    │
│  │ Meetily DB   │     │ entities,    │     │ /sync-notion │    │
│  │              │     │ wiki-links   │     │ (if config'd)│    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐                         │
│  │ 4. CALENDAR  │ ──► │ 5. FOLLOWUPS │                         │
│  │ /link-       │     │ /send-       │                         │
│  │  calendar    │     │  followups   │                         │
│  └──────────────┘     └──────────────┘                         │
│         │                    │                                  │
│         ▼                    ▼                                  │
│  ┌──────────────┐     ┌──────────────┐                         │
│  │ Attach to    │     │ Email task   │                         │
│  │ Google Cal   │     │ reminders    │                         │
│  └──────────────┘     └──────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

```
/run-pipeline
```

This runs all stages with sensible defaults.

---

## Workflow Stages

### Stage 1: Sync Meetily Database

**Goal:** Pull new meetings from Meetily's SQLite database.

```bash
python3 scripts/sync_meetily.py
```

**Output:**
- New meeting files in `_inbox/meetings/`
- Count of meetings synced

**Continue if:** At least 1 new meeting, OR existing pending meetings in inbox.

**Skip if:** No new meetings AND no pending files.

---

### Stage 2: Ingest Meetings

**Goal:** Process raw meetings - extract entities, add wiki-links, route to projects.

For each file in `_inbox/meetings/` with `status: pending_enrichment`:

1. **Analyze content** - Extract people, concepts, organizations
2. **Match to project** - Score against `PROJECT.md` files
3. **Create entity files** - Stub files for new people/concepts
4. **Enrich meeting** - Add summary, key insights, action items
5. **Move file** - Route to project folder or general meetings

**Output:**
- Processed meeting files in destination folders
- New entity files in `people/`, `concepts/`, `organizations/`
- List of action items found

**Track:**
- `meetings_processed`: count
- `entities_created`: {people: N, concepts: N, orgs: N}
- `action_items_found`: [{person, task, due}]

---

### Stage 3a: Sync Tasks to People

**Goal:** Push action items to person profiles in the vault.

For each action item found in Stage 2:

1. **Find assignee** - Parse wiki-link to person
2. **Read person file** - Check existing tasks
3. **Add new tasks** - Append to "Open Tasks" section
4. **Avoid duplicates** - Skip if already present

**Output:**
- Updated person files with tasks
- Count of tasks synced

---

### Stage 3b: Sync Tasks to Notion (Optional)

**Requires:** Notion MCP + Project configured with `notion_tasks_database`

**Goal:** Push action items to Notion task databases for integrated projects.

For each project with Notion configured:

1. **Check configuration** - Read `notion_tasks_database` from PROJECT.md
2. **Connect to Notion** - Verify database access via MCP
3. **Check duplicates** - Query existing tasks with same source
4. **Create tasks** - Add new tasks with assignee, due date, source link

**Output:**
- Tasks created in Notion databases
- Meeting files updated with `notion_synced` metadata

**Skip if:** `--skip-notion` flag OR project has no Notion config OR Notion MCP not available.

**Project Configuration Required:**
```yaml
# In PROJECT.md frontmatter
notion_workspace: "Workspace Name"
notion_tasks_database: "database-id-here"
```

---

### Stage 4: Link to Calendar (Optional)

**Requires:** Google Calendar MCP

**Goal:** Attach meeting notes to Google Calendar events.

For each processed meeting:

1. **Search calendar** - Find events around meeting time
2. **Match event** - Score by time, title, attendees
3. **Confirm match** - Ask user if confidence < 80%
4. **Update event** - Add summary to event description

**Output:**
- Calendar events updated with meeting links
- Meeting files updated with `calendar_event` ID

**Skip if:** `--skip-calendar` flag OR Calendar MCP not available.

---

### Stage 5: Send Follow-ups (Optional)

**Requires:** Gmail MCP

**Goal:** Email participants with their action items.

For each meeting with action items:

1. **Get participants** - Read from meeting frontmatter
2. **Get emails** - Look up in person files
3. **Generate emails** - Personalized with their tasks
4. **Review & send** - Show preview, confirm before sending

**Output:**
- Emails sent or drafted
- Meeting files updated with `followups_sent`

**Skip if:** `--skip-email` flag OR Gmail MCP not available.

---

## Command Options

| Flag | Description |
|------|-------------|
| `--all` | Re-process all meetings (not just new) |
| `--since DATE` | Only process meetings after this date |
| `--skip-notion` | Skip Notion task sync |
| `--skip-calendar` | Skip the calendar linking stage |
| `--skip-email` | Skip the follow-up email stage |
| `--draft-only` | Save emails as drafts, don't send |
| `--dry-run` | Preview what would happen, don't make changes |
| `--verbose` | Show detailed progress for each step |

---

## Interactive Mode

The pipeline will pause for user input at key decision points:

### Project Matching (Low Confidence)
```
⚠️ Uncertain project match for "Q1 Planning Meeting"

Best matches:
1. OpenCivics (score: 4)
2. Localism Fund (score: 3)
3. [No project - use general meetings/]

Select project (1/2/3) or [s]kip:
```

### Calendar Matching
```
📅 Found 2 potential calendar matches:

1. "Weekly Sync" (06:00-07:00) - 85% match
2. "Morning Standup" (09:00-09:15) - 20% match

Select event (1/2) or [s]kip:
```

### Email Confirmation
```
📧 Ready to send 3 follow-up emails:

1. patricia@opencivics.co - 2 action items
2. spencer@opencivics.co - 1 action item
3. marcus@example.com - 1 action item

[S]end all / [D]raft all / [R]eview each / [A]bort:
```

---

## Pipeline State & Recovery

The pipeline tracks progress in `.hyperflow_state.json`:

```json
{
  "run_id": "2026-01-08T10:30:00",
  "status": "in_progress",
  "current_stage": 3,
  "completed_stages": [1, 2],
  "meetings_synced": ["meeting-123", "meeting-456"],
  "meetings_processed": ["2026-01-08_theory-of-change.md"],
  "tasks_synced": 5,
  "errors": []
}
```

### Resume After Interruption
```
/run-pipeline --resume
```

Continues from the last successful stage.

### Retry Failed Stage
```
/run-pipeline --retry-stage 3
```

---

## Example Full Run

```
User: /run-pipeline

Claude: 🚀 HYPERFLOW PIPELINE
═══════════════════════════════════════════════════

📋 Stage 1/5: Sync Meetily Database
────────────────────────────────────
Running: python3 scripts/sync_meetily.py
📂 Database: ~/Library/Application Support/com.meetily.ai/meeting_minutes.sqlite
📁 Export to: _inbox/meetings/

✅ Synced 2 new meetings:
   • 2026-01-08T10-15_team-standup.md
   • 2026-01-08T14-30_client-call.md

═══════════════════════════════════════════════════

📋 Stage 2/5: Ingest Meetings
────────────────────────────────────
Processing 2 meetings...

📄 team-standup.md
   ├─ Project: OpenCivics (score: 8, high confidence)
   ├─ Entities: 2 people, 1 concept
   ├─ Action items: 3
   └─ ✅ Moved to: projects/opencivics/meetings/

📄 client-call.md
   ├─ Project: Localism Fund (score: 6, medium confidence)
   ├─ Entities: 1 person (new), 2 concepts
   ├─ Action items: 2
   └─ ✅ Moved to: projects/localism-fund/meetings/

Created:
   • people/Jane Client.md (new)
   • concepts/Impact Metrics.md (new)

═══════════════════════════════════════════════════

📋 Stage 3a/6: Sync Tasks to Profiles
────────────────────────────────────
Found 5 action items assigned to 3 people.

✅ Updated:
   • people/Patricia Parkinson.md (+2 tasks)
   • people/Spencer Cavanaugh.md (+1 task)
   • people/Jane Client.md (+2 tasks)

═══════════════════════════════════════════════════

📋 Stage 3b/6: Sync Tasks to Notion
────────────────────────────────────
Checking project Notion configurations...

📊 OpenCivics: Notion configured ✓
   Database: "OpenCivics Tasks"
   Creating 3 tasks...
   ✅ Created: "Complete membership onboarding page"
   ✅ Created: "Review launch timeline"
   ✅ Created: "Update website content"

📊 Localism Fund: No Notion config (skipped)

═══════════════════════════════════════════════════

📋 Stage 4/6: Link to Calendar
────────────────────────────────────
Searching for calendar events...

📅 team-standup.md
   Match: "OpenCivics Daily Sync" (10:00-10:30) - 92% confidence
   ✅ Calendar event updated

📅 client-call.md
   Match: "Localism Fund Check-in" (14:30-15:00) - 88% confidence
   ✅ Calendar event updated

═══════════════════════════════════════════════════

📋 Stage 5/6: Send Follow-ups
────────────────────────────────────
3 participants have action items.

📧 Ready to send:
   1. patricia@opencivics.co - 2 tasks
   2. spencer@opencivics.co - 1 task  
   3. jane@client.com - 2 tasks

[S]end all / [D]raft all / [R]eview each / [A]bort? d

✅ Created 3 email drafts in Gmail

═══════════════════════════════════════════════════

✨ PIPELINE COMPLETE
═══════════════════════════════════════════════════

Summary:
   📥 Meetings synced: 2
   📝 Meetings processed: 2
   👤 People created: 1
   💡 Concepts created: 1
   ✅ Tasks synced to profiles: 5
   📊 Tasks synced to Notion: 3
   📅 Calendar events linked: 2
   📧 Follow-up drafts: 3

Duration: 45 seconds

Next run: /run-pipeline (new meetings only)
Full refresh: /run-pipeline --all
```

---

## Error Handling

### Stage Failure
If a stage fails, the pipeline:
1. Logs the error
2. Asks whether to continue or abort
3. Allows retry of failed stage

```
❌ Stage 2 Error: Failed to process "team-standup.md"
   Error: Could not parse frontmatter

Options:
1. [R]etry this file
2. [S]kip and continue
3. [A]bort pipeline

Choice:
```

### MCP Not Available
```
⚠️ Stage 4 Skipped: Google Calendar MCP not available
   Configure the Calendar MCP to enable this feature.
   
Continuing to Stage 5...
```

### Using Direct API Integration (Alternative to MCP)

If MCP tools are not available, the pipeline can use `scripts/integrations.py` for direct API access:

```bash
# Test integrations
python scripts/integrations.py --test

# Setup Google APIs (Gmail + Calendar)
python scripts/setup_google.py
```

The direct API approach provides:
- Consistent authentication flow
- Better error messages
- Works outside Claude Code
- No MCP configuration needed

---

## Scheduling (Future)

For automated runs, the pipeline can be triggered via:

```bash
# Cron job (run every hour)
0 * * * * cd /path/to/vault && claude-code "/run-pipeline --skip-email"

# Or manual trigger after meetings
/run-pipeline
```

---

## See Also

- `/sync-meetily` - Stage 1 details
- `/ingest-meetings` - Stage 2 details
- `/sync-tasks` - Stage 3 details
- `/link-calendar` - Stage 4 details
- `/send-followups` - Stage 5 details

