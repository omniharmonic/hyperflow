# Intelligent Meeting Knowledge System
## Product Requirements Document

**Version:** 1.0  
**Date:** January 2026  
**Author:** Benjamin / OpenCivics  
**Status:** Draft

---

## Executive Summary

This document specifies a local-first, privacy-preserving personal knowledge management system that automatically captures meeting audio, transcribes it locally, generates AI summaries, and intelligently organizes the output into an Obsidian knowledge base with full collaboration capabilities.

The system combines three primary components:
- **Meetily** — Open-source meeting transcription with local AI processing
- **Claude Code** — Agentic AI for transcript enrichment and intelligent routing
- **Obsidian** — Markdown-based knowledge management with Google Drive sync

**Core Value Proposition:** Transform every meeting into searchable, linked, collaborative knowledge without sending a single byte to the cloud.

---

## Problem Statement

Knowledge workers face a persistent challenge: meetings generate valuable information that rapidly decays. Current solutions force a choice between:

1. **Cloud-based tools** (Granola, Otter.ai) — Good UX but privacy concerns, subscription costs, vendor lock-in
2. **Manual note-taking** — Private but inconsistent, time-consuming, poorly organized
3. **Local transcription** — Private but outputs sit in isolation, no enrichment or routing

**Target User:** Technical knowledge workers, researchers, consultants, and collaborative teams who:
- Value data sovereignty and privacy
- Work across multiple projects with different collaborators
- Need meeting content integrated into their existing workflows
- Want AI assistance without cloud dependency

---

## Solution Overview

### Vision Statement

> Meetings auto-transcribe locally → AI enriches with context and metadata → Files are intelligently routed to the correct project folder → Shared with collaborators via selective sync. All processing happens on your machine.

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER'S MACHINE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Meetily    │───▶│   _inbox/    │───▶│    Claude Code       │  │
│  │              │    │  meetings/   │    │                      │  │
│  │ • Whisper    │    │              │    │ • Project matching   │  │
│  │ • Parakeet   │    │  Raw .md     │    │ • Metadata enrichment│  │
│  │ • Ollama     │    │  exports     │    │ • Wiki-linking       │  │
│  └──────────────┘    └──────────────┘    │ • Intelligent routing│  │
│                                          └──────────┬─────────────┘  │
│                                                     │               │
│                                                     ▼               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    OBSIDIAN VAULT                           │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │  projects/                                                  │   │
│  │  ├── opencivics/                                           │   │
│  │  │   ├── PROJECT.md          ◄── Context for matching      │   │
│  │  │   ├── meetings/           ◄── Processed notes go here   │   │
│  │  │   └── shared/             ◄── Google Drive synced       │   │
│  │  ├── localism-fund/                                        │   │
│  │  └── [other-projects]/                                     │   │
│  │  people/                     ◄── Person stubs with links    │   │
│  │  meetings/                   ◄── Fallback for unmatched     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼ (selective sync)
                    ┌─────────────────────┐
                    │    Google Drive     │
                    │  shared/ folders    │
                    │                     │
                    │  Collaborators      │
                    │  mount as vault     │
                    │  subfolder          │
                    └─────────────────────┘
```

---

## Component Specifications

### Component 1: Meetily

**Repository:** [github.com/Zackriya-Solutions/meeting-minutes](https://github.com/Zackriya-Solutions/meeting-minutes)  
**License:** MIT  
**Version:** 0.1.1 (current as of January 2026)  
**Stars:** 8,200+

#### Technical Architecture

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Next.js + Tauri v2 | Cross-platform desktop UI |
| Audio Processing | Rust | System audio capture, speaker diarization |
| Transcription | Whisper.cpp / NVIDIA Parakeet | Local speech-to-text |
| Summarization | Ollama (llama3.2, mistral, etc.) | Local LLM processing |
| Storage | SQLite | Meeting data persistence |

#### Database Schema

**Location:** `~/.meetily/meeting_minutes.db` (configurable)

```sql
-- Core tables
meetings (id, title, created_at, updated_at, duration_seconds, status)
transcript_segments (id, meeting_id, speaker, text, start_time, end_time)
summaries (id, meeting_id, model_used, content, created_at)
settings (key, value)
```

#### Required Fork Modifications

To enable automatic markdown export, the following modifications are needed:

**New file: `backend/app/export.py`**

```python
"""Markdown export functionality for Meetily"""

