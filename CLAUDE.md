# Hyperflow Knowledge Vault

AI-augmented knowledge management system with multi-source content ingestion, entity extraction, and static site publishing.

## Quick Start

### For Meetings
1. **Record a meeting** in [Meetily](https://github.com/Zackriya-Solutions/meeting-minutes)
2. **Sync**: Run `/sync-meetily` to export from Meetily's database
3. **Process**: Run `/ingest-meetings` to enrich and route to projects

### For Other Content
```bash
# Ingest a PDF
/ingest ~/Downloads/paper.pdf

# Ingest a web article
/ingest https://example.com/article

# Ingest an arXiv paper
/ingest arxiv:2301.00001

# Quick capture
/clip My quick note
```

## Commands

### Core Pipeline

| Command | Description |
|---------|-------------|
| `/run-pipeline` | Run complete pipeline (sync → ingest → tasks → calendar → followups) |
| `/sync-meetily` | Export new meetings from Meetily's database |
| `/ingest-meetings` | Process meetings, match to projects, add wiki-links |

### Content Ingestion

| Command | Description |
|---------|-------------|
| `/ingest [source]` | Universal ingestion - auto-detects PDFs, URLs, papers |
| `/clip [title]` | Quick capture from conversation context |

### Productivity

| Command | Description |
|---------|-------------|
| `/extract-actions` | Extract action items from a meeting note |
| `/sync-tasks` | Update person profiles with action items |
| `/sync-notion` | Push tasks to Notion databases |
| `/send-followups` | Generate follow-up emails for participants |
| `/link-calendar` | Match meetings to Google Calendar events |

### Knowledge Management

| Command | Description |
|---------|-------------|
| `/save [message]` | Create detailed Git commit of all vault changes |

### Publishing

| Command | Description |
|---------|-------------|
| `/publish` | Build and deploy knowledge base as static site |

## Directory Structure

```
├── _inbox/
│   ├── meetings/     # Raw Meetily exports
│   ├── papers/       # Ingested PDFs and research papers
│   ├── articles/     # Ingested web articles
│   └── clippings/    # Quick captures
├── _templates/       # Note templates
├── _drafts/          # Generated email drafts
├── projects/         # Project folders
│   └── [project-name]/
│       ├── PROJECT.md   # Project context (team, keywords)
│       ├── index.md     # Project overview
│       └── meetings/    # Processed meeting notes
├── people/           # Person notes
├── organizations/    # Organization profiles
├── meetings/         # General/unmatched meetings
├── concepts/         # Wiki-linkable concepts
├── scripts/          # Python utilities
│   ├── sync_meetily.py      # Meetily database export
│   ├── extract_entities.py  # Entity extraction (spaCy/regex fallback)
│   ├── entities_to_kb.py    # Convert entities to KB markdown files
│   ├── process_inbox.py     # Unified inbox processor (auto-detect file types)
│   ├── sync_tasks.py        # Sync tasks to person profiles
│   ├── diarize_audio.py     # Speaker diarization (pyannote + Whisper)
│   ├── ingest_pdf.py        # PDF ingestion
│   ├── ingest_web.py        # Web content ingestion
│   ├── ingest_paper.py      # Academic paper ingestion
│   ├── publish_site.py      # Static site publishing
│   ├── integrations.py      # API integrations (Notion, Gmail, Calendar)
│   └── setup_google.py      # Google OAuth setup
├── tasks.md          # Central task dashboard with Dataview queries
├── .vscode/          # VS Code/Foam configuration
├── .foam/            # Foam templates
└── .hyperflow/       # Hyperflow configuration
```

## Content Ingestion

### Supported Sources

| Source | Script | Destination |
|--------|--------|-------------|
| Meetily meetings | `sync_meetily.py` | `_inbox/meetings/` |
| PDF documents | `ingest_pdf.py` | `_inbox/papers/` |
| Web articles | `ingest_web.py` | `_inbox/articles/` |
| arXiv papers | `ingest_paper.py` | `_inbox/papers/` |
| DOI references | `ingest_paper.py` | `_inbox/papers/` |
| Semantic Scholar | `ingest_paper.py` | `_inbox/papers/` |

### Script Usage

```bash
# PDFs
python scripts/ingest_pdf.py document.pdf --auto-route

# Web pages (uses Jina Reader)
python scripts/ingest_web.py "https://example.com" --auto-route

# Academic papers
python scripts/ingest_paper.py arxiv:2301.00001 --download-pdf
python scripts/ingest_paper.py doi:10.1234/example

# Entity extraction
python scripts/extract_entities.py file.md --format table
```

## Entity Extraction

Hyperflow uses a hybrid extraction approach:
- **spaCy** for fast offline NER (people, organizations, dates)
- **LangExtract** (optional) for deep structured extraction with Ollama

```bash
# Quick extraction
python scripts/extract_entities.py meeting.md

# With deep extraction (requires Ollama)
python scripts/extract_entities.py meeting.md --deep --model llama3.2
```

## Publishing

Publish your knowledge base as a static site using:
- **Quartz** (recommended) - Best graph view, GitHub Pages
- **Jekyll Garden** - Simple, Netlify-friendly
- **Eleventy** - Fast, flexible
- **Gatsby KB** - Rich interactivity

```bash
# Build with Quartz
python scripts/publish_site.py build --framework quartz

# Preview locally
python scripts/publish_site.py preview --port 8080

# Deploy to GitHub Pages
python scripts/publish_site.py deploy --target github-pages
```

### Privacy Filtering

Only files marked as public are published:
```yaml
---
title: My Public Note
public: true  # or add 'public' to tags
---
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
| Organizations | `[[organizations/Name]]` |

- Link first occurrence only
- Max 10-15 links per document
- Create stubs if missing

## Editor Support

### VS Code / Foam
- Open this folder in VS Code
- Install recommended extensions (see `.vscode/extensions.json`)
- Use Foam for wiki-links, backlinks, and graph view
- Run tasks via Command Palette (`Ctrl+Shift+P` → "Tasks: Run Task")

### Obsidian
- Open this folder as an Obsidian vault
- Templates available in `_templates/`
- Graph view and backlinks work out of the box

## Setup Checklist

### Required
- [ ] Install [Python 3.10+](https://python.org)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Install spaCy model: `python -m spacy download en_core_web_md`

### For Meetings
- [ ] Install [Meetily](https://github.com/Zackriya-Solutions/meeting-minutes/releases)
- [ ] Install [Ollama](https://ollama.ai) and pull a model (`ollama pull llama3.2`)

### For Publishing
- [ ] Install Node.js 18+
- [ ] Set up Quartz: `npx quartz create`

### For Integrations
- [ ] Set up Notion integration (add token to `.hyperflow/config.yaml`)
- [ ] Set up Google OAuth: `python scripts/setup_google.py`

## Configuration

Create `.hyperflow/config.yaml`:

```yaml
# Meetily database path (auto-detected if not set)
meetily_db_path: ~/Library/Application Support/com.meetily.ai/meeting_minutes.sqlite

# Notion integration
notion:
  token: ntn_xxxxx
  default_workspace: "My Workspace"

# Publishing
publishing:
  framework: quartz
  site_path: ~/projects/my-knowledge-site
  deploy_target: github-pages
```

## Architecture

```
Content Sources              Processing                    Outputs
───────────────             ──────────────                ─────────
Meetily       ─┐            ┌────────────┐
PDFs          ─┼─→ Ingest ─→│  spaCy /   │─→ Vault        ─→ Obsidian/Foam
Web articles  ─┤   Scripts  │ LangExtract│   (Markdown)   ─→ Quartz Site
arXiv papers  ─┤            └────────────┘                ─→ Notion Tasks
Clipboard     ─┘                  │                       ─→ Gmail Drafts
Audio files   ─┐                  ↓                       ─→ Calendar Links
              ─┴─→ Diarize ─→ Claude Code
                             (Orchestration)
```

## Unified Inbox Processing

Drop any file into `_inbox/` and the system auto-detects and routes:

```bash
# Process all files in inbox
python scripts/process_inbox.py

# Watch for new files
python scripts/process_inbox.py --watch

# Preview what would happen
python scripts/process_inbox.py --dry-run
```

Supported file types:
- **PDFs** → `_inbox/papers/`
- **URLs** (`.url`, `.txt` with links) → `_inbox/articles/`
- **arXiv/DOI** (in `.txt`) → `_inbox/papers/`
- **Markdown** → Routed by content type
- **Images** → `_inbox/clippings/`

## Entity to Knowledge Base

Extract entities and create markdown profiles automatically:

```bash
# From a meeting file
python scripts/entities_to_kb.py --from-file meeting.md

# Batch process a folder
python scripts/entities_to_kb.py --batch _inbox/meetings/
```

This creates:
- `people/Name.md` - Person profiles with contact info and mentions
- `organizations/Name.md` - Organization profiles
- `concepts/Term.md` - Concept definitions with examples

## Speaker Diarization

Process audio files with speaker identification:

```bash
# Basic diarization
python scripts/diarize_audio.py recording.mp3

# With known speaker names
python scripts/diarize_audio.py meeting.mp3 --speakers "Alice,Bob" --num-speakers 2

# Output as subtitles
python scripts/diarize_audio.py interview.wav --format srt
```

Requirements:
- `pip install pyannote.audio openai-whisper torch`
- Hugging Face token (set `HF_TOKEN` env var)

## Task Management

Central task dashboard at `tasks.md` with Dataview queries:

- View all open tasks across the vault
- Filter by project or person
- Track tasks from meetings
- See recently completed items

Sync tasks to person profiles:
```bash
python scripts/sync_tasks.py --all-meetings
```

## Version Control

Use `/save` to create detailed commits:

```
/save after weekly planning sessions
```

Creates commits like:
```
[Knowledge]: Add OpenCivics meetings and new contact

Changes:
- meetings/2024-01-07-opencivics-planning.md (new)
- people/Jane Smith.md (new)

Stats:
- 2 new meeting notes
- 1 new person profile
```
