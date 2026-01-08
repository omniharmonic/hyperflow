# Hyperflow

Intelligent Meeting Knowledge System - A local-first, privacy-preserving pipeline that captures meeting audio, transcribes it locally, generates AI summaries, and intelligently organizes outputs into an Obsidian knowledge base.

## What's Included

```
hyperflow/
├── CLAUDE.md                    # Vault context for Claude Code
├── .claude/
│   ├── commands/
│   │   ├── sync-meetily.md      # /sync-meetily command
│   │   ├── ingest-meetings.md   # /ingest-meetings command  
│   │   ├── extract-actions.md   # /extract-actions command
│   │   └── send-followups.md    # /send-followups command
│   └── skills/
│       └── meeting-processor/   # Auto-invoked processing rules
├── scripts/
│   └── sync_meetily.py          # Syncs from Meetily database
├── _templates/                  # Note templates
├── _inbox/meetings/             # Raw meetings land here
├── _drafts/followups/           # Generated email drafts
├── projects/_example-project/   # Example project structure
├── people/                      # Person notes
├── meetings/                    # General/unmatched meetings
└── concepts/                    # Wiki-linkable concepts
```

---

## Installation

### Option A: Fresh Vault

### Option A: Clone as Your Vault

Clone this repository to use as your Obsidian vault:
```bash
git clone https://github.com/omniharmonic/hyperflow.git ~/Documents/my-vault
cd ~/Documents/my-vault
```

### Option B: Add to Existing Vault

Copy the pieces you need:
```bash
# Required
cp -r hyperflow/.claude ~/my-vault/
cp -r hyperflow/scripts ~/my-vault/
cp hyperflow/CLAUDE.md ~/my-vault/

# Recommended
cp -r hyperflow/_templates ~/my-vault/
cp -r hyperflow/_inbox ~/my-vault/
cp -r hyperflow/projects ~/my-vault/
mkdir -p ~/my-vault/{people,meetings,concepts,_drafts/followups}
```

---

## Setup Checklist

### 1. Install Prerequisites

- [ ] **Meetily**: Download from [GitHub Releases](https://github.com/Zackriya-Solutions/meeting-minutes/releases)
- [ ] **Ollama**: Install from [ollama.ai](https://ollama.ai)
  ```bash
  ollama pull llama3.2
  ```
- [ ] **Python 3**: Usually pre-installed on macOS/Linux

### 2. Configure Vault

- [ ] Open vault in Obsidian
- [ ] Install recommended plugins:
  - Dataview (for meeting lists)
  - Templater (optional, for templates)

### 3. Create Your First Project

```bash
cd ~/my-vault/projects
cp -r _example-project my-project
```

Edit `my-project/PROJECT.md`:
- Add your team members
- Add keywords that identify this project
- Update aliases

### 4. Record a Test Meeting

1. Open Meetily
2. Start recording
3. Talk for 30 seconds
4. Stop and let it generate a summary

---

## Usage

### First Time Setup

```
1. Open vault in Claude Code
2. /setup              ← Finds Meetily DB, configures paths
3. /add-project        ← Create your first project
```

### Daily Workflow

```
1. Record meetings in Meetily (normal usage)
2. /sync-meetily       ← Pull new meetings into vault
3. /ingest-meetings    ← Process and route to projects
```

### Command Reference

| Command | What It Does |
|---------|--------------|
| `/setup` | **Run first!** Finds Meetily DB, configures vault path |
| `/sync-meetily` | Exports new meetings from Meetily's database to `_inbox/meetings/` |
| `/sync-meetily --all` | Re-exports all meetings (fresh start) |
| `/sync-meetily --list` | Shows meetings in Meetily database |
| `/sync-meetily --db /path/to/db` | Use custom database path |
| `/ingest-meetings` | Processes inbox, matches to projects, adds links |
| `/ingest-meetings path/to/file.md` | Process a specific file |
| `/add-project` | Interactive wizard to create a new project |
| `/extract-actions path/to/meeting.md` | Extract action items |
| `/send-followups path/to/meeting.md` | Generate follow-up emails |

---

## Configuration

### Environment Variables (Optional)

Set these to override auto-detection:

```bash
# In ~/.zshrc or ~/.bashrc:
export MEETILY_DB_PATH="~/Library/Application Support/ai.meetily.app/meeting_minutes.sqlite"
export HYPERFLOW_VAULT="~/Documents/my-vault"
```

### Command-Line Overrides

```bash
# Specify database path directly
python3 scripts/sync_meetily.py --db /path/to/database.sqlite

# Specify vault path directly  
python3 scripts/sync_meetily.py --vault /path/to/vault
```

### Default Locations

| Setting | macOS | Windows | Linux |
|---------|-------|---------|-------|
| Meetily DB | `~/Library/Application Support/ai.meetily.app/` | `%APPDATA%/ai.meetily.app/` | `~/.local/share/ai.meetily.app/` |
| Vault | Script's parent directory | Script's parent directory | Script's parent directory |

---

## How It Works

### Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Meetily   │ ──► │  SQLite DB  │ ──► │ /sync-      │ ──► │ _inbox/     │
│  (vanilla)  │     │  (native)   │     │  meetily    │     │  meetings/  │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                   │
                    ┌─────────────┐     ┌─────────────┐            │
                    │ projects/   │ ◄── │ /ingest-    │ ◄──────────┘
                    │ */meetings/ │     │  meetings   │
                    └─────────────┘     └─────────────┘
```

### Project Matching

When you run `/ingest-meetings`, Claude Code:

1. Reads each file in `_inbox/meetings/` with `status: pending_enrichment`
2. Loads all `PROJECT.md` files to get team, keywords, aliases
3. Scores each project based on content matches:
   - Project name mentioned: +5 points
   - Alias mentioned: +4 points
   - Team member name: +3 points
   - Keyword found: +2 points
4. Routes to highest-scoring project (if ≥4 points) or `meetings/` folder

---

## Customization

### Add a New Project

**Option A: Interactive (Recommended)**

Run `/add-project` in Claude Code. It will guide you through:
- Project name and aliases
- Team members and emails
- Keywords for auto-matching
- Related links

**Option B: Manual**

1. Create folder: `projects/my-project/`
2. Create `PROJECT.md` with:
   - Team members (name + email)
   - Keywords unique to this project
   - Aliases (short names people use)
3. Create `index.md` for the project overview
4. Create `meetings/` subfolder

### Adjust Matching Sensitivity

Edit `.claude/skills/meeting-processor/SKILL.md`:
- Change signal weights
- Adjust threshold values

---

## Troubleshooting

### "Meetily database not found"

1. Open Meetily and record at least one meeting
2. Check database exists:
   ```bash
   ls ~/Library/Application\ Support/ai.meetily.app/
   ```

### Meetings not matching to projects

1. Check `PROJECT.md` has keywords that appear in transcripts
2. Add team member names exactly as they appear in Meetily
3. Run `/ingest-meetings` with a specific file to see debug output

### Command not recognized

1. Ensure `.claude/commands/` folder exists in vault root
2. Check file has correct frontmatter with `---` delimiters
3. Restart Claude Code session

---

## Files to Delete After Testing

- `_inbox/meetings/_EXAMPLE_*.md` - Test meeting file
- `projects/_example-project/` - Example project (after creating your own)

---

## Support

- [Meetily GitHub](https://github.com/Zackriya-Solutions/meeting-minutes)
- [Claude Code Docs](https://docs.anthropic.com/claude-code)
- [Obsidian Help](https://help.obsidian.md)

