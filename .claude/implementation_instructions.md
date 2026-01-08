# AI Coding Agent Implementation Prompt
## Intelligent Meeting Knowledge System

---

## Context

You are an expert software engineer tasked with implementing the **Intelligent Meeting Knowledge System** — a local-first, privacy-preserving pipeline that captures meeting audio, transcribes it locally, generates AI summaries, and intelligently organizes outputs into an Obsidian knowledge base.

The complete Product Requirements Document (PRD) is available at:
```
./docs/intelligent-meeting-knowledge-system-prd.md
```

**Read the PRD thoroughly before beginning any implementation work.**

---

## Project State

### What Already Exists

The following Claude Code configuration files have been created and placed in the `.claude/` directory:

```
.claude/
├── commands/
│   ├── ingest-meetings.md      # Slash command for processing inbox
│   ├── extract-actions.md      # Action item extraction command
│   └── send-followups.md       # Follow-up email generation command
└── skills/
    └── meeting-processor/
        └── SKILL.md            # Auto-invoked processing rules
```

**IMPORTANT:** These files are complete and tested. Do NOT modify them unless explicitly instructed. Your task is to build the infrastructure that these commands will operate on.

### What You Need to Create

1. **Project CLAUDE.md** — The root-level context file for this repository (NOT the Obsidian vault CLAUDE.md specified in the PRD — that's a different file for a different location)
2. **Meetily fork modifications** — Export pipeline to generate markdown
3. **Obsidian vault scaffold** — Directory structure and templates
4. **Integration layer** — Scripts/configs connecting components
5. **Documentation** — Setup guides, configuration docs

---

## Implementation Priorities

Execute in this order:

### Priority 1: Project Setup & Documentation

**Task 1.1: Create project CLAUDE.md**

Create a `CLAUDE.md` file at the project root that describes THIS repository (the implementation codebase), not the target Obsidian vault. Include:

```markdown
# Intelligent Meeting Knowledge System

## Project Overview
Implementation repository for the meeting-to-knowledge pipeline.

## Directory Structure
[document the repo structure you create]

## Key Components
- `/meetily-fork/` — Modified Meetily with markdown export
- `/obsidian-scaffold/` — Template vault structure
- `/scripts/` — Utility scripts for setup and maintenance
- `/docs/` — Documentation including PRD

## Development Commands
[add as you implement]

## Architecture Notes
[reference PRD, explain implementation decisions]
```

**Task 1.2: Create directory structure**

```
project-root/
├── CLAUDE.md                           # Project context (create this)
├── README.md                           # User-facing setup guide
├── docs/
│   ├── intelligent-meeting-knowledge-system-prd.md
│   ├── SETUP.md                        # Detailed installation guide
│   ├── CONFIGURATION.md                # Configuration reference
│   └── TROUBLESHOOTING.md              # Common issues
├── meetily-fork/
│   └── [modifications only, not full fork]
├── obsidian-scaffold/
│   ├── .claude/                        # [already exists - DO NOT MODIFY]
│   ├── CLAUDE.md                       # Vault context file (from PRD)
│   ├── _inbox/
│   │   └── meetings/
│   │       └── .gitkeep
│   ├── _templates/
│   │   ├── meeting-note.md
│   │   ├── person.md
│   │   └── PROJECT-template.md
│   ├── _drafts/
│   │   └── followups/
│   │       └── .gitkeep
│   ├── projects/
│   │   └── _example-project/
│   │       ├── PROJECT.md
│   │       ├── index.md
│   │       ├── meetings/
│   │       │   └── .gitkeep
│   │       └── shared/
│   │           └── .gitkeep
│   ├── people/
│   │   └── .gitkeep
│   ├── meetings/
│   │   └── .gitkeep
│   └── concepts/
│       └── .gitkeep
└── scripts/
    ├── setup.sh                        # One-command setup
    ├── install-meetily.sh              # Meetily installation
    ├── configure-ollama.sh             # Ollama model setup
    └── init-vault.sh                   # Vault initialization
```

---

### Priority 2: Meetily Fork Implementation

This is the critical integration point. You need to create the modifications that will be applied to a Meetily fork.

**Task 2.1: Create export module**

Create `meetily-fork/backend/app/export.py`:

```python
"""
Markdown export functionality for Meetily.

This module provides automated export of completed meetings to markdown format
with YAML frontmatter, suitable for processing by Claude Code in an Obsidian vault.

Usage:
    This module is called automatically when a meeting is marked complete.
    Configure export path via MEETILY_EXPORT_PATH environment variable.
"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Default export path - override with MEETILY_EXPORT_PATH env var
DEFAULT_EXPORT_PATH = os.path.expanduser('~/Documents/obsidian-vault/_inbox/meetings')


def get_export_path() -> Path:
    """Get the configured export path for markdown files."""
    path = os.getenv('MEETILY_EXPORT_PATH', DEFAULT_EXPORT_PATH)
    return Path(path)


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """
    Convert a meeting title to a kebab-case filename slug.
    
    Args:
        title: The meeting title to convert
        max_length: Maximum length of the resulting slug
        
    Returns:
        A sanitized, kebab-case string suitable for filenames
    """
    if not title:
        return 'untitled-meeting'
    
    # Remove non-alphanumeric characters (except spaces and hyphens)
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower())
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    # Truncate to max length, avoiding mid-word cuts
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit('-', 1)[0]
    
    return slug or 'untitled-meeting'


def format_duration(seconds: Optional[int]) -> int:
    """Convert duration in seconds to minutes, rounded."""
    if not seconds:
        return 0
    return round(seconds / 60)


def extract_speakers(transcript_segments: List[Dict[str, Any]]) -> List[str]:
    """
    Extract unique speaker names from transcript segments.
    
    Args:
        transcript_segments: List of transcript segment dicts with 'speaker' key
        
    Returns:
        List of unique speaker names, excluding None/Unknown
    """
    speakers = set()
    for segment in transcript_segments:
        speaker = segment.get('speaker')
        if speaker and speaker.lower() not in ('unknown', 'none', ''):
            speakers.add(speaker)
    return sorted(list(speakers))


def generate_frontmatter(
    meeting: Dict[str, Any],
    transcript_segments: List[Dict[str, Any]]
) -> str:
    """
    Generate YAML frontmatter for the meeting markdown file.
    
    Args:
        meeting: Meeting record from database
        transcript_segments: List of transcript segments
        
    Returns:
        YAML frontmatter string including delimiters
    """
    title = meeting.get('title', 'Untitled Meeting')
    created_at = meeting.get('created_at', datetime.now())
    duration = format_duration(meeting.get('duration_seconds'))
    speakers = extract_speakers(transcript_segments)
    
    # Format datetime
    if isinstance(created_at, str):
        date_str = created_at
    else:
        date_str = created_at.isoformat()
    
    # Build frontmatter
    lines = [
        '---',
        f'title: "{title}"',
        f'date: {date_str}',
        f'duration: {duration}',
        'status: pending_enrichment',
        'source: meetily',
    ]
    
    # Add speakers if detected
    if speakers:
        lines.append('speakers:')
        for speaker in speakers:
            lines.append(f'  - "{speaker}"')
    
    # Standard tags
    lines.append('tags:')
    lines.append('  - meeting')
    lines.append('  - unprocessed')
    
    lines.append('---')
    
    return '\n'.join(lines)


def generate_markdown_body(
    meeting: Dict[str, Any],
    transcript_segments: List[Dict[str, Any]],
    summary: Optional[Dict[str, Any]]
) -> str:
    """
    Generate the markdown body content.
    
    Args:
        meeting: Meeting record
        transcript_segments: List of transcript segments
        summary: Summary record (may be None)
        
    Returns:
        Markdown body string
    """
    title = meeting.get('title', 'Untitled Meeting')
    lines = [f'# {title}', '']
    
    # Add summary section if available
    if summary and summary.get('content'):
        lines.extend([
            '## Summary',
            '',
            summary['content'],
            ''
        ])
    
    # Add transcript section
    lines.extend([
        '## Transcript',
        ''
    ])
    
    for segment in transcript_segments:
        speaker = segment.get('speaker', 'Unknown')
        text = segment.get('text', '')
        timestamp = segment.get('start_time')
        
        # Format with optional timestamp
        if timestamp:
            lines.append(f'**[{speaker}]** _{timestamp}_: {text}')
        else:
            lines.append(f'**[{speaker}]:** {text}')
        lines.append('')
    
    return '\n'.join(lines)


def export_meeting_to_markdown(
    meeting: Dict[str, Any],
    transcript_segments: List[Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None
) -> Path:
    """
    Export a complete meeting to a markdown file.
    
    This is the main entry point for the export functionality.
    
    Args:
        meeting: Meeting record dict with keys: id, title, created_at, duration_seconds
        transcript_segments: List of segment dicts with keys: speaker, text, start_time
        summary: Optional summary dict with key: content
        
    Returns:
        Path to the created markdown file
        
    Raises:
        IOError: If file cannot be written
        ValueError: If meeting data is invalid
    """
    if not meeting:
        raise ValueError("Meeting data is required")
    
    # Generate filename
    created_at = meeting.get('created_at', datetime.now())
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    
    timestamp = created_at.strftime('%Y-%m-%dT%H-%M')
    slug = sanitize_filename(meeting.get('title', ''))
    filename = f"{timestamp}_{slug}.md"
    
    # Ensure export directory exists
    export_path = get_export_path()
    export_path.mkdir(parents=True, exist_ok=True)
    
    filepath = export_path / filename
    
    # Generate content
    frontmatter = generate_frontmatter(meeting, transcript_segments)
    body = generate_markdown_body(meeting, transcript_segments, summary)
    content = f"{frontmatter}\n\n{body}"
    
    # Write file
    try:
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"Exported meeting to: {filepath}")
    except IOError as e:
        logger.error(f"Failed to export meeting: {e}")
        raise
    
    return filepath


# Convenience function for integration with existing Meetily code
def export_meeting_by_id(meeting_id: int, db_session) -> Path:
    """
    Export a meeting by its database ID.
    
    This function integrates with Meetily's existing database layer.
    Import and call this from the meeting completion handler.
    
    Args:
        meeting_id: Database ID of the meeting to export
        db_session: SQLAlchemy session or database connection
        
    Returns:
        Path to the created markdown file
    """
    # These imports would come from Meetily's existing code
    # Adjust import paths based on actual Meetily structure
    from .models import Meeting, TranscriptSegment, Summary
    
    meeting = db_session.query(Meeting).get(meeting_id)
    if not meeting:
        raise ValueError(f"Meeting {meeting_id} not found")
    
    segments = db_session.query(TranscriptSegment)\
        .filter_by(meeting_id=meeting_id)\
        .order_by(TranscriptSegment.start_time)\
        .all()
    
    summary = db_session.query(Summary)\
        .filter_by(meeting_id=meeting_id)\
        .order_by(Summary.created_at.desc())\
        .first()
    
    # Convert ORM objects to dicts
    meeting_dict = {
        'id': meeting.id,
        'title': meeting.title,
        'created_at': meeting.created_at,
        'duration_seconds': meeting.duration_seconds
    }
    
    segments_list = [{
        'speaker': s.speaker,
        'text': s.text,
        'start_time': s.start_time
    } for s in segments]
    
    summary_dict = {'content': summary.content} if summary else None
    
    return export_meeting_to_markdown(meeting_dict, segments_list, summary_dict)
```

**Task 2.2: Create integration patch documentation**

Create `meetily-fork/INTEGRATION.md`:

```markdown
# Meetily Integration Guide

## Overview

This document describes how to integrate the markdown export functionality into a Meetily fork.

## Files to Add

### 1. `backend/app/export.py`

Copy the `export.py` file from this directory to your Meetily fork at `backend/app/export.py`.

## Files to Modify

### 2. `backend/app/config.py`

Add the following to your config:

```python
# Markdown Export Configuration
MEETILY_EXPORT_PATH = os.getenv(
    'MEETILY_EXPORT_PATH',
    os.path.expanduser('~/Documents/obsidian-vault/_inbox/meetings')
)
```

### 3. `backend/app/routes/meetings.py` (or equivalent)

In the function that marks a meeting as complete, add the export call:

```python
from app.export import export_meeting_by_id

@router.post("/meetings/{meeting_id}/complete")
async def complete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    # ... existing completion logic ...
    
    # Add export trigger
    try:
        export_path = export_meeting_by_id(meeting_id, db)
        logger.info(f"Meeting exported to: {export_path}")
    except Exception as e:
        logger.error(f"Export failed: {e}")
        # Don't fail the request if export fails
    
    return {"status": "completed", "export_path": str(export_path)}
```

### 4. Environment Configuration

Add to your `.env` or environment:

```bash
MEETILY_EXPORT_PATH=/path/to/your/obsidian-vault/_inbox/meetings
```

## Testing the Integration

1. Start Meetily with the modifications
2. Record a short test meeting
3. Complete the meeting
4. Check the export directory for the markdown file
5. Verify frontmatter and content structure

## Troubleshooting

### Export directory not created
- Ensure the parent directory exists
- Check write permissions

### Meeting not exporting
- Check logs for export errors
- Verify the completion endpoint is being called
- Confirm MEETILY_EXPORT_PATH is set correctly

### Malformed markdown
- Check for special characters in meeting title
- Verify transcript segments have required fields
```

**Task 2.3: Create configuration module**

Create `meetily-fork/backend/app/export_config.py`:

```python
"""
Configuration for the markdown export module.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, validator


class ExportSettings(BaseSettings):
    """Settings for markdown export functionality."""
    
    export_path: Path = Path.home() / "Documents" / "obsidian-vault" / "_inbox" / "meetings"
    export_enabled: bool = True
    include_timestamps: bool = True
    max_title_length: int = 50
    
    class Config:
        env_prefix = "MEETILY_"
    
    @validator('export_path', pre=True)
    def expand_path(cls, v):
        if isinstance(v, str):
            return Path(os.path.expanduser(v))
        return v


# Global settings instance
export_settings = ExportSettings()


def get_export_settings() -> ExportSettings:
    """Get the current export settings."""
    return export_settings
```

---

### Priority 3: Obsidian Vault Scaffold

**Task 3.1: Create vault CLAUDE.md**

Create `obsidian-scaffold/CLAUDE.md` (this is the file referenced in the PRD for the Obsidian vault context):

```markdown
# Knowledge Vault

Personal knowledge management system with automated meeting transcript integration.

## Directory Structure

```
├── _inbox/meetings/     # Raw Meetily exports → process with /ingest-meetings
├── _templates/          # Note templates
├── projects/            # Project folders with PROJECT.md context
│   └── [project-name]/
│       ├── PROJECT.md   # Team, keywords, Notion IDs
│       ├── meetings/    # Processed meeting notes
│       └── shared/      # Google Drive synced (optional)
├── people/              # Person notes with contact info
├── meetings/            # General meetings (unmatched to project)
└── concepts/            # Wiki-linkable concept notes
```

## Commands

| Command | Description |
|---------|-------------|
| `/ingest-meetings` | Process all pending files in `_inbox/meetings/` |
| `/extract-actions` | Extract action items from meeting, create Notion tasks |
| `/send-followups` | Generate follow-up email drafts for participants |

## File Conventions

### Frontmatter (Required)

All notes must include:

```yaml
---
title: "Note Title"
date: YYYY-MM-DDTHH:mm:ss
status: draft | pending_enrichment | processed | reviewed
tags: [tag1, tag2]
---
```

### Meeting Notes (Additional Fields)

```yaml
project: "[[projects/project-slug/index]]"
participants:
  - "[[people/Person Name]]"
duration: 45
themes: [theme1, theme2]
confidence: high | medium | low
processed_at: YYYY-MM-DDTHH:mm:ss
```

## Linking Rules

| Type | Format | Example |
|------|--------|---------|
| People | `[[people/First Last]]` | `[[people/Jane Doe]]` |
| Projects | `[[projects/slug/index]]` | `[[projects/opencivics/index]]` |
| Concepts | `[[concepts/Name]]` | `[[concepts/Governance]]` |

**Rules:**
- Link first occurrence only
- Maximum 10-15 links per document
- Create person stubs if missing

## Tags

Standard tags:
- `#meeting` — all meeting notes
- `#action-item` — contains tasks to extract
- `#draft` — needs review
- `#unprocessed` — raw from Meetily, not yet ingested
- `#shared` — synced to collaborators

## Project Context

Each project folder contains `PROJECT.md` with:
- Team members (name, email, role)
- Notion workspace and database IDs (optional)
- Keywords for auto-matching
- Aliases (alternative project names)

The `/ingest-meetings` command reads these to determine meeting routing.

## Processing Workflow

1. Meetily exports completed meetings to `_inbox/meetings/`
2. User runs `/ingest-meetings` in Claude Code terminal
3. Claude Code:
   - Reads each file with `status: pending_enrichment`
   - Matches to project via PROJECT.md keywords/team
   - Enriches metadata, adds wiki-links
   - Moves to `projects/[name]/meetings/` or `meetings/`
   - Updates status to `processed`
4. Google Drive syncs `shared/` folders to collaborators

## Quality Standards

- Preserve all original transcript content
- Use kebab-case for filenames
- ISO 8601 format for all dates
- UTF-8 encoding
- Max 50 character slugs in filenames
```

**Task 3.2: Create templates**

Create `obsidian-scaffold/_templates/meeting-note.md`:

```markdown
---
title: "{{title}}"
date: {{date}}
duration: {{duration}}
status: pending_enrichment
source: meetily
project: 
participants: []
themes: []
tags:
  - meeting
  - unprocessed
---

# {{title}}

## Summary

{{summary}}

## Action Items

- [ ] 

## Transcript

{{transcript}}

## Notes

<!-- Additional notes added during/after processing -->
```

Create `obsidian-scaffold/_templates/person.md`:

```markdown
---
name: "{{name}}"
email: 
organization: 
role: 
first_seen: {{date}}
tags:
  - person
---

# {{name}}

## Contact

- **Email:** 
- **Organization:** 
- **Role:** 

## Context

First encountered: [[{{source_meeting}}]]

## Notes

<!-- Add notes about this person, relationship, context -->

## Meetings

```dataview
LIST
FROM "projects" OR "meetings"
WHERE contains(participants, this.file.link)
SORT date DESC
```
```

Create `obsidian-scaffold/_templates/PROJECT-template.md`:

```markdown
---
name: "{{project_name}}"
aliases: []
status: active
notion_workspace: 
notion_tasks_database: 
tags:
  - project
---

# {{project_name}}

## Overview

<!-- Brief description of this project -->

## Team

| Name | Email | Role |
|------|-------|------|
| | | Lead |
| | | |

## Keywords

Keywords for auto-matching meeting content to this project:

- 
- 
- 

## Related Projects

- 

## Links

- **Repository:** 
- **Notion:** 
- **Shared Drive:** 

## Recent Meetings

```dataview
TABLE date, duration, themes
FROM "projects/{{project_slug}}/meetings"
SORT date DESC
LIMIT 10
```
```

**Task 3.3: Create example project**

Create `obsidian-scaffold/projects/_example-project/PROJECT.md`:

```markdown
---
name: "Example Project"
aliases:
  - "example"
  - "ex-proj"
status: active
notion_workspace: "your-workspace-id"
notion_tasks_database: "your-database-id"
tags:
  - project
  - example
---

# Example Project

## Overview

This is an example project to demonstrate the structure. Duplicate this folder and customize for your actual projects.

## Team

| Name | Email | Role |
|------|-------|------|
| Your Name | you@example.com | Lead |
| Collaborator | collab@example.com | Member |

## Keywords

Keywords for auto-matching meeting content to this project:

- example
- demo
- sample
- test-project

## Related Projects

- [[projects/another-project/index]]

## Links

- **Repository:** https://github.com/example/project
- **Notion:** https://notion.so/workspace/example
- **Shared Drive:** https://drive.google.com/drive/folders/xxx

## Recent Meetings

```dataview
TABLE date, duration, themes
FROM "projects/_example-project/meetings"
SORT date DESC
LIMIT 10
```
```

Create `obsidian-scaffold/projects/_example-project/index.md`:

```markdown
# Example Project

> This is the index page for Example Project. Link here when referencing this project: `[[projects/_example-project/index]]`

## Quick Links

- [[projects/_example-project/PROJECT|Project Context]]
- [[projects/_example-project/meetings/|Meetings]]

## Overview

<!-- Add project overview, goals, current status -->

## Key Decisions

<!-- Track major decisions made -->

## Resources

<!-- Links to relevant resources -->
```

---

### Priority 4: Setup Scripts

**Task 4.1: Create main setup script**

Create `scripts/setup.sh`:

```bash
#!/bin/bash

# Intelligent Meeting Knowledge System - Setup Script
# This script sets up the complete environment

set -e

echo "========================================"
echo "Intelligent Meeting Knowledge System"
echo "Setup Script"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for required tools
check_dependencies() {
    echo "Checking dependencies..."
    
    local missing=()
    
    command -v git >/dev/null 2>&1 || missing+=("git")
    command -v node >/dev/null 2>&1 || missing+=("node")
    command -v python3 >/dev/null 2>&1 || missing+=("python3")
    command -v cargo >/dev/null 2>&1 || missing+=("rust/cargo")
    
    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}Missing required tools: ${missing[*]}${NC}"
        echo "Please install these before continuing."
        exit 1
    fi
    
    echo -e "${GREEN}All dependencies found.${NC}"
}

