---
description: Generate personalized follow-up emails for meeting participants with their action items
allowed-tools: Read, Write, Grep, Glob
argument-hint: [path to meeting note or 'recent' for latest]
---

# Follow-up Email Generation Workflow

Generate personalized follow-up emails for each meeting participant, summarizing the discussion and highlighting their specific action items.

## Invocation

```
/send-followups recent
/send-followups projects/opencivics/meetings/2026-01-07-sync.md
```

## Step 1: Load Meeting Content

- Read the specified meeting note
- Extract: title, date, summary, action items, participants
- Load PROJECT.md for team contact information

## Step 2: Identify Recipients

From meeting participants list:
1. Look up each person in `people/[name].md` for email
2. Check PROJECT.md team section for email
3. If email not found, note for user to fill in

Create recipient list:
```yaml
recipients:
  - name: Benjamin
    email: benjamin@example.org
    actions: [list of their action items]
  - name: Sarah
    email: sarah@example.org  
    actions: [list of their action items]
```

## Step 3: Generate Email Drafts

For each recipient, generate personalized email:

### Email Template

**Subject:** Follow-up: [Meeting Title] - [Date]

```markdown
Hi [First Name],

Thanks for joining today's [meeting type] on [topic]. Here's a quick summary and your action items.

## Meeting Summary

[2-3 sentence summary of key discussion points and decisions]

## Your Action Items

[If they have action items:]
Based on our discussion, here's what you committed to:

- [ ] [Action item 1] [by deadline if specified]
- [ ] [Action item 2]

[If no action items:]
No specific action items were assigned to you in this meeting.

## Team Action Items

For visibility, here's what others are working on:

- **[Other Person]**: [Their action item summary]

## Next Steps

[Any scheduled follow-ups, next meeting, or general next steps]

---

Let me know if I missed anything or if you have questions!

[Sender signature block]
```

### Personalization Rules

- Use first name in greeting
- Only include their action items prominently
- Summarize (don't list all) others' items
- Match tone to relationship (formal for external, casual for team)

## Step 4: Save Drafts

Create draft files in a staging location:

```
_drafts/followups/[meeting-date]/
├── email-benjamin.md
├── email-sarah.md
└── summary.md  # Overview of all drafts
```

Each email file format:
```markdown
---
to: email@example.org
subject: Follow-up: [Meeting Title] - [Date]
status: draft
meeting: "[[path/to/meeting-note]]"
---

[Email body]
```

## Step 5: Summary Output

Present summary to user:

```markdown
## Follow-up Emails Generated

Meeting: [Title] on [Date]

### Ready to Send
| Recipient | Email | Action Items |
|-----------|-------|--------------|
| Benjamin | benjamin@example.org | 2 items |
| Sarah | sarah@example.org | 1 item |

### Missing Contact Info
- [Name] - email not found (check people/ or PROJECT.md)

### Draft Location
Files saved to: `_drafts/followups/2026-01-07/`

### Next Steps
1. Review drafts in the folder above
2. Fill in missing emails
3. Copy content to your email client
4. Send!
```

## Step 6: Cleanup Options

After user confirms emails sent:
- Move drafts to `_archive/sent-followups/`
- Update meeting note with "follow-ups sent" status

## Customization

### Tone Settings

In CLAUDE.md or settings, user can specify:
```yaml
email_defaults:
  tone: professional | casual | formal
  signature: |
    Best,
    [Name]
  include_team_items: true | false
```

### Template Override

User can create custom template at:
`_templates/followup-email.md`

## Error Handling

### Missing Emails
- Generate draft without "to:" field
- Flag in summary for user to fill in

### No Action Items
- Still generate thank-you email
- Focus on summary and next steps

### Large Meetings
- If >10 participants, ask user which to include
- Option to generate "all hands" version for large groups

## Notes

- Emails are drafts only - user must send manually
- Consider privacy: don't include sensitive details
- Keep summaries concise - busy people skim
- Action items should be clear and actionable
