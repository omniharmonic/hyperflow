---
description: Send follow-up emails with task reminders to meeting participants using Gmail MCP
allowed-tools: Read, Write, Glob, Grep, mcp__gmail__send-email, mcp__gmail__create-draft, mcp__gmail__list-drafts
argument-hint: [path/to/meeting.md]
---

# Send Follow-up Emails

Generate and send follow-up emails to meeting participants with their assigned action items.

## Prerequisites

- Gmail MCP server must be configured in Claude Code
- Meeting file must have `participants` in frontmatter
- Person files should have email addresses

---

## Workflow

### Step 1: Read Meeting File

Read the specified meeting file and extract:
- Meeting title
- Meeting date
- Summary
- Action items (with assignees)
- Participants
- Key decisions

### Step 2: Get Participant Emails

For each participant in the meeting:
1. Read their person file (`people/{Name}.md`)
2. Extract email address from frontmatter
3. Collect their assigned action items

### Step 3: Generate Personalized Emails

For each participant with action items, generate a personalized email:

**Email Template:**
```
Subject: Follow-up: {Meeting Title} - Action Items

Hi {First Name},

Thanks for joining the {Meeting Title} on {Meeting Date}.

Here's a summary of what we discussed and your action items:

## Summary
{2-3 sentence meeting summary}

## Your Action Items
- [ ] {Task 1} - Due: {date}
- [ ] {Task 2} - Due: {date}

## Key Decisions
- {Decision 1}
- {Decision 2}

## Full Meeting Notes
{Link to Obsidian note or summary}

Let me know if you have any questions!

Best,
{Sender name}
```

### Step 4: Review Before Sending

Show the user a preview of each email:

```
📧 Email Preview (1 of 3)

To: patricia@opencivics.co
Subject: Follow-up: Open Civics Launch Strategy - Action Items

Hi Patricia,

Thanks for joining the Open Civics Launch Strategy meeting on January 8, 2026.

Your Action Items:
- [ ] Complete the membership onboarding page - Due: Tuesday

[Full email preview...]

Options:
- [S]end now
- [D]raft (save to Gmail drafts)
- [E]dit subject/body
- [N]ext (skip this email)
- [A]bort all

Choice:
```

### Step 5: Send or Draft

Based on user choice:

**Send immediately:**
```
mcp__gmail__send-email
- to: {recipient email}
- subject: {subject}
- body: {email body}
```

**Save as draft:**
```
mcp__gmail__create-draft
- to: {recipient email}
- subject: {subject}
- body: {email body}
```

### Step 6: Update Meeting File

After sending, add to meeting frontmatter:
```yaml
followups_sent:
  - email: patricia@opencivics.co
    sent_at: 2026-01-08T10:30:00
    status: sent
  - email: spencer@opencivics.co
    sent_at: 2026-01-08T10:30:00
    status: draft
```

---

## Email Types

### 1. Action Item Reminder (Default)
Personalized email with just that person's action items.

### 2. Full Summary (`--summary`)
Same email to all participants with full meeting summary and all action items.

### 3. Due Date Reminder (`--reminder`)
For tasks approaching their due date:
```
Subject: Reminder: Task due {tomorrow/today}

Hi {Name},

Just a friendly reminder that this task is due {when}:

- {Task description}

From meeting: {Meeting Title} ({Date})

Let me know if you need any help!
```

---

## Example Session

```
User: /send-followups projects/opencivics/meetings/2026-01-08_launch-strategy-website-updates.md

Claude: 📧 Preparing follow-up emails for "Open Civics Launch Strategy"

Found 1 participant with action items:
- Patricia Parkinson (patricia@opencivics.co): 1 task

Generating email for Patricia...

📧 Email Preview:

To: patricia@opencivics.co
Subject: Follow-up: Open Civics Launch Strategy - Action Items

Hi Patricia,

Thanks for joining the Open Civics Launch Strategy meeting on January 8th.

## Your Action Items
- [ ] Complete the membership onboarding page - Due: Tuesday

## Summary
The meeting focused on launch preparation and website updates needed for the 
OpenCivics launch. The main focus was on the membership onboarding page.

Let me know if you have any questions!

---

[S]end / [D]raft / [E]dit / [N]ext / [A]bort?

User: d

Claude: ✅ Draft saved to Gmail

Summary:
- 1 email drafted
- 0 emails sent

Drafts can be reviewed in Gmail before sending.
```

---

## Batch Follow-ups

Send follow-ups for multiple meetings:

```
/send-followups --batch --since 2026-01-01
```

This will:
1. Find all meetings since the date without `followups_sent`
2. Generate emails for each
3. Show summary before sending/drafting

---

## Options

| Flag | Description |
|------|-------------|
| `--draft` | Save all as drafts, don't send |
| `--summary` | Send full summary to all participants |
| `--reminder` | Send due date reminders for upcoming tasks |
| `--batch` | Process multiple meetings |
| `--since DATE` | Only meetings after this date |

---

## Finding Missing Emails

If a participant doesn't have an email address:

```
⚠️ Missing email for: Spencer Cavanaugh

Options:
1. Enter email address now (will save to person file)
2. Skip this participant
3. Abort

Choice:
```

If user enters email, update the person file:
```yaml
email: spencer@opencivics.co
```

---

## Troubleshooting

### "Gmail MCP not available"
Ensure the Gmail MCP server is configured in Claude Code settings.

### "Send failed"
- Check Gmail OAuth permissions
- Verify recipient email is valid
- Check for sending limits

### "No action items found"
The meeting may not have action items extracted. Run `/ingest-meetings` first.