# Get configuration from user
get_config() {
    echo ""
    echo "Configuration"
    echo "-------------"
    
    # Obsidian vault path
    read -p "Obsidian vault path [~/Documents/obsidian-vault]: " VAULT_PATH
    VAULT_PATH=${VAULT_PATH:-~/Documents/obsidian-vault}
    VAULT_PATH=$(eval echo "$VAULT_PATH")  # Expand ~
    
    # Ollama model
    read -p "Ollama model for summarization [llama3.2]: " OLLAMA_MODEL
    OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.2}
    
    echo ""
    echo "Configuration:"
    echo "  Vault path: $VAULT_PATH"
    echo "  Ollama model: $OLLAMA_MODEL"
    echo ""
    read -p "Continue with this configuration? [Y/n]: " CONFIRM
    CONFIRM=${CONFIRM:-Y}
    
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
}

# Initialize Obsidian vault
init_vault() {
    echo ""
    echo "Initializing Obsidian vault..."
    
    if [ -d "$VAULT_PATH" ]; then
        echo -e "${YELLOW}Vault directory exists. Merging scaffold...${NC}"
    else
        echo "Creating vault directory..."
        mkdir -p "$VAULT_PATH"
    fi
    
    # Copy scaffold
    cp -rn obsidian-scaffold/* "$VAULT_PATH/" 2>/dev/null || true
    cp -rn obsidian-scaffold/.claude "$VAULT_PATH/" 2>/dev/null || true
    
    # Ensure directories exist
    mkdir -p "$VAULT_PATH/_inbox/meetings"
    mkdir -p "$VAULT_PATH/_templates"
    mkdir -p "$VAULT_PATH/_drafts/followups"
    mkdir -p "$VAULT_PATH/projects"
    mkdir -p "$VAULT_PATH/people"
    mkdir -p "$VAULT_PATH/meetings"
    mkdir -p "$VAULT_PATH/concepts"
    
    echo -e "${GREEN}Vault initialized at: $VAULT_PATH${NC}"
}

# Setup Ollama
setup_ollama() {
    echo ""
    echo "Setting up Ollama..."
    
    if ! command -v ollama >/dev/null 2>&1; then
        echo -e "${YELLOW}Ollama not found. Please install from: https://ollama.ai${NC}"
        echo "After installing, run: ollama pull $OLLAMA_MODEL"
        return
    fi
    
    echo "Pulling model: $OLLAMA_MODEL"
    ollama pull "$OLLAMA_MODEL"
    
    echo -e "${GREEN}Ollama configured with model: $OLLAMA_MODEL${NC}"
}

# Create environment file
create_env() {
    echo ""
    echo "Creating environment configuration..."
    
    cat > .env << EOF
# Intelligent Meeting Knowledge System Configuration
# Generated by setup.sh

# Obsidian vault path
VAULT_PATH=$VAULT_PATH

# Meetily export path (inbox directory)
MEETILY_EXPORT_PATH=$VAULT_PATH/_inbox/meetings

# Ollama model for summarization
OLLAMA_MODEL=$OLLAMA_MODEL
EOF

    echo -e "${GREEN}Environment file created: .env${NC}"
}

# Print next steps
print_next_steps() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}Setup Complete!${NC}"
    echo "========================================"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Install Meetily:"
    echo "   - Download from: https://github.com/Zackriya-Solutions/meeting-minutes/releases"
    echo "   - Or build from source with our modifications (see meetily-fork/INTEGRATION.md)"
    echo ""
    echo "2. Configure Meetily export path:"
    echo "   - Set MEETILY_EXPORT_PATH=$VAULT_PATH/_inbox/meetings"
    echo ""
    echo "3. Open Obsidian and select vault:"
    echo "   - Open folder: $VAULT_PATH"
    echo ""
    echo "4. Install recommended Obsidian plugins:"
    echo "   - Templater"
    echo "   - Dataview"
    echo "   - Terminal (for Claude Code)"
    echo ""
    echo "5. Create your first project:"
    echo "   - Copy projects/_example-project to projects/your-project"
    echo "   - Edit PROJECT.md with your team and keywords"
    echo ""
    echo "6. Test the pipeline:"
    echo "   - Record a test meeting in Meetily"
    echo "   - Run: /ingest-meetings in Claude Code"
    echo ""
    echo "For detailed instructions, see: docs/SETUP.md"
}

# Main execution
main() {
    check_dependencies
    get_config
    init_vault
    setup_ollama
    create_env
    print_next_steps
}

main "$@"
```

**Task 4.2: Create vault initialization script**

Create `scripts/init-vault.sh`:

```bash
#!/bin/bash

# Initialize or update an Obsidian vault with the knowledge system scaffold

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SCAFFOLD_DIR="$PROJECT_ROOT/obsidian-scaffold"

# Default vault path
VAULT_PATH="${1:-$HOME/Documents/obsidian-vault}"

echo "Initializing vault at: $VAULT_PATH"

# Create base directories
mkdir -p "$VAULT_PATH/_inbox/meetings"
mkdir -p "$VAULT_PATH/_templates"
mkdir -p "$VAULT_PATH/_drafts/followups"
mkdir -p "$VAULT_PATH/projects"
mkdir -p "$VAULT_PATH/people"
mkdir -p "$VAULT_PATH/meetings"
mkdir -p "$VAULT_PATH/concepts"

# Copy scaffold files (don't overwrite existing)
echo "Copying scaffold files..."

# Copy .claude directory
if [ -d "$SCAFFOLD_DIR/.claude" ]; then
    cp -rn "$SCAFFOLD_DIR/.claude" "$VAULT_PATH/" 2>/dev/null || true
fi

# Copy CLAUDE.md
if [ -f "$SCAFFOLD_DIR/CLAUDE.md" ] && [ ! -f "$VAULT_PATH/CLAUDE.md" ]; then
    cp "$SCAFFOLD_DIR/CLAUDE.md" "$VAULT_PATH/"
fi

# Copy templates
if [ -d "$SCAFFOLD_DIR/_templates" ]; then
    cp -rn "$SCAFFOLD_DIR/_templates/"* "$VAULT_PATH/_templates/" 2>/dev/null || true
fi

# Copy example project
if [ -d "$SCAFFOLD_DIR/projects/_example-project" ] && [ ! -d "$VAULT_PATH/projects/_example-project" ]; then
    cp -r "$SCAFFOLD_DIR/projects/_example-project" "$VAULT_PATH/projects/"
fi

# Create .gitkeep files
touch "$VAULT_PATH/_inbox/meetings/.gitkeep"
touch "$VAULT_PATH/_drafts/followups/.gitkeep"
touch "$VAULT_PATH/people/.gitkeep"
touch "$VAULT_PATH/meetings/.gitkeep"
touch "$VAULT_PATH/concepts/.gitkeep"

echo "Vault initialized successfully!"
echo ""
echo "Structure:"
find "$VAULT_PATH" -type d -maxdepth 3 | head -20

echo ""
echo "Next: Create your first project in $VAULT_PATH/projects/"
```

---

### Priority 5: Documentation

**Task 5.1: Create README.md**

Create `README.md` at project root:

```markdown
# Intelligent Meeting Knowledge System

A local-first, privacy-preserving pipeline that captures meeting audio, transcribes it locally, generates AI summaries, and intelligently organizes outputs into an Obsidian knowledge base.

## Features

- 🎙️ **Local transcription** — Whisper/Parakeet processes audio on your machine
- 🤖 **AI summarization** — Ollama generates summaries without cloud APIs
- 🧠 **Intelligent routing** — Claude Code matches meetings to projects
- 📝 **Rich metadata** — Automatic tagging, wiki-linking, participant detection
- 🔗 **Knowledge integration** — Seamless Obsidian vault organization
- 👥 **Collaboration** — Selective Google Drive sync for team projects

## Components

| Component | Purpose |
|-----------|---------|
| [Meetily](https://github.com/Zackriya-Solutions/meeting-minutes) | Audio capture and transcription |
| [Ollama](https://ollama.ai) | Local LLM summarization |
| [Claude Code](https://docs.anthropic.com/claude-code) | Intelligent processing and routing |
| [Obsidian](https://obsidian.md) | Knowledge base and note management |

## Quick Start

```bash
# Clone this repository
git clone https://github.com/your-org/meeting-knowledge-system
cd meeting-knowledge-system

# Run setup
chmod +x scripts/setup.sh
./scripts/setup.sh
```

## Documentation

- [Complete PRD](docs/intelligent-meeting-knowledge-system-prd.md)
- [Setup Guide](docs/SETUP.md)
- [Configuration Reference](docs/CONFIGURATION.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## How It Works

```
Meeting → Meetily → Markdown Export → Claude Code → Obsidian Vault
                                           ↓
                                    Project Matching
                                    Metadata Enrichment
                                    Wiki-Linking
                                    Intelligent Filing
```

1. **Record** — Start a meeting in Meetily
2. **Transcribe** — Audio is processed locally with Whisper/Parakeet
3. **Summarize** — Ollama generates a structured summary
4. **Export** — Meeting is saved as markdown to inbox
5. **Process** — Run `/ingest-meetings` in Claude Code
6. **Organize** — Meeting is enriched and filed to the correct project

## Project Structure

```
├── docs/                    # Documentation
├── meetily-fork/            # Meetily modifications for markdown export
├── obsidian-scaffold/       # Template vault structure
│   ├── .claude/             # Claude Code commands and skills
│   ├── _templates/          # Note templates
│   └── projects/            # Example project structure
└── scripts/                 # Setup and utility scripts
```

## Requirements

- macOS 12+ or Windows 10+
- 16GB RAM (32GB recommended)
- [Ollama](https://ollama.ai)
- [Obsidian](https://obsidian.md)
- [Claude Code CLI](https://docs.anthropic.com/claude-code)

## License

MIT

## Acknowledgments

- [Meetily](https://github.com/Zackriya-Solutions/meeting-minutes) by Zackriya Solutions
- [Obsidian](https://obsidian.md)
- [Ollama](https://ollama.ai)
```

**Task 5.2: Create detailed setup guide**

Create `docs/SETUP.md`:

```markdown
# Setup Guide

Complete installation and configuration instructions.

## Prerequisites

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 16 GB | 32 GB |
| Storage | 50 GB SSD | 100+ GB SSD |
| CPU | 4 cores | 8+ cores |
| GPU | Integrated | Apple Silicon M1+ or NVIDIA CUDA |

### Software

Install the following before proceeding:

1. **Git** — https://git-scm.com
2. **Node.js 18+** — https://nodejs.org
3. **Rust** — https://rustup.rs
4. **Python 3.10+** — https://python.org
5. **Ollama** — https://ollama.ai
6. **Obsidian** — https://obsidian.md
7. **Claude Code** — `npm install -g @anthropic-ai/claude-code`

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/meeting-knowledge-system
cd meeting-knowledge-system
```

### Step 2: Run Setup Script

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The script will:
- Check dependencies
- Prompt for configuration
- Initialize your Obsidian vault
- Configure Ollama
- Create environment files

### Step 3: Install Meetily

**Option A: Use official release**

Download from: https://github.com/Zackriya-Solutions/meeting-minutes/releases

Then manually configure export (see Configuration section).

**Option B: Build fork with export support**

```bash
# Clone Meetily
git clone https://github.com/Zackriya-Solutions/meeting-minutes meetily
cd meetily

# Apply our modifications
cp ../meetily-fork/backend/app/export.py backend/app/
# Follow instructions in meetily-fork/INTEGRATION.md

# Build
npm install
cargo build --release
```

### Step 4: Configure Obsidian

1. Open Obsidian
2. Select "Open folder as vault"
3. Choose your vault path (default: `~/Documents/obsidian-vault`)
4. Install community plugins:
   - Settings → Community plugins → Enable
   - Browse and install:
     - Templater
     - Dataview
     - Terminal

### Step 5: Configure Claude Code

```bash
# Authenticate
claude auth

# Verify access
claude --version
```

### Step 6: Create Your First Project

```bash
cd ~/Documents/obsidian-vault/projects
cp -r _example-project my-project
```

Edit `my-project/PROJECT.md`:
- Add team members
- Add keywords for matching
- Configure Notion IDs (optional)

## Configuration

### Environment Variables

Create or edit `.env`:

```bash
# Vault location
VAULT_PATH=~/Documents/obsidian-vault

# Meetily export destination
MEETILY_EXPORT_PATH=~/Documents/obsidian-vault/_inbox/meetings

# Ollama model
OLLAMA_MODEL=llama3.2
```

### Meetily Configuration

If using official Meetily without fork:

1. Open Meetily settings
2. Set export path to: `~/Documents/obsidian-vault/_inbox/meetings`
3. Enable "Export on completion"
4. Set format to "Markdown"

### Google Drive Sync (Optional)

For collaboration:

1. Install Google Drive desktop app
2. In Drive settings, enable "Stream files"
3. Right-click on `projects/your-project/shared/` folder
4. Select "Add shortcut to Drive"
5. Share the Drive folder with collaborators

## Verification

### Test Transcription

1. Open Meetily
2. Start a test recording
3. Speak for 30 seconds
4. Stop recording
5. Verify file appears in `_inbox/meetings/`

### Test Processing

1. Open terminal in Obsidian (Terminal plugin)
2. Or open terminal and navigate to vault
3. Run: `/ingest-meetings`
4. Verify meeting was processed and moved

### Test Project Matching

1. Create a meeting mentioning your project keywords
2. Process with `/ingest-meetings`
3. Verify it was filed to correct project folder

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.
```

---

## Success Criteria

Your implementation is complete when:

1. [ ] Project `CLAUDE.md` exists and accurately documents the repository
2. [ ] Directory structure matches specification
3. [ ] `meetily-fork/backend/app/export.py` is complete and documented
4. [ ] `meetily-fork/INTEGRATION.md` provides clear fork instructions
5. [ ] `obsidian-scaffold/` contains complete vault template
6. [ ] All templates are functional with correct frontmatter
7. [ ] `scripts/setup.sh` runs without errors
8. [ ] `README.md` provides clear project overview
9. [ ] `docs/SETUP.md` enables complete installation
10. [ ] Example project demonstrates correct structure

## Testing Checklist

Before considering complete:

- [ ] Fresh `setup.sh` execution on clean system
- [ ] Vault initialization creates all directories
- [ ] Templates render correctly in Obsidian
- [ ] `.claude/commands/` are recognized by Claude Code
- [ ] Export module passes Python linting
- [ ] Documentation links are valid

---

## Notes for the AI Agent

1. **Do not modify `.claude/` contents** — These are provided and tested
2. **Focus on infrastructure** — Build what the Claude Code commands will operate on
3. **Test incrementally** — Verify each component before moving to next
4. **Document decisions** — Add comments explaining non-obvious choices
5. **Follow the PRD** — When in doubt, reference the PRD for specifications
6. **Ask for clarification** — If requirements conflict, ask before assuming

The goal is a complete, working system that a user can clone and run with minimal manual intervention. The Claude Code commands will handle the intelligent processing; your job is to build the scaffolding they operate within.