import os
import re
from datetime import datetime
from pathlib import Path
from .db import get_meeting, get_transcript, get_summary
from .config import get_export_path

def sanitize_filename(title: str) -> str:
    """Convert title to kebab-case filename slug."""
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower())
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug[:50]  # Max 50 chars

def export_meeting_to_markdown(meeting_id: int) -> Path:
    """Export a meeting to markdown with YAML frontmatter."""
    meeting = get_meeting(meeting_id)
    transcript = get_transcript(meeting_id)
    summary = get_summary(meeting_id)
    
    timestamp = meeting['created_at'].strftime('%Y-%m-%dT%H-%M')
    slug = sanitize_filename(meeting['title'])
    filename = f"{timestamp}_{slug}.md"
    
    export_path = Path(get_export_path())
    export_path.mkdir(parents=True, exist_ok=True)
    filepath = export_path / filename
    
    content = generate_markdown(meeting, transcript, summary)
    filepath.write_text(content, encoding='utf-8')
    
    return filepath

def generate_markdown(meeting, transcript, summary) -> str:
    """Generate markdown content with frontmatter."""
    frontmatter = f"""---
title: "{meeting['title']}"
date: {meeting['created_at'].isoformat()}
duration: {meeting['duration_seconds'] // 60}
status: pending_enrichment
source: meetily
tags:
  - meeting
---

"""
    
    body = f"# {meeting['title']}\n\n"
    
    if summary:
        body += "## Summary\n\n"
        body += summary['content'] + "\n\n"
    
    body += "## Transcript\n\n"
    for segment in transcript:
        speaker = segment['speaker'] or 'Unknown'
        body += f"**[{speaker}]:** {segment['text']}\n\n"
    
    return frontmatter + body
```

**Configuration addition: `backend/app/config.py`**

```python
# Add to existing config
EXPORT_PATH = os.getenv(
    'MEETILY_EXPORT_PATH', 
    os.path.expanduser('~/Documents/obsidian-vault/_inbox/meetings')
)

def get_export_path() -> str:
    return EXPORT_PATH
```

**Hook into meeting completion: `backend/app/db.py`**

```python
# In the function that marks meeting as complete:
def complete_meeting(meeting_id: int):
    # ... existing completion logic ...
    
    # Add export trigger
    from .export import export_meeting_to_markdown
    export_meeting_to_markdown(meeting_id)
```

---

### Component 2: Claude Code

Claude Code serves as the intelligent orchestration layer, processing raw meeting exports and integrating them into the knowledge base.

#### Integration Architecture

**Recommended Approach:** Direct filesystem access with vault context

```
obsidian-vault/
├── .claude/
│   ├── commands/
│   │   ├── ingest-meetings.md      # Primary processing command
│   │   ├── extract-actions.md      # Action item extraction
│   │   └── send-followups.md       # Email draft generation
│   └── skills/
│       └── meeting-processor/
│           └── SKILL.md            # Auto-invoked processing rules
├── CLAUDE.md                       # Vault context and conventions
└── [vault contents...]
```

#### CLAUDE.md (Vault Context)

```markdown
# Knowledge Vault

Personal knowledge management system with automated meeting integration.

## Directory Structure

