# Hyperflow Knowledge Vault

Automated meeting-to-knowledge pipeline using Meetily + Claude Code + Obsidian.

## Quick Start

1. **Record a meeting** in [Meetily](https://github.com/Zackriya-Solutions/meeting-minutes)
2. **Sync**: Run `/sync-meetily` to export from Meetily's database
3. **Process**: Run `/ingest-meetings` to enrich and route to projects

## Commands

| Command | Description |
|---------|-------------|
| `/sync-meetily` | Export new meetings from Meetily's database to `_inbox/meetings/` |
| `/ingest-meetings` | Process pending meetings, match to projects, add wiki-links |
| `/extract-actions` | Extract action items from a meeting note |
| `/send-followups` | Generate follow-up email drafts for participants |

## Directory Structure

```
├── _inbox/meetings/     # Raw Meetily exports land here
├── _templates/          # Note templates
├── _drafts/followups/   # Generated email drafts
├── projects/            # Project folders
│   └── [project-name]/
│       ├── PROJECT.md   # Project context (team, keywords)
│       ├── index.md     # Project overview
│       └── meetings/    # Processed meeting notes
├── people/              # Person notes
├── meetings/            # General/unmatched meetings
├── concepts/            # Wiki-linkable concepts
└── scripts/             # Utility scripts (sync_meetily.py)
```

## Workflow

```
Meetily → /sync-meetily → _inbox/meetings/ → /ingest-meetings → projects/*/meetings/
```

## Project Matching

Meetings are matched to projects using signals from `PROJECT.md`:

| Signal | Weight |
|--------|--------|
| Explicit project name | 5 |
| Project alias | 4 |
| Team member name | 3 |
| Project keyword | 2 |

**Thresholds:** ≥8 = strong match, 4-7 = moderate, <4 = general meetings folder

## Linking Rules

| Type | Format |
|------|--------|
| People | `[[people/First Last]]` |
| Projects | `[[projects/slug/index]]` |
| Concepts | `[[concepts/Name]]` |

- Link first occurrence only
- Max 10-15 links per document
- Create person stubs if missing

## Setup Checklist

- [ ] Install [Meetily](https://github.com/Zackriya-Solutions/meeting-minutes/releases)
- [ ] Install [Ollama](https://ollama.ai) and pull a model (`ollama pull llama3.2`)
- [ ] Create at least one project in `projects/` with a `PROJECT.md`
- [ ] Record a test meeting
- [ ] Run `/sync-meetily` then `/ingest-meetings`

