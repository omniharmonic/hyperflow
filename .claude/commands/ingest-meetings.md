---
description: Process new meeting transcripts from inbox, enrich with metadata, and route to correct project folders
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
argument-hint: [optional: specific file to process]
---

# Meeting Ingestion Workflow

Process all markdown files in `_inbox/meetings/` that have `status: pending_enrichment` in their frontmatter.

## Pre-Processing Check

1. List all files in `_inbox/meetings/` using Glob
2. Filter for `.md` files with pending status
3. If `$ARGUMENTS` provided, process only that specific file
4. If no files found, inform user and exit

## For Each File, Execute These Steps

### Step 1: Read and Parse

Read the meeting file and extract:
- Full transcript content
- Summary (if present)
- Any existing frontmatter metadata
- Meeting date and duration

### Step 2: Load Project Context

Read all `PROJECT.md` files from `projects/*/PROJECT.md` to build context:
- Project names and aliases
- Team member names and emails
- Keywords associated with each project
- Notion workspace IDs for later action item routing

### Step 3: Project Matching

Analyze transcript content to determine project association:

**Matching signals (in priority order):**
1. Direct project name mention (e.g., "OpenCivics", "TrustGraph")
2. Project aliases from PROJECT.md `aliases` field
3. Team member names matching `team` entries in any PROJECT.md
4. Keyword density matching `keywords` arrays

**Decision logic:**
- If single strong match (>3 signals): assign to that project
- If multiple matches: assign to highest signal count, note others in metadata
- If no match: route to `meetings/[YYYY-MM-DD]/` general folder

### Step 4: Metadata Enrichment

Update the frontmatter with:

```yaml
---
title: "[Cleaned title from content or filename]"
date: [ISO timestamp]
duration: [minutes if available]
status: processed
project: "[[projects/[matched-project]/index]]"
participants:
  - "[[people/Person Name]]"
themes:
  - theme-one
  - theme-two
tags:
  - meeting
  - [project-slug]
  - [primary-theme]
processed_at: [current ISO timestamp]
---
```

### Step 5: Wiki-Linking

Scan the content for linkable concepts:

**Auto-link:**
- People mentioned → `[[people/Person Name]]`
- Projects mentioned → `[[projects/project-name/index]]`
- Known concepts in vault (check existing files)
- Tools/platforms discussed (if notes exist)

**Linking rules:**
- Only link first occurrence of each term
- Don't over-link (max ~10 links per document)
- Preserve original text, wrap with brackets

### Step 6: Create Missing Notes

For each participant not already in `people/`:
- Create stub file: `people/[Name].md`
- Frontmatter: `name`, `first_seen` (meeting date)
- Add TODO comment to fill in details

### Step 7: File Placement

Move the enriched file to target location:
- **If project matched:** `projects/[project-name]/meetings/[filename].md`
- **If no match:** `meetings/[YYYY-MM-DD]/[filename].md`

### Step 8: Cleanup

- Remove original from `_inbox/meetings/`
- Log processing result

## Post-Processing Report

After processing all files, output summary:
- Number of files processed
- Project assignments made
- New people notes created
- Any files that couldn't be processed (with reason)

## Error Handling

If any step fails:
1. Do not delete original file from inbox
2. Update file status to `error`
3. Add `error_message` to frontmatter
4. Continue with next file
5. Report errors in final summary