```
├── _inbox/meetings/     # Raw Meetily exports → process with /ingest-meetings
├── _templates/          # Note templates
├── projects/            # Project folders with PROJECT.md context
│   └── [project-name]/
│       ├── PROJECT.md   # Team, keywords, Notion IDs
│       ├── meetings/    # Processed notes
│       └── shared/      # Google Drive synced
├── people/              # Person notes
├── meetings/            # General (unmatched) meetings
└── concepts/            # Wiki-linkable concepts
```

## Commands

| Command | Description |
|---------|-------------|
| `/ingest-meetings` | Process pending files in _inbox/meetings/ |
| `/extract-actions` | Extract action items, create Notion tasks |
| `/send-followups` | Generate follow-up email drafts |

## Linking Conventions

- People: `[[people/First Last]]`
- Projects: `[[projects/project-slug/index]]`
- Concepts: `[[concepts/Concept Name]]`
- First occurrence only, max ~10-15 links per document

## Project Matching

Each project has PROJECT.md with:
- Team members (for participant matching)
- Keywords (for content matching)
- Aliases (alternative project names)
- Notion database IDs (for task creation)

Match meetings to projects by scoring signals, route to project folder if confident.
```

#### /ingest-meetings Command

**File:** `.claude/commands/ingest-meetings.md`

```markdown
---
name: ingest-meetings
description: Process pending meeting transcripts from inbox, enrich with metadata, and route to appropriate project folders
---

# Ingest Meetings

Process all pending meeting files in `_inbox/meetings/` directory.

## Workflow

1. **Scan inbox**
   - Find all `.md` files in `_inbox/meetings/`
   - Filter for files with `status: pending_enrichment` in frontmatter

2. **Load project context**
   - Read all `PROJECT.md` files from `projects/*/PROJECT.md`
   - Build index of: project names, aliases, team members, keywords

3. **For each pending file:**

   a. **Parse content**
      - Extract frontmatter metadata
      - Parse transcript for speaker names
      - Identify key topics from summary

   b. **Match to project**
      - Score each project using signal weights:
        - Explicit project name in content: 5 points
        - Project alias mentioned: 4 points  
        - Team member speaking/mentioned: 3 points
        - Project keyword found: 2 points
        - Related concept: 1 point
      - Strong match (≥8 points): assign with confidence
      - Moderate match (4-7): assign, add uncertainty note
      - Weak match (<4): route to general `meetings/` folder

   c. **Enrich metadata**
      - Add `project` field linking to matched project
      - Convert participant names to wiki-links: `[[people/Name]]`
      - Add theme tags based on content analysis
      - Create person stubs in `people/` if missing

   d. **Add wiki-links**
      - Scan for known concepts, projects, people
      - Link first occurrence only
      - Maximum 10-15 links per document

   e. **Move file**
      - Strong/moderate match: `projects/[name]/meetings/YYYY-MM-DD-slug.md`
      - Weak/no match: `meetings/YYYY-MM-DD-slug.md`

   f. **Update status**
      - Change frontmatter `status: pending_enrichment` → `status: processed`
      - Add `processed_at` timestamp

4. **Report results**
   - List processed files and destinations
   - Note any errors or warnings
   - Show confidence levels for project assignments

## Error Handling

- Malformed frontmatter: Add minimal required fields, continue
- Missing directories: Create as needed
- Parse failures: Log error, skip file, preserve in inbox
```

#### /extract-actions Command

**File:** `.claude/commands/extract-actions.md`

```markdown
---
name: extract-actions
description: Extract action items from meeting notes and optionally create Notion tasks
---

# Extract Action Items

Scan meeting transcript for commitments and tasks, create structured action items.

## Detection Patterns

Look for phrases indicating action items:
- "[Name] will [verb]..."
- "[Name] to [verb]..."
- "Action item: ..."
- "TODO: ..."
- "Next step: ..."
- "By [date], [name] should..."

## Extraction Format

For each action item, extract:
- `task`: The action to be taken
- `assignee`: Person responsible (as wiki-link)
- `deadline`: Due date if mentioned (ISO format)
- `context`: Surrounding context from transcript
- `confidence`: high | medium | low

