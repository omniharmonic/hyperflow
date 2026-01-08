# Meeting Processor Skill

Auto-invoked context when working with meeting files or the `_inbox/meetings/` directory.

---

## Core Principles

1. **Preserve original content** - Never delete transcript text
2. **Enrich, don't replace** - Add structure and links around content
3. **Create connections** - Every entity should be linkable
4. **Generate missing summaries** - If Meetily didn't provide one, create it

---

## Content Preservation Rules

- **Never delete original transcript text**
- Additions go in new sections or frontmatter only
- Preserve speaker attributions exactly
- Keep timestamps intact
- Move transcript to end of document after enrichment

---

## Entity Extraction Guide

### People Detection Patterns

Look for:
- Proper nouns in speech: "Sarah mentioned..."
- Direct address: "Hey Marcus, can you..."
- Attribution: "...according to Benjamin"
- Email mentions: "...email john@example.com"
- Action assignment: "Marcus will handle..."
- Introduction: "I'm Sarah Chen from..."

### Concept Detection Patterns

Look for:
- Technical terms: "pattern language", "theory of change"
- Methodologies: "agile", "design thinking"
- Frameworks: "bioregional", "regenerative"
- Domain terminology: "attestation", "governance"
- Acronyms with explanation: "TrustGraph (TG)"

### Organization Detection Patterns

Look for:
- Company mentions: "working with Microsoft"
- Institutions: "Stanford University"
- Partner orgs: "Localism Fund team"
- Government: "the city council"

---

## Wiki-Linking Standards

| Entity Type | Format | Example |
|-------------|--------|---------|
| People | `[[people/First Last]]` | `[[people/Benjamin Life]]` |
| People (alias) | `[[people/First Last\|Display]]` | `[[people/Benjamin Life\|Ben]]` |
| Projects | `[[projects/slug/index]]` | `[[projects/opencivics/index]]` |
| Projects (alias) | `[[projects/slug/index\|Name]]` | `[[projects/opencivics/index\|OpenCivics]]` |
| Concepts | `[[concepts/Name]]` | `[[concepts/Pattern Language]]` |
| Organizations | `[[organizations/Name]]` | `[[organizations/Localism Fund]]` |

### Linking Rules

- Link **first occurrence only** in each section
- Maximum **15-20 links** per document
- Don't link:
  - Common words (the, a, meeting, etc.)
  - Inside code blocks
  - Inside existing links
  - Pronouns (he, she, they)
- **Always create the target file** if it doesn't exist

---

## Project Matching Algorithm

### Signal Weights

| Signal | Weight | Example |
|--------|--------|---------|
| Explicit project name | +5 | "OpenCivics" mentioned |
| Project alias | +4 | "OC" or "civic project" |
| Team member name | +3 | "Benjamin" (if in PROJECT.md team) |
| Project keyword | +2 | "governance" (if in keywords) |
| Related concept | +1 | Links to known project concepts |

### Confidence Thresholds

| Score | Confidence | Action |
|-------|------------|--------|
| ≥10 | Very High | Assign to project |
| 8-9 | High | Assign to project |
| 5-7 | Medium | Assign, add note |
| 3-4 | Low | Assign, flag for review |
| <3 | None | Route to general `meetings/` |

---

## Meeting File Structure

### Target Structure After Processing

```markdown
---
title: "{Descriptive Title}"
date: {ISO timestamp}
duration: {minutes}
status: processed
source: meetily
project: "[[projects/slug/index]]"
participants:
  - "[[people/Person One]]"
  - "[[people/Person Two]]"
themes:
  - {theme-1}
  - {theme-2}  
entities:
  people: ["{Person One}", "{Person Two}"]
  concepts: ["{Concept 1}", "{Concept 2}"]
  organizations: ["{Org 1}"]
action_count: {number}
tags:
  - meeting
  - {project-slug}
processed_at: {timestamp}
confidence: {high|medium|low}
---

# {Meeting Title}

> **Project:** [[projects/slug/index|Project Name]]
> **Date:** {Formatted date}  
> **Participants:** [[people/P1]], [[people/P2]]

## Summary

{2-3 paragraphs summarizing the meeting}

## Key Insights

- {Insight 1}
- {Insight 2}
- {Insight 3}

## Action Items

- [ ] {Task} - @[[people/Assignee]] (due: {date})

## Decisions Made

- {Decision 1}
- {Decision 2}

## Topics Discussed

### {Topic 1}
{Discussion summary with [[wiki-links]]}

### {Topic 2}
{Discussion summary}

## Next Steps

- {Step 1}
- {Step 2}

---

## Full Transcript

{Original transcript with wiki-links added}
```

---

## Entity File Templates

### Person Template

```markdown
---
name: "{Full Name}"
type: person
email: "{if known}"
organization: "{if known}"
role: "{if known}"
first_seen: {date}
tags:
  - person
---

# {Full Name}

First encountered in: [[{meeting path}]]

## Context

{How they were mentioned/their role}

## Meetings

\```dataview
TABLE date, project
FROM "meetings" OR "projects"
WHERE contains(participants, this.file.link)
SORT date DESC
\```
```

### Concept Template

```markdown
---
name: "{Concept Name}"
type: concept
aliases: []
category: "{if known}"
first_seen: {date}
tags:
  - concept
---

# {Concept Name}

First encountered in: [[{meeting path}]]

## Definition

{Definition from context, or placeholder}

## Related Concepts

- [[concepts/Related 1]]

## Mentions

\```dataview
LIST
FROM "meetings" OR "projects"  
WHERE contains(file.outlinks, this.file.link)
SORT date DESC
\```
```

### Organization Template

```markdown
---
name: "{Organization Name}"
type: organization
website: "{if known}"
sector: "{if known}"
first_seen: {date}
tags:
  - organization
---

# {Organization Name}

First encountered in: [[{meeting path}]]

## About

{Context from meeting}

## Key People

- [[people/Known Person]]

## Mentions

\```dataview
LIST  
FROM "meetings" OR "projects"
WHERE contains(file.outlinks, this.file.link)
SORT date DESC
\```
```

---

## File Naming Convention

Format: `YYYY-MM-DD_{descriptive-slug}.md`

- Use kebab-case
- Max 50 characters for slug
- Derive from meeting title or key topic

**Examples:**
- `2024-01-07_q1-planning-sync.md`
- `2024-01-08_theory-of-change-review.md`
- `2024-01-10_client-kickoff-call.md`

---

## Summary Generation

If no summary from Meetily, generate one covering:

1. **Context** - What was the meeting about?
2. **Key Points** - Main topics discussed
3. **Outcomes** - Decisions and action items
4. **Next Steps** - What happens after this meeting?

Target length: 150-300 words

---

## Quality Checklist

Before marking `status: processed`:

- [ ] Title is descriptive (not "Untitled")
- [ ] Summary section populated (150+ words)
- [ ] Key Insights has 2-5 items
- [ ] Action Items extracted (with assignees if mentioned)
- [ ] All participants wiki-linked
- [ ] Person stubs created for new people
- [ ] Concept files created for key terms
- [ ] At least 5 wiki-links in transcript
- [ ] Project matched (or placed in general)
- [ ] File moved to destination
- [ ] `processed_at` timestamp added
