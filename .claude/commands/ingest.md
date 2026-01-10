# Universal Ingest

Intelligently ingest content from various sources into the knowledge base with automatic entity extraction and knowledge graph building.

## Usage

```
/ingest [source] [options]
```

## Source Detection

The command automatically detects source type and routes to the appropriate ingester:

| Input Pattern | Handler | Destination |
|---------------|---------|-------------|
| Files dropped in `_inbox/` | `process_inbox.py` | Auto-detected |
| `*.pdf` (file path) | `ingest_pdf.py` | `_inbox/papers/` |
| `arxiv:*` or arxiv.org URL | `ingest_paper.py` | `_inbox/papers/` |
| `doi:*` or doi.org URL | `ingest_paper.py` | `_inbox/papers/` |
| `s2:*` (Semantic Scholar) | `ingest_paper.py` | `_inbox/papers/` |
| `http(s)://*` (web URL) | `ingest_web.py` | `_inbox/articles/` |
| `_inbox/meetings/*.md` | `/ingest-meetings` | `projects/*/meetings/` |
| `--all` flag | Process all inbox | Various |

## Unified Inbox Processing

Drop ANY file type into `_inbox/` and the system will auto-detect and process:

```bash
# Process everything in inbox root
python scripts/process_inbox.py

# Watch for new files continuously
python scripts/process_inbox.py --watch

# Dry run to preview
python scripts/process_inbox.py --dry-run
```

Supported file types:
- **PDFs** → Converted to markdown, classified, routed to papers/
- **URLs** (in .url or .txt files) → Fetched via Jina Reader, routed to articles/
- **arXiv/DOI references** (in .txt) → Paper metadata fetched, routed to papers/
- **Markdown files** → Entity extraction, routed based on content type
- **Images** → Copied to clippings/

## Workflow

1. **Parse input** to determine source type
2. **Run appropriate ingestion script**:
   - PDF: `python scripts/ingest_pdf.py [file] --auto-route`
   - Web: `python scripts/ingest_web.py [url] --auto-route`
   - Paper: `python scripts/ingest_paper.py [ref] --download-pdf`
   - Meetings: Run `/ingest-meetings` command
3. **Extract entities** (optional): `python scripts/extract_entities.py [file]`
4. **Report results** with next steps

## Examples

### Ingest a PDF
```
/ingest ~/Downloads/research-paper.pdf
```
→ Runs `python scripts/ingest_pdf.py ~/Downloads/research-paper.pdf --auto-route`

### Ingest from arXiv
```
/ingest arxiv:2301.00001
```
→ Runs `python scripts/ingest_paper.py arxiv:2301.00001 --download-pdf`

### Ingest a web article
```
/ingest https://example.com/interesting-article
```
→ Runs `python scripts/ingest_web.py "https://example.com/interesting-article" --auto-route`

### Process all pending meetings
```
/ingest --meetings
```
→ Runs `/ingest-meetings` to process `_inbox/meetings/`

### Process everything in inbox
```
/ingest --all
```
→ Processes all content in `_inbox/` subdirectories

## Options

| Option | Description |
|--------|-------------|
| `--meetings` | Only process meetings from `_inbox/meetings/` |
| `--papers` | Only process papers from `_inbox/papers/` |
| `--articles` | Only process articles from `_inbox/articles/` |
| `--all` | Process all inbox content |
| `--extract` | Run entity extraction on ingested files |
| `--dry-run` | Show what would be done without making changes |

## Post-Ingestion

After ingestion, the command will:
1. Show summary of ingested files
2. Run entity extraction automatically
3. Create/update knowledge base entries for extracted entities:
   - **People** → `people/Name.md` profiles
   - **Organizations** → `organizations/Name.md` profiles
   - **Concepts** → `concepts/Term.md` definitions
4. Offer to run `/sync-tasks` for action item extraction
5. Offer to run `/sync-notion` for Notion integration

## Entity to Knowledge Base

After extraction, convert entities to markdown files:

```bash
# From a specific file
python scripts/entities_to_kb.py --from-file meeting.md

# From extraction JSON
python scripts/entities_to_kb.py entities.json

# Batch process all meetings
python scripts/entities_to_kb.py --batch _inbox/meetings/
```

This creates:
- Person profiles in `people/` with contact sections and mentions
- Organization profiles in `organizations/` with key people and notes
- Concept notes in `concepts/` with definitions and examples

## Full Pipeline Example

```bash
# 1. Drop files in inbox
cp ~/Downloads/*.pdf _inbox/

# 2. Process inbox (auto-detects and routes)
python scripts/process_inbox.py

# 3. Extract entities and build knowledge graph
python scripts/entities_to_kb.py --batch _inbox/papers/

# 4. Sync tasks to people profiles
python scripts/sync_tasks.py --all-meetings

# 5. Save changes with detailed commit
/save after processing new papers
```

## Error Handling

- If ingestion script is not found, provide installation instructions
- If source type cannot be determined, ask for clarification
- On failure, preserve original file and show error details