## Output

Add action items section to meeting note:

```markdown
## Action Items

- [ ] **[Assignee]**: [Task description] *(due: [date])*
  - Context: [relevant transcript excerpt]
```

## Notion Integration (if PROJECT.md has Notion IDs)

For high-confidence items:
1. Read `notion_tasks_database` from PROJECT.md
2. Create task via Notion MCP with:
   - Title: task description
   - Assignee: matched Notion user (if available)
   - Due date: extracted deadline
   - Tags: project name, meeting date
3. Add Notion link to action item in meeting note

## Confidence Levels

- **High**: Clear assignee + explicit deadline + action verb
- **Medium**: Assignee + action but no deadline, or implicit commitment
- **Low**: Vague reference to future work, unclear ownership
```

#### /send-followups Command

**File:** `.claude/commands/send-followups.md`

```markdown
---
name: send-followups
description: Generate personalized follow-up emails for meeting participants
---

# Send Follow-ups

Generate draft follow-up emails for each meeting participant.

## Workflow

1. **Identify participants**
   - Read from meeting frontmatter `participants` field
   - Look up contact info from `people/[Name].md` or PROJECT.md team list

2. **For each participant:**
   - Extract their specific action items
   - Note key discussion points they were involved in
   - Generate personalized email draft

3. **Email template**
   ```
   Subject: Follow-up: [Meeting Title] - [Date]

   Hi [First Name],

   Thanks for joining [meeting title] today. Here's a quick summary of what we discussed and your specific action items.

   **Key Takeaways:**
   [2-3 bullet points of main decisions/outcomes]

   **Your Action Items:**
   [List of their specific commitments with deadlines]

   **Next Steps:**
   [Any scheduled follow-ups or dependencies]

   Let me know if I missed anything or if you have questions.

   Best,
   [Your name]
   ```

4. **Save drafts**
   - Create folder: `_drafts/followups/[YYYY-MM-DD]/`
   - Save each email as: `[participant-name].md`

## Output

Report:
- Number of drafts generated
- Participants without contact info (skipped)
- Path to drafts folder
```

#### Meeting Processor Skill

**File:** `.claude/skills/meeting-processor/SKILL.md`

```markdown
---
name: meeting-processor
description: Rules and context for processing meeting transcripts
---

# Meeting Processor Skill

Auto-invoked when working with meeting files or `_inbox/meetings/` directory.

## Content Preservation Rules

- **Never delete original transcript text**
- Additions go in new sections or frontmatter only
- Preserve speaker attributions exactly
- Keep timestamps intact

## Wiki-Linking Standards

| Link Type | Format | Example |
|-----------|--------|---------|
| People | `[[people/First Last]]` | `[[people/Benjamin Life]]` |
| Projects | `[[projects/slug/index]]` | `[[projects/opencivics/index]]` |
| Concepts | `[[concepts/Name]]` | `[[concepts/Attestation]]` |

- Link first occurrence only
- Maximum 10-15 links per document
- Don't link common words

## Project Matching Algorithm

**Signal Weights:**

| Signal | Weight |
|--------|--------|
| Explicit project name | 5 |
| Project alias | 4 |
| Team member name | 3 |
| Project keyword | 2 |
| Related concept | 1 |

**Thresholds:**
- ≥8 points: Strong match, assign confidently
- 4-7 points: Moderate match, assign with note
- <4 points: Weak match, use general `meetings/` folder

## File Naming Convention

Format: `YYYY-MM-DD-descriptive-slug.md`

- Use kebab-case
- Max 50 characters for slug
- Example: `2026-01-07-quarterly-planning-sync.md`

## Frontmatter Schema

