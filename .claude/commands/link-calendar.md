---
description: Link meeting notes to Google Calendar events using the Calendar MCP
allowed-tools: Read, Write, Glob, mcp__google-calendar__list-calendars, mcp__google-calendar__list-events, mcp__google-calendar__get-event, mcp__google-calendar__update-event, mcp__google-calendar__create-event
argument-hint: [path/to/meeting.md or leave empty to process recent meetings]
---

# Link Meeting to Google Calendar

Find the corresponding Google Calendar event for a meeting and attach the notes.

## Prerequisites

- Google Calendar MCP server must be configured in Claude Code
- Meeting file must have a `date` field in frontmatter

---

## Workflow

### Step 1: Read Meeting File

If `$ARGUMENTS` provided, use that file. Otherwise, find recently processed meetings:
```bash
ls -t projects/*/meetings/*.md meetings/**/*.md | head -5
```

For each meeting file, extract:
- `date` from frontmatter (ISO timestamp)
- `title` from frontmatter or H1 heading
- `participants` from frontmatter
- Meeting duration (if available)
- Key topics/themes from content

### Step 2: Search Calendar Events

Use the Google Calendar MCP to find matching events:

1. **List calendars** to find the primary calendar:
   ```
   mcp__google-calendar__list-calendars
   ```

2. **List events** around the meeting time:
   ```
   mcp__google-calendar__list-events
   - calendarId: "primary" (or selected calendar)
   - timeMin: {meeting date - 1 hour}
   - timeMax: {meeting date + 2 hours}
   ```

### Step 3: Match Event to Meeting

Score potential matches based on:

| Signal | Weight |
|--------|--------|
| Time overlap (within 30 min) | +5 |
| Title similarity | +4 |
| Attendee name match | +3 |
| Duration match | +2 |
| Description keyword match | +1 |

**Matching logic:**
- If score ≥ 8: Strong match, proceed
- If score 5-7: Ask user to confirm
- If score < 5: List top candidates, ask user to select

### Step 4: Confirm Match

Show the user:
```
📅 Found potential calendar match:

Meeting: "Open Civics Theory of Change Meeting"
Date: 2026-01-08 06:15

Calendar Event: "OpenCivics Weekly Sync"  
Time: 2026-01-08 06:00 - 07:00
Attendees: benjamin@opencivics.co, patricia@opencivics.co

Link this meeting to this event? (y/n)
```

### Step 5: Update Calendar Event

Use MCP to update the event description:

```
mcp__google-calendar__update-event
- calendarId: "primary"
- eventId: {matched event ID}
- description: {existing description + meeting notes link/summary}
```

**Add to event description:**
```
---
📝 Meeting Notes: {vault path or link}

Summary: {2-3 sentence summary}

Action Items:
- {action item 1}
- {action item 2}

Full notes: {obsidian://link or file path}
---
```

### Step 6: Update Meeting File

Add calendar link to meeting frontmatter:
```yaml
calendar_event: "{event ID}"
calendar_link: "{Google Calendar event URL}"
```

---

## Example Session

```
User: /link-calendar projects/opencivics/meetings/2026-01-08_theory-of-change.md

Claude: 📅 Searching calendar for events on 2026-01-08 around 06:15...

Found 2 potential matches:

1. "OpenCivics Theory of Change" (06:00-07:00) - Score: 12 ✓
2. "Morning Standup" (09:00-09:15) - Score: 2

Best match: "OpenCivics Theory of Change"
Link meeting notes to this event? (y/n)

User: y

Claude: ✅ Calendar event updated!
- Added meeting summary to event description
- Added action items
- Linked to notes file

Meeting file updated with calendar_event ID.
```

---

## Batch Processing

To link multiple meetings at once:
```
/link-calendar --batch
```

This will:
1. Find all meetings without `calendar_event` in frontmatter
2. Search for matches for each
3. Show summary of proposed links
4. Ask for confirmation before updating

---

## No Match Found

If no calendar event is found:

```
⚠️ No matching calendar event found for:
"Open Civics Theory of Change Meeting" (2026-01-08 06:15)

Options:
1. Create a new calendar event with these details
2. Manually specify an event ID
3. Skip this meeting

Choice (1/2/3):
```

If user chooses 1, create event:
```
mcp__google-calendar__create-event
- calendarId: "primary"
- summary: {meeting title}
- start: {meeting date}
- end: {meeting date + 1 hour}
- description: {meeting summary}
```

---

## Troubleshooting

### "Calendar MCP not available"
Ensure the Google Calendar MCP server is configured in Claude Code settings.

### "No calendars found"
Check that the MCP has proper OAuth permissions for Google Calendar.

### "Event not found"
The meeting may have occurred outside the search window. Try:
- Expanding the time range
- Searching by event title directly

