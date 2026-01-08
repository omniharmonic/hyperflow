---
description: Process pending meetings from inbox - extract entities, create wiki links, generate summaries, route to projects
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
argument-hint: [optional: specific file to process]
---

# Ingest Meetings

Process all markdown files in `_inbox/meetings/` — works with Meetily exports, Fathom, Otter, or manual notes.

## Overview

This command transforms raw meeting transcripts into rich, interconnected knowledge base entries by:
1. Auto-detecting the source format (Meetily, Fathom, Otter, manual)
2. Extracting and creating entity files (people, concepts, organizations)
3. Generating or using existing summaries
4. Adding wiki-links throughout the content
5. Routing to the appropriate project folder

---

## Supported Sources

| Source | How to Add | What to Expect |
|--------|-----------|----------------|
| **Meetily** | `/sync-meetily` | Full transcript + AI summary |
| **Fathom** | Export → paste into `_templates/fathom-import.md` | Transcript + summary + action items |
| **Otter** | Export TXT → paste into `_templates/otter-import.md` | Transcript + summary + outline |
| **Manual** | Create file or use `_templates/quick-meeting.md` | Generate everything from transcript |
| **Plain text** | Drop `.txt` file in `_inbox/meetings/` | Auto-convert and process |

---

## Workflow

### Step 1: Find Pending Files

```bash
ls _inbox/meetings/*.md _inbox/meetings/*.txt 2>/dev/null
```

Process files that:
- Have `status: pending_enrichment` in frontmatter, OR
- Have no frontmatter (plain text drop), OR
- Have `status:` missing (assume pending)

If `$ARGUMENTS` provided, process only that specific file.

### Step 1b: Auto-Detect Source Format

For each file, detect the source by checking:

1. **Frontmatter `source:` field** - explicit declaration
2. **Content patterns:**
   - Meetily: `"result_json"`, timestamps like `00:15:23`
   - Fathom: `Speaker Name (HH:MM:SS)` format, "Key Points" section
   - Otter: `Speaker N  M:SS` format, "Outline" section
   - Manual: No recognized patterns → treat as general notes

3. **File extension:**
   - `.txt` files → convert to markdown, treat as manual
   
**Set `detected_source` for use in later steps.**

### Step 2: Load Project Context

Read all `projects/*/PROJECT.md` files to build matching context:
- Project names and aliases
- Team member names and emails
- Keywords for matching

### Step 3: Normalize Source Format

Before processing, normalize the content based on detected source:

#### Meetily Format
- Summary usually in frontmatter or `## Summary` section
- Transcript has timestamps: `[00:15:23] Speaker: Text`
- Action items may be pre-extracted
- **Use existing summary if present**

#### Fathom Format
- Look for summary at top of content
- Transcript format: `Speaker Name (00:00:00)\nText...`
- Key Points section often present
- Action items often pre-extracted
- **Preserve Fathom's summary and action items**

#### Otter Format
- Summary usually at the very top
- Transcript format: `Speaker 1  0:00\nText...`
- May have Outline/Chapters section
- Action items sometimes extracted
- **Preserve Otter's summary if present**

#### Manual / Plain Text
- No structured sections expected
- May be raw meeting notes or pasted transcript
- **Generate summary from content**
- **Extract action items from text patterns**

### Step 4: For Each Pending Meeting

---

## Entity Extraction (CRITICAL)

Analyze the transcript and identify ALL entities:

### People
- Names mentioned in speech
- Email addresses referenced
- Speakers in the conversation
- Anyone assigned action items

### Organizations
- Companies mentioned
- Institutions referenced
- Partner organizations

### Concepts
- Technical terms discussed
- Methodologies mentioned
- Frameworks referenced
- Domain-specific terminology

### Tools/Platforms
- Software tools discussed
- Platforms mentioned
- Services referenced

**Output a list of all extracted entities with their type.**

---

## Entity File Creation

### For Each Person

Check if `people/{Name}.md` exists. If not, create:

```markdown
---
name: "{Full Name}"
type: person
email: "{if known}"
organization: "{if mentioned}"
role: "{if mentioned}"
first_seen: {meeting date}
tags:
  - person
---

# {Full Name}

First encountered in: [[{path to this meeting}]]

## Context

{Brief note about how they were mentioned}

## Meetings

<!-- Dataview query will show related meetings -->

## Notes

<!-- Add more context as you learn about this person -->
```

### For Each Concept

Check if `concepts/{Concept}.md` exists. If not, create:

```markdown
---
name: "{Concept Name}"
type: concept
aliases:
  - "{any alternative names}"
first_seen: {meeting date}
tags:
  - concept
---

# {Concept Name}

First encountered in: [[{path to this meeting}]]

## Definition

{Brief definition based on meeting context, or leave as TODO}

## Related

- [[other related concepts if known]]

## Mentions

<!-- Meetings where this concept appears -->
```

### For Each Organization

Check if `organizations/{Org}.md` exists (create folder if needed). If not, create:

```markdown
---
name: "{Organization Name}"
type: organization
website: "{if mentioned}"
first_seen: {meeting date}
tags:
  - organization
---

# {Organization Name}

First encountered in: [[{path to this meeting}]]

## About

{Brief description based on context}

## People

- [[people who work here if mentioned]]

## Mentions

<!-- Meetings where this org appears -->
```

---

## Meeting File Enrichment

Transform the meeting file to have this structure:

```markdown
---
title: "{Cleaned descriptive title}"
date: {ISO timestamp}
duration: {minutes if known}
status: processed
source: {meetily|fathom|otter|manual}
original_source: "{keep original if provided}"
project: "[[projects/{matched}/index]]"
participants:
  - "[[people/Person One]]"
  - "[[people/Person Two]]"
themes:
  - {theme-1}
  - {theme-2}
tags:
  - meeting
  - {project-slug}
  - {source}
processed_at: {current ISO timestamp}
confidence: {high|medium|low}
---

# {Meeting Title}

> **Project:** [[projects/{project}/index]]
> **Date:** {formatted date}
> **Participants:** [[people/Person One]], [[people/Person Two]]

## Summary

{2-3 paragraph summary of the meeting.

**Source-specific handling:**
- **Meetily/Fathom/Otter with existing summary:** Use and lightly edit for consistency
- **Manual/plain text:** Generate comprehensive summary from content
- **Always include:** Main topic, key outcomes, notable discussions}

## Key Insights

- {Most important insight or decision}
- {Second key insight}
- {Third key insight}

## Action Items

{Extract action items with assignees and due dates.

**Source-specific handling:**
- **Fathom/Otter with action items:** Use their extracted items, normalize format
- **Meetily:** Check for action items in summary or transcript
- **Manual:** Search for patterns like "will do", "action:", "TODO:", "@name to..."

**Format:**}
- [ ] {Action item 1} - @[[people/Assignee]] (due: {date if mentioned})
- [ ] {Action item 2} - @[[people/Assignee]]
- [ ] {Action item 3}

## Decisions Made

- {Decision 1 and its context}
- {Decision 2}

## Topics Discussed

### {Topic 1}

{Brief summary of discussion around this topic, with [[wiki-links]] to relevant concepts}

### {Topic 2}

{Brief summary}

## Next Steps

- {Next step 1}
- {Next step 2}

---

## Full Transcript

{Original transcript with wiki-links added for first occurrences of:
- People → [[people/Name]]
- Projects → [[projects/slug/index]]  
- Concepts → [[concepts/Term]]
- Organizations → [[organizations/Name]]
}
```

---

## Wiki-Linking Rules

### What to Link
- **People:** First mention of each person → `[[people/Full Name]]`
- **Projects:** Project names/aliases → `[[projects/slug/index|Display Name]]`
- **Concepts:** Technical terms, methodologies → `[[concepts/Term]]`
- **Organizations:** Companies, institutions → `[[organizations/Name]]`

