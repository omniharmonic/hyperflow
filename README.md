# Hyperflow

**Turn every meeting into actionable knowledge — automatically.**

Hyperflow is an open-source, AI-powered meeting intelligence system that transforms raw meeting recordings into an interconnected knowledge base. Built on [Meetily](https://github.com/Zackriya-Solutions/meeting-minutes) (local transcription) and [Claude Code](https://claude.ai/claude-code) (AI orchestration), it delivers the power of enterprise meeting tools while keeping your data completely private.

> **Zero cloud dependencies. Fully local transcription. Your meetings stay yours.**

## Why Hyperflow?

| Traditional Workflow | With Hyperflow |
|----------------------|----------------|
| Record meeting | Record meeting |
| Manually take notes | *Automatic* |
| Transcribe (pay per minute) | *Free, local via Ollama* |
| Write summary | *AI-generated* |
| Extract action items | *Extracted & assigned* |
| Create tasks in project tool | *Synced to Notion automatically* |
| Email participants their tasks | *One command* |
| Link to calendar event | *Automatic* |
| Organize in knowledge base | *Routed to project folder* |
| Remember who said what | *Wiki-linked people profiles* |

**One command: `/run-pipeline`** — does all of the above.

## The Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                         YOUR MEETING                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  MEETILY (Local Transcription)                                   │
│  ├─ Records system audio + microphone                           │
│  ├─ Runs Whisper/Ollama locally — no API costs                  │
│  └─ Stores transcripts in SQLite                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  HYPERFLOW + CLAUDE CODE (AI Orchestration)                      │
│  ├─ /sync-meetily     → Exports from Meetily DB                 │
│  ├─ /ingest-meetings  → Extracts entities, creates wiki-links   │
│  ├─ /sync-tasks       → Pushes tasks to person profiles         │
│  ├─ /sync-notion      → Creates tasks in Notion                 │
│  ├─ /link-calendar    → Attaches notes to Google Calendar       │
│  └─ /send-followups   → Emails participants their action items  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  OBSIDIAN (Knowledge Base)                                       │
│  ├─ projects/*/meetings/  → Project-specific meeting notes      │
│  ├─ people/               → Auto-generated person profiles      │
│  ├─ concepts/             → Wiki-linkable knowledge graph       │
│  └─ Full-text search, backlinks, graph view                     │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### Intelligent Meeting Processing

- **Entity Extraction**: Automatically identifies people, organizations, concepts, and creates wiki-linked files
- **Project Routing**: Scores meetings against your project context and routes to the right folder
- **Summary Generation**: Creates structured summaries with key insights, decisions, and action items
- **Wiki-Linking**: First occurrence of each entity becomes a clickable link in your knowledge graph

### Task Management

- **Action Item Extraction**: Parses tasks from transcripts with assignees and due dates
- **Person Profiles**: Each person gets a file tracking their tasks, meeting history, and context
- **Notion Integration**: Push tasks directly to project-specific Notion databases
- **Email Follow-ups**: Generate personalized emails with each participant's action items

### Calendar Integration

- **Event Matching**: Finds the calendar event that corresponds to your meeting
- **Note Attachment**: Adds meeting summary and action items to calendar event description
- **Bidirectional Linking**: Meeting notes link to calendar; calendar links to notes

### Privacy-First Design

- **Local Transcription**: Meetily uses Whisper/Ollama — audio never leaves your machine
- **No Cloud Lock-in**: Your data lives in SQLite + Markdown files you control
- **Offline-Capable**: Core functionality works without internet
- **Git-Friendly**: Version control your entire knowledge base

## Quick Start

### Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| [Meetily](https://github.com/Zackriya-Solutions/meeting-minutes/releases) | Local transcription | Download release |
| [Ollama](https://ollama.ai) | Local LLM for transcription | `brew install ollama` |
| [Claude Code](https://claude.ai/claude-code) | AI orchestration | `npm install -g @anthropic-ai/claude-code` |
| Python 3 | Sync script | Usually pre-installed |

### Installation

```bash
# Clone as your Obsidian vault
git clone https://github.com/omniharmonic/hyperflow.git ~/Documents/hyperflow
cd ~/Documents/hyperflow

# Pull an Ollama model for Meetily
ollama pull llama3.2

# Open in Claude Code
claude
```

### First Run

```bash
# 1. Configure paths (finds Meetily database automatically)
/setup

# 2. Create your first project
/add-project

# 3. Record a meeting in Meetily, then:
/run-pipeline
```

That's it. Your meeting is now transcribed, summarized, wiki-linked, routed to the correct project, and optionally synced to Notion/Calendar/Email.

## Command Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `/run-pipeline` | **The big one** — runs the complete workflow end-to-end |
| `/setup` | Configure Meetily database and vault paths |
| `/add-project` | Interactive wizard to create a new project |

### Pipeline Stages

| Command | Stage | Description |
|---------|-------|-------------|
| `/sync-meetily` | 1 | Export new meetings from Meetily's SQLite database |
| `/ingest-meetings` | 2 | Extract entities, add wiki-links, route to projects |
| `/sync-tasks` | 3a | Push action items to person profile files |
| `/sync-notion` | 3b | Create tasks in project Notion databases |
| `/link-calendar` | 4 | Attach notes to Google Calendar events |
| `/send-followups` | 5 | Email participants their action items |

### Command Options

```bash
# Sync
/sync-meetily --all        # Re-export all meetings
/sync-meetily --list       # Show meetings in database

# Pipeline
/run-pipeline --skip-email    # Skip follow-up emails
/run-pipeline --draft-only    # Save emails as drafts
/run-pipeline --since 2024-01-01  # Only recent meetings

# Batch processing
/sync-notion --all            # Sync all meetings to Notion
/link-calendar --batch        # Link all unlinked meetings
```

## Directory Structure

```
hyperflow/
├── .claude/
│   └── commands/          # Claude Code slash commands
│       ├── run-pipeline.md
│       ├── sync-meetily.md
│       ├── ingest-meetings.md
│       └── ...
├── scripts/
│   └── sync_meetily.py    # Python script for database export
├── _inbox/
│   └── meetings/          # Raw meetings land here for processing
├── _drafts/
│   └── followups/         # Generated email drafts
├── projects/
│   └── [project-name]/
│       ├── PROJECT.md     # Project context (team, keywords, Notion config)
│       ├── index.md       # Project overview
│       └── meetings/      # Processed meeting notes
├── people/                # Auto-generated person profiles
├── concepts/              # Wiki-linkable concept definitions
├── organizations/         # Company/institution profiles
└── meetings/              # General meetings (no project match)
```

## How It Works

### Project Matching

When processing a meeting, Hyperflow scores it against each project:

| Signal | Points |
|--------|--------|
| Project name mentioned | +5 |
| Project alias used | +4 |
| Team member name | +3 |
| Project keyword | +2 |

- **≥8 points**: Strong match → routes to project folder
- **4-7 points**: Moderate match → routes with confidence note
- **<4 points**: No match → goes to general `meetings/` folder

### Entity Extraction

From a transcript like:
> "Sarah mentioned that we should talk to Marcus about the TrustGraph implementation..."

Hyperflow creates:
- `people/Sarah Chen.md` — with context from the meeting
- `people/Marcus Johnson.md` — linked as mentioned
- `concepts/TrustGraph.md` — linked technical concept

And transforms the transcript to:
> "[[people/Sarah Chen|Sarah]] mentioned that we should talk to [[people/Marcus Johnson|Marcus]] about the [[concepts/TrustGraph]] implementation..."

### Task Flow

```
Meeting transcript
    │
    ▼ (extract action items)
┌─────────────────────────────────────┐
│ - [ ] Complete onboarding - @Patricia│
│ - [ ] Review timeline - @Spencer     │
└─────────────────────────────────────┘
    │
    ├──► people/Patricia.md (Open Tasks section)
    ├──► people/Spencer.md (Open Tasks section)
    ├──► Notion database (if configured)
    └──► Email drafts (if requested)
```

## MCP Integrations

Hyperflow leverages Claude Code's [Model Context Protocol](https://modelcontextprotocol.io/) for external service connections:

### Notion

Push tasks to project-specific databases.

```yaml
# In projects/my-project/PROJECT.md:
notion_workspace: "My Workspace"
notion_tasks_database: "abc123-def456"
```

### Google Calendar

Automatically attach meeting notes to calendar events.

### Gmail

Send follow-up emails with personalized task lists.

**To configure MCP servers**: See [Claude Code MCP documentation](https://docs.anthropic.com/claude-code/mcp)

## Example Session

```
$ claude
claude> /run-pipeline

🚀 HYPERFLOW PIPELINE
═══════════════════════════════════════════════════

📋 Stage 1/5: Sync Meetily Database
────────────────────────────────────
✅ Synced 2 new meetings:
   • 2024-01-08T10-15_team-standup.md
   • 2024-01-08T14-30_client-call.md

📋 Stage 2/5: Ingest Meetings
────────────────────────────────────
📄 team-standup.md
   ├─ Project: OpenCivics (score: 9, high confidence)
   ├─ Entities: 3 people, 2 concepts
   ├─ Action items: 3
   └─ ✅ Moved to: projects/opencivics/meetings/

📄 client-call.md
   ├─ Project: Localism Fund (score: 6, medium confidence)
   ├─ Entities: 1 person (new), 2 concepts
   └─ ✅ Moved to: projects/localism-fund/meetings/

Created:
   • people/Jane Client.md (new)
   • concepts/Impact Metrics.md (new)

📋 Stage 3: Sync Tasks
────────────────────────────────────
✅ Updated 3 person profiles with 5 tasks
✅ Created 3 tasks in Notion (OpenCivics)

📋 Stage 4: Link Calendar
────────────────────────────────────
📅 Linked 2 meetings to calendar events

📋 Stage 5: Follow-ups
────────────────────────────────────
📧 Created 3 email drafts in Gmail

✨ PIPELINE COMPLETE
═══════════════════════════════════════════════════
   📥 Meetings synced: 2
   👤 People created: 1
   ✅ Tasks synced: 5
   📅 Calendar linked: 2
   📧 Drafts created: 3
```

## Configuration

### Environment Variables

```bash
# In ~/.zshrc or ~/.bashrc:
export MEETILY_DB_PATH="~/Library/Application Support/com.meetily.ai/meeting_minutes.sqlite"
export HYPERFLOW_VAULT="~/Documents/hyperflow"
```

Or create `.hyperflow.env` in your vault root:

```bash
MEETILY_DB_PATH="/path/to/meeting_minutes.sqlite"
HYPERFLOW_VAULT="/path/to/vault"
```

### Project Configuration

Each project needs a `PROJECT.md` with:

```yaml
---
name: "OpenCivics"
aliases:
  - "oc"
  - "the civics project"
status: active
# Optional: Notion integration
notion_workspace: "OpenCivics Workspace"
notion_tasks_database: "abc123-def456"
---

## Team

| Name | Email | Role |
|------|-------|------|
| Benjamin Life | ben@example.com | Lead |
| Patricia Parkinson | patricia@example.com | Designer |

## Keywords

- governance
- attestation
- TrustGraph
- civic technology
```

## Comparison

| Feature | Hyperflow | Otter.ai | Fireflies | Grain |
|---------|-----------|----------|-----------|-------|
| **Local transcription** | ✅ | ❌ | ❌ | ❌ |
| **Privacy** | Your machine | Cloud | Cloud | Cloud |
| **Cost** | Free | $16/mo+ | $19/mo+ | $19/mo+ |
| **Knowledge graph** | ✅ Obsidian | ❌ | ❌ | ❌ |
| **Custom routing** | ✅ | ❌ | ❌ | ❌ |
| **Wiki-linking** | ✅ | ❌ | ❌ | ❌ |
| **Open source** | ✅ | ❌ | ❌ | ❌ |
| **Notion sync** | ✅ | Limited | Limited | Limited |
| **Email follow-ups** | ✅ | ❌ | ✅ | ❌ |

## Roadmap

- [ ] Real-time transcription mode
- [ ] Meeting templates per project
- [ ] Slack/Discord notifications
- [ ] Linear/Jira task integration
- [ ] Speaker diarization
- [ ] Meeting analytics dashboard

## Contributing

Contributions welcome! This project is built with:

- **Python** for Meetily database sync
- **Markdown** for Claude Code commands and knowledge base
- **Claude Code** as the AI orchestration layer

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Acknowledgments

- [Meetily](https://github.com/Zackriya-Solutions/meeting-minutes) — The excellent open-source meeting recorder this builds on
- [Claude Code](https://claude.ai/claude-code) — The AI agent making intelligent processing possible
- [Obsidian](https://obsidian.md) — The knowledge base that ties it all together

## License

MIT — See [LICENSE](LICENSE)

---

**Built by [omniharmonic](https://github.com/omniharmonic)** | [Report Issues](https://github.com/omniharmonic/hyperflow/issues)