```yaml
---
title: "Meeting Title"
date: 2026-01-07T14:30:00
duration: 45
status: pending_enrichment | processed | reviewed
source: meetily
project: "[[projects/project-slug/index]]"
participants:
  - "[[people/Person One]]"
  - "[[people/Person Two]]"
themes:
  - theme-one
  - theme-two
tags:
  - meeting
  - project-slug
processed_at: 2026-01-07T15:00:00
confidence: high | medium | low
---
```
```

---

### Component 3: Obsidian Configuration

#### Directory Structure

```
obsidian-vault/
├── .obsidian/                    # Obsidian config (git-ignored)
├── .claude/                      # Claude Code config
│   ├── commands/
│   └── skills/
├── CLAUDE.md                     # Vault context
├── _inbox/
│   └── meetings/                 # Meetily export destination
├── _templates/
│   ├── meeting-note.md
│   ├── person.md
│   └── project.md
├── _drafts/
│   └── followups/                # Generated email drafts
├── projects/
│   ├── opencivics/
│   │   ├── PROJECT.md
│   │   ├── index.md
│   │   ├── meetings/
│   │   └── shared/               # Google Drive synced
│   ├── localism-fund/
│   └── [other-projects]/
├── people/
│   └── [person-name].md
├── meetings/                     # General/unmatched meetings
└── concepts/                     # Wiki-linkable concepts
```

#### PROJECT.md Template

```markdown
---
name: "Project Name"
aliases:
  - "project-shortname"
  - "proj"
status: active
notion_workspace: "workspace-id"
notion_tasks_database: "database-id"
---

# Project Name

## Team

| Name | Email | Role |
|------|-------|------|
| Benjamin Life | ben@example.com | Lead |
| Jane Doe | jane@example.com | Collaborator |

## Keywords

Keywords for auto-matching meeting content:

- keyword-one
- keyword-two
- specific-term

## Related Projects

- [[projects/related-project/index]]

## Links