### Linking Guidelines
- Link first occurrence only (don't over-link)
- Maximum 15-20 links per document
- Don't link common words or obvious terms
- Preserve original text in display: `[[people/Benjamin Life|Benjamin]]`
- Skip linking inside code blocks or quotes

---

## Project Matching

Score each project based on content:

| Signal | Weight |
|--------|--------|
| Project name in content | +5 |
| Project alias mentioned | +4 |
| Team member name found | +3 |
| Project keyword found | +2 |

**Thresholds:**
- ≥8 points: Strong match → `projects/[name]/meetings/`
- 4-7 points: Moderate match → same, add confidence note
- <4 points: No match → `meetings/YYYY-MM-DD/`

---

## File Placement

After enrichment, move the file:

**If project matched:**
```
projects/{project-slug}/meetings/YYYY-MM-DD_{descriptive-slug}.md
```

**If no match:**
```
meetings/YYYY-MM-DD/{descriptive-slug}.md
```

---

## Quality Checklist

Before marking complete, verify:
- [ ] Summary section is populated
- [ ] Key Insights has 2-5 items
- [ ] Action Items extracted (if any mentioned)
- [ ] All participants have wiki-links
- [ ] Person files created for new people
- [ ] Concept files created for key terms
- [ ] Project correctly matched (or placed in general)
- [ ] File moved to destination folder
- [ ] Status updated to `processed`

---

## Example Output

After processing `2024-01-08T06-15_untitled.md`:

**Created files:**
```
✅ people/Sarah Chen.md (new)
✅ people/Marcus Johnson.md (new)
✅ concepts/Pattern Language.md (new)
✅ concepts/Theory of Change.md (new)
✅ organizations/Localism Fund.md (new)
```

**Moved:**
```
_inbox/meetings/2024-01-08T06-15_untitled.md
  → projects/opencivics/meetings/2024-01-08_theory-of-change-planning.md
```

**Summary:**
```
Processed: 1 meeting
Project: OpenCivics (confidence: high, score: 12)
Entities created: 3 people, 2 concepts, 1 organization
Wiki-links added: 14
```

---

## Step 10: Suggest Task Sync

If action items were found during processing:

```
→ Found {N} action items assigned to {M} people.
→ Run /sync-tasks to add them to person profiles.
```

---

## Error Handling

If any step fails:
1. Do not delete original file from inbox
2. Update file status to `error`
3. Add `error_message` to frontmatter
4. Continue with next file
5. Report errors in final summary

---

## Quick Reference: Adding Meetings Manually

### Option 1: Quick Drop (Fastest)
```bash
# Create file directly
cat > _inbox/meetings/my-meeting.md << 'EOF'
---
date: 2024-01-15T14:00
status: pending_enrichment
---

[Paste your transcript or notes here]
EOF
```

### Option 2: Use Templates
```bash
# Copy appropriate template
cp _templates/fathom-import.md _inbox/meetings/client-call.md
cp _templates/otter-import.md _inbox/meetings/team-sync.md
cp _templates/quick-meeting.md _inbox/meetings/quick-notes.md
```

### Option 3: Plain Text Drop
```bash
# Just drop a .txt file - will auto-convert
mv ~/Downloads/meeting-transcript.txt _inbox/meetings/
```

### Then Process
```
/ingest-meetings
```

---

## Tips for Each Source

### Fathom
1. After your meeting, go to Fathom dashboard
2. Click on the meeting → "Summary" tab
3. Copy summary, action items, and transcript
4. Paste into `_templates/fathom-import.md`
5. Save to `_inbox/meetings/`

### Otter
1. Open your transcript in Otter
2. Click Share → Export → TXT (or Copy)
3. Paste into `_templates/otter-import.md`
4. Save to `_inbox/meetings/`

### Quick Notes
If you just have raw notes or a transcript from any source:
1. Create new file in `_inbox/meetings/`
2. Add minimal frontmatter: `date:` and `status: pending_enrichment`
3. Paste content below
4. Run `/ingest-meetings`

The AI will figure out the rest!
