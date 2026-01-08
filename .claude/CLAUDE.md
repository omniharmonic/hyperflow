# Knowledge Vault

This is a personal knowledge management system with automated meeting transcript integration.

## Directory Structure

```
├── _inbox/meetings/     # Raw meeting exports from Meetily - process with /ingest-meetings
├── _templates/          # Note templates (Templater plugin)
├── projects/            # Project folders, each with PROJECT.md context file
│   └── [project-name]/
│       ├── PROJECT.md   # Project context (team, links, keywords)
│       ├── meetings/    # Processed meeting notes
│       └── shared/      # Google Drive synced folder for collaborators
├── people/              # Person notes with contact info and context
├── meetings/            # General meetings not associated with a project
│   └── [YYYY-MM-DD]/
└── concepts/            # Concept notes for wiki-linking
```

## Key Commands

| Command | Description |
|---------|-------------|
| `/ingest-meetings` | Process all pending files in _inbox/meetings/ |
| `/extract-actions` | Pull action items from recent meeting and create Notion tasks |
| `/send-followups` | Draft follow-up emails for meeting participants |

## File Conventions

### Frontmatter Required Fields
All notes should include:
```yaml
---
title: "Note Title"
date: YYYY-MM-DDTHH:mm:ss
status: draft | processed | reviewed
tags: [tag1, tag2]
---
```

### Meeting Notes Additional Fields
```yaml
project: "[[projects/project-name/index]]"
participants:
  - "[[people/Person Name]]"
duration: 45  # minutes
themes: [theme1, theme2]
```

## Linking Rules

- **People:** `[[people/First Last]]` - create stub if missing
- **Projects:** `[[projects/project-slug/index]]`
- **Concepts:** `[[concepts/Concept Name]]` if exists
- Link first occurrence only, max ~10 links per doc

## Tags

Standard tags to use:
- `#meeting` - all meeting notes
- `#action-item` - tasks to extract
- `#draft` - needs review
- `#shared` - synced to collaborators

## Project Context

Each project folder contains PROJECT.md with:
- Team members (name, email, role)
- Notion workspace and database IDs
- Keywords for auto-matching
- Aliases (alternative names)

Read these files when determining where to route meeting notes.

## MCP Integration

- **Notion:** Available for task creation - use `notion_tasks_database` ID from PROJECT.md
- **Obsidian MCP:** If running via plugin, vault operations available

## Processing Workflow

1. Meetily exports completed meetings to `_inbox/meetings/`
2. User runs `/ingest-meetings` (or can automate)
3. Claude Code:
   - Reads each pending file
   - Matches to project via PROJECT.md context
   - Enriches metadata and adds wiki-links
   - Moves to target folder
4. Google Drive syncs shared folders to collaborators

## Quality Standards

- Preserve all original transcript content
- Use kebab-case for file names
- ISO format for all dates
- UTF-8 encoding
- Max 50 char slugs in filenames