- [Notion Workspace](https://notion.so/...)
- [GitHub Repo](https://github.com/...)
- [Shared Drive](https://drive.google.com/...)
```

#### Required Obsidian Plugins

**Essential:**

| Plugin | Purpose |
|--------|---------|
| Templater | Note templates with dynamic fields |
| Dataview | Query and display meeting data |
| Terminal | Embedded terminal for Claude Code |

**Recommended:**

| Plugin | Purpose |
|--------|---------|
| Calendar | Date-based meeting navigation |
| Tag Wrangler | Bulk tag management |
| Natural Language Dates | Date parsing in notes |

---

### Component 4: Google Drive Sync

#### Sync Architecture

```
Local Vault                          Google Drive
────────────                         ────────────
projects/
├── opencivics/
│   └── shared/  ◄──── sync ────►   OpenCivics Shared/
├── localism-fund/
│   └── shared/  ◄──── sync ────►   Localism Fund Shared/
```

#### Collaborator Setup

1. **Your setup:**
   - Install Google Drive desktop app
   - Configure selective sync for `shared/` folders
   - Share Drive folders with collaborators

2. **Collaborator setup:**
   - Mount shared Drive folder
   - Add as vault subfolder: `external/[project-name]/`
   - OR use as standalone vault

#### Sync Best Practices

- Avoid simultaneous editing (last-write-wins)
- Use `.gitignore`-style exclusions for local-only files
- Sync only `shared/` folders, not entire vault
- Consider Git backup for version history

---

## Data Flow Pipeline

### Complete Processing Flow

| Step | Component | Action | Output |
|------|-----------|--------|--------|
| 1 | User | Starts meeting, clicks record in Meetily | Recording active |
| 2 | Meetily | Captures system audio | Audio stream |
| 3 | Meetily | Real-time transcription (Whisper/Parakeet) | Transcript segments |
| 4 | Meetily | User ends meeting | Complete transcript |
| 5 | Meetily | Ollama generates summary | Summary + transcript |
| 6 | Meetily (fork) | Export to markdown | `_inbox/meetings/*.md` |
| 7 | User | Runs `/ingest-meetings` in terminal | Command triggered |
| 8 | Claude Code | Reads inbox files | File contents |
| 9 | Claude Code | Loads PROJECT.md contexts | Project index |
| 10 | Claude Code | Matches meeting → project | Project assignment |
| 11 | Claude Code | Enriches metadata | Tags, links, participants |
| 12 | Claude Code | Adds wiki-links | Linked content |
| 13 | Claude Code | Moves to target folder | Organized file |
| 14 | Google Drive | Syncs shared/ folder | Collaborator access |

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Objective:** Working transcription with manual export

**Tasks:**
- [ ] Install Meetily from official release
- [ ] Configure Ollama with summarization model (llama3.2 or mistral)
- [ ] Test transcription quality on real meetings
- [ ] Set up Obsidian vault with directory structure
- [ ] Create initial PROJECT.md files for active projects
- [ ] Install Claude Code CLI and authenticate

**Deliverable:** Can transcribe meetings and manually copy to Obsidian

### Phase 2: Export Integration (Weeks 3-4)

**Objective:** Automatic markdown export from Meetily

**Tasks:**
- [ ] Fork Meetily repository
- [ ] Implement `export.py` module
- [ ] Add export path configuration
- [ ] Hook export into meeting completion flow
- [ ] Test end-to-end export pipeline
- [ ] Configure export path to vault inbox

**Deliverable:** Completed meetings automatically appear in `_inbox/meetings/`

### Phase 3: Claude Code Integration (Weeks 5-6)

**Objective:** Intelligent processing and routing

**Tasks:**
- [ ] Create CLAUDE.md with vault context
- [ ] Implement `/ingest-meetings` command
- [ ] Create `meeting-processor` skill
- [ ] Test project matching with real meetings
- [ ] Refine wiki-linking heuristics
- [ ] Add person stub generation

**Deliverable:** `/ingest-meetings` processes and routes meetings correctly

### Phase 4: Collaboration (Weeks 7-8)

**Objective:** Shared project knowledge bases

**Tasks:**
- [ ] Configure Google Drive sync for shared/ folders
- [ ] Set up folder permissions
- [ ] Test multi-user sync scenarios
- [ ] Document collaborator onboarding process
- [ ] Create collaboration guidelines

**Deliverable:** Collaborators can access shared meeting notes

### Phase 5: Stretch Features (Ongoing)

**Objective:** Enhanced automation and integration

**Tasks:**
- [ ] Implement `/extract-actions` command
- [ ] Add Notion MCP integration for task creation
- [ ] Implement `/send-followups` command
- [ ] Explore automated `/ingest-meetings` triggering
- [ ] Calendar integration for meeting metadata

---

## Technical Requirements

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 16 GB | 32 GB |
| Storage | 50 GB SSD | 100+ GB SSD |
| CPU | 4 cores | 8+ cores |
| GPU | Integrated | Apple Silicon M1+ or NVIDIA CUDA |

**Notes:**
- GPU significantly accelerates transcription (4x with Parakeet on NVIDIA)
- Apple Silicon M-series chips provide excellent local LLM performance
- SSD required for responsive transcription

### Software Dependencies

| Software | Version | Purpose |
|----------|---------|---------|
| macOS | 12+ | Primary platform |
| Windows | 10+ | Alternative platform |
| Node.js | 18+ | Meetily build |
| Rust | Latest stable | Meetily build |
| Python | 3.10+ | Meetily backend |
| Ollama | Latest | Local LLM |
| Claude Code | Latest CLI | AI orchestration |
| Obsidian | 1.4+ | Knowledge base |
| Google Drive | Desktop app | Sync |

### API Keys and Accounts

| Service | Requirement | Purpose |
|---------|-------------|---------|
| Anthropic | Claude Pro/Max subscription OR API key | Claude Code access |
| Notion | Internal integration token | Task creation (optional) |
| Google | Google account | Drive sync |

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Meetily API changes break export | Medium | Medium | Maintain fork, track upstream, contribute back |
| Transcription accuracy issues | Medium | Medium | Use larger Whisper models, GPU acceleration, manual review |
| Project misclassification | Low | Medium | Manual review step, confidence threshold, fallback folder |
| Sync conflicts | Medium | Low | Avoid simultaneous edits, use Git backup, conflict resolution |
| Performance on long meetings | Low | Low | Chunked processing, streaming transcription |
| Claude Code rate limits | Low | Low | Batch processing, local caching |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Transcription accuracy | >95% | Manual review sampling |
| Project match accuracy | >85% | Correct folder placement |
| Processing time | <2 min per meeting | Stopwatch |
| Time saved per meeting | >15 min | User estimate |
| Adoption by collaborators | >80% | Active sync users |

---

## Appendices

### Appendix A: Meetily Fork Modifications Summary

**Files to create:**
- `backend/app/export.py` — Markdown export module

**Files to modify:**
- `backend/app/config.py` — Add export path configuration
- `backend/app/db.py` — Hook export into completion flow
- `frontend/src/settings.tsx` — Add export path UI (optional)

### Appendix B: Claude Code Configuration Files

Complete configuration package available as separate download:

```
claude-configs/
├── CLAUDE.md
├── commands/
│   ├── ingest-meetings.md
│   ├── extract-actions.md
│   └── send-followups.md
├── skills/
│   └── meeting-processor/
│       └── SKILL.md
├── templates/
│   ├── PROJECT.md
│   └── meeting-note.md
└── README.md
```

### Appendix C: Sample Meeting Note (Processed)

```markdown
---
title: "OpenCivics Q1 Planning"
date: 2026-01-07T14:30:00
duration: 45
status: processed
source: meetily
project: "[[projects/opencivics/index]]"
participants:
  - "[[people/Benjamin Life]]"
  - "[[people/Jane Doe]]"
themes:
  - quarterly-planning
  - governance
tags:
  - meeting
  - opencivics
  - planning
processed_at: 2026-01-07T15:45:00
confidence: high
---

# OpenCivics Q1 Planning

## Summary

Discussed Q1 priorities for [[projects/opencivics/index|OpenCivics]], focusing on the [[concepts/TrustGraph]] implementation timeline and [[concepts/Localism Fund]] integration. Key decisions:

1. TrustGraph MVP target: end of February
2. Expert network pilot: 10 initial participants
3. Weekly sync moving to Tuesdays

## Action Items

- [ ] **[[people/Benjamin Life]]**: Draft TrustGraph technical spec *(due: 2026-01-14)*
- [ ] **[[people/Jane Doe]]**: Recruit pilot participants *(due: 2026-01-21)*
- [ ] **[[people/Benjamin Life]]**: Schedule stakeholder review *(due: 2026-01-10)*

## Transcript

**[Benjamin]:** Let's start with the TrustGraph timeline. I think we can have an MVP by end of February if we scope it right.

**[Jane]:** That works for me. I can handle recruiting the pilot participants. How many are we thinking?

**[Benjamin]:** Let's start with 10 for the expert network pilot...

[transcript continues...]
```

### Appendix D: Resources

**Meetily:**
- Repository: https://github.com/Zackriya-Solutions/meeting-minutes
- Documentation: https://meetily.ai/docs
- Releases: https://github.com/Zackriya-Solutions/meeting-minutes/releases

**Claude Code:**
- Documentation: https://docs.anthropic.com/claude-code
- Slash commands: https://docs.anthropic.com/claude-code/commands
- Skills: https://docs.anthropic.com/claude-code/skills

**Obsidian:**
- Documentation: https://help.obsidian.md
- Community plugins: https://obsidian.md/plugins

**Ollama:**
- Documentation: https://ollama.ai/docs
- Models: https://ollama.ai/library

---

*Document generated January 2026. For latest updates, check project repository.*