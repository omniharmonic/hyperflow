---
description: Export new meetings from Meetily's database to _inbox/meetings/
allowed-tools: Bash, Read, Write, Glob
argument-hint: [--all to re-export all, --list to show meetings]
---

# Sync Meetily Meetings

Export meetings from Meetily's native SQLite database to the vault inbox.

## Execution

Run the sync script located in this vault:

```bash
python3 scripts/sync_meetily.py $ARGUMENTS
```

**Arguments:**
- (none): Export only new/unsynced meetings
- `--all`: Force re-export all meetings  
- `--list`: List meetings in database without exporting
- `--meeting-id ID`: Export a specific meeting
- `--db /path/to/db`: Use custom database path

## After Syncing

1. Report how many meetings were exported
2. List the new files in `_inbox/meetings/`
3. Suggest running `/ingest-meetings` to process them

## Database Location

Meetily stores its database at:
- **macOS**: `~/Library/Application Support/ai.meetily.app/meeting_minutes.sqlite`
- **Windows**: `%APPDATA%/ai.meetily.app/meeting_minutes.sqlite`

Or set via environment variable: `MEETILY_DB_PATH`

## Troubleshooting

If "database not found":
1. Make sure Meetily has been run at least once
2. Record and complete at least one meeting
3. Check if database exists at the paths above
4. Use `--db /path/to/database.sqlite` to specify custom path

