---
name: meeting-processor
description: Automatically processes and enriches meeting transcripts. Invoked when working with files in _inbox/meetings/ or when discussing meeting notes, transcripts, or knowledge base organization.
---

# Meeting Processor Skill

This skill provides context and rules for processing meeting transcripts and integrating them into the Obsidian knowledge base.

## When to Use This Skill

Activate this skill when:
- User mentions "meeting", "transcript", "process meetings", "inbox"
- Working with files in `_inbox/meetings/` directory
- Asked to organize or categorize meeting notes
- Extracting action items from meeting content

## Core Processing Rules

### Content Preservation
- **Never delete or modify original transcript text**
- Additions go in new sections or metadata only
- Keep speaker attributions intact
- Preserve timestamps if present

### Wiki-Linking Standards
- Use `[[double brackets]]` for all links
- People: `[[people/First Last]]`
- Projects: `[[projects/project-slug/index]]`
- Concepts: `[[concepts/Concept Name]]` (if folder exists)
- Link only first occurrence per document
- Maximum 10-15 links per document

### Tagging Conventions
```yaml
tags:
  - meeting           # Always include
  - [project-slug]    # kebab-case project name
  - [theme-1]         # Primary discussion theme
  - [theme-2]         # Secondary theme (optional)
```

### File Naming
- Format: `YYYY-MM-DD-[descriptive-slug].md`
- Use kebab-case for slug
- Maximum 50 characters for slug portion
- Example: `2026-01-07-quarterly-planning-sync.md`

## Project Matching Algorithm

### Signal Weights
| Signal Type | Weight | Example |
|-------------|--------|---------|
| Explicit project name | 5 | "discussed OpenCivics roadmap" |
| Project alias | 4 | "oc-labs team" |
| Team member name | 3 | "Benjamin mentioned..." |
| Project keyword | 2 | "governance", "attestation" |
| Related concept | 1 | "blockchain", "coordination" |

### Matching Threshold
- **Strong match:** Total weight ≥ 8 → Assign with confidence
- **Moderate match:** Weight 4-7 → Assign, note uncertainty
- **Weak match:** Weight < 4 → Route to general meetings/

### Conflict Resolution
If multiple projects match with similar weights:
1. Check for explicit project mention in meeting title
2. Favor project with more team member matches
3. If still tied, assign to first matched and add `also_related` field

## Metadata Extraction

### Participants
Extract names from:
- Speaker labels in transcript (e.g., "[Benjamin]:", "Benjamin said")
- Mentioned attendees in summary
- @-mentions or references

### Themes
Identify 2-4 primary themes from:
- Section headers in summary
- Most frequent topic clusters
- Explicitly stated agenda items

### Duration
Parse from:
- Frontmatter if present
- Timestamp difference (first to last)
- Explicit mention in content

## People Note Template

When creating new person stubs in `people/`:

```markdown
---
name: "[Full Name]"
first_seen: [meeting date]
email: 
organization: 
role: 
---

# [Full Name]

## Context
First encountered in: [[path/to/meeting-note]]

## Notes
<!-- TODO: Add details about this person -->
```

## Error Handling

### Malformed Files
- Missing frontmatter: Add minimal required fields
- Corrupted content: Log error, skip processing, preserve original

### Unknown Formats
- Non-markdown files: Ignore, report in summary
- Unexpected frontmatter fields: Preserve, don't remove

### Permission Issues
- Read failures: Report and continue
- Write failures: Keep original in inbox, report error

## Integration Points

### With /ingest-meetings command
This skill provides the processing logic; the command handles file discovery and orchestration.

### With /extract-actions command
After processing, action items should be in a consistent format for extraction.

### With Notion MCP
Project matching determines which Notion workspace receives action items.

## Quality Checks

Before finalizing a processed file:
- [ ] Frontmatter is valid YAML
- [ ] All links use proper syntax
- [ ] At least one tag applied
- [ ] Status updated to `processed`
- [ ] Original content preserved
- [ ] File moved to correct location
