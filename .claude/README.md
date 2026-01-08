# Intelligent Meeting Knowledge System - Claude Code Configurations

This package contains all the Claude Code configuration files needed to set up the intelligent meeting processing pipeline described in the PRD.

## Quick Start

1. Copy the `.claude/` folder structure to your Obsidian vault root
2. Copy `CLAUDE.md` to your vault root
3. Create your first `PROJECT.md` in `projects/your-project/`
4. Install Meetily and configure export path to `_inbox/meetings/`
5. Run `/ingest-meetings` to process your first meeting!

## Package Contents

```
claude-configs/
├── CLAUDE.md                    # Vault context file (copy to vault root)
├── commands/
│   ├── ingest-meetings.md       # Primary processing command
│   ├── extract-actions.md       # Action item extraction + Notion
│   └── send-followups.md        # Email draft generation
├── skills/
│   └── meeting-processor/
│       └── SKILL.md             # Auto-invoked processing rules
└── templates/
    ├── PROJECT.md               # Project context template
    └── meeting-note.md          # Processed meeting format
```

## Installation

### Step 1: Set Up Directory Structure

In your Obsidian vault:

```bash
mkdir -p .claude/commands
mkdir -p .claude/skills/meeting-processor
mkdir -p _inbox/meetings
mkdir -p _templates
mkdir -p projects
mkdir -p people
mkdir -p meetings
```

### Step 2: Copy Configuration Files

```bash
# Copy CLAUDE.md to vault root
cp CLAUDE.md /path/to/vault/

# Copy commands
cp commands/*.md /path/to/vault/.claude/commands/

# Copy skills
cp skills/meeting-processor/SKILL.md /path/to/vault/.claude/skills/meeting-processor/

# Copy templates
cp templates/*.md /path/to/vault/_templates/
```

### Step 3: Create Your First Project

1. Create folder: `projects/your-project-name/`
2. Copy `templates/PROJECT.md` to `projects/your-project-name/PROJECT.md`
3. Fill in your project details, team members, and Notion IDs
4. Create `meetings/` and `shared/` subdirectories

### Step 4: Configure Meetily Export

In your Meetily fork or settings:
- Set export path: `[vault-path]/_inbox/meetings/`
- Enable automatic export on meeting completion
- Format: Markdown with YAML frontmatter

## Usage

### Processing New Meetings

After a meeting is transcribed and exported:

```
/ingest-meetings
```

This will:
- Scan `_inbox/meetings/` for pending files
- Match each meeting to a project
- Enrich metadata and add wiki-links
- Move to the correct project folder

### Extracting Action Items

After processing a meeting:

```
/extract-actions recent
# or
/extract-actions projects/opencivics/meetings/2026-01-07-sync.md
```

This will:
- Parse action items from the meeting
- Present for confirmation
- Create tasks in Notion (if configured)

### Generating Follow-up Emails

```
/send-followups recent
```

This will:
- Generate personalized emails for each participant
- Save drafts to `_drafts/followups/`
- Include their specific action items

## Customization

### Adding New Projects

1. Create `projects/[project-name]/` folder
2. Copy `PROJECT.md` template
3. Fill in:
   - Team members with emails
   - Notion workspace/database IDs
   - Keywords for auto-matching
   - Project aliases

### Modifying Processing Rules

Edit `.claude/skills/meeting-processor/SKILL.md` to:
- Change wiki-linking rules
- Adjust project matching weights
- Modify tag conventions

### Custom Commands

Create new `.md` files in `.claude/commands/` with:
- Frontmatter: `description`, `allowed-tools`
- Markdown body: instructions for Claude

## Requirements

- Claude Code CLI installed and authenticated
- Obsidian with community plugins enabled
- (Optional) Notion MCP configured for task creation
- (Optional) Meetily fork with export modifications

## Troubleshooting

### Meetings not being matched to projects

- Check PROJECT.md has relevant keywords
- Verify team member names match how they appear in transcripts
- Add aliases for common variations

### Notion tasks not creating

- Verify MCP is configured: `claude mcp list`
- Check Notion database ID is correct in PROJECT.md
- Ensure integration has database access

### Files stuck in inbox

- Check file has `status: pending_enrichment` in frontmatter
- Verify Claude Code has write permissions to vault

## Contributing

This is an open-source template. Feel free to:
- Modify for your workflow
- Share improvements
- Create variations for different use cases

## License

MIT - Use freely, attribution appreciated.
