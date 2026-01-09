# Universal Ingest

Intelligently ingest content from various sources into the knowledge base.

## Usage

```
/ingest [source] [options]
```

## Source Detection

The command automatically detects source type and routes to the appropriate ingester:

| Input Pattern | Handler | Destination |
|---------------|---------|-------------|
| `*.pdf` (file path) | `ingest_pdf.py` | `_inbox/papers/` |
| `arxiv:*` or arxiv.org URL | `ingest_paper.py` | `_inbox/papers/` |
| `doi:*` or doi.org URL | `ingest_paper.py` | `_inbox/papers/` |
| `s2:*` (Semantic Scholar) | `ingest_paper.py` | `_inbox/papers/` |
| `http(s)://*` (web URL) | `ingest_web.py` | `_inbox/articles/` |
| `_inbox/meetings/*.md` | `/ingest-meetings` | `projects/*/meetings/` |
| `--all` flag | Process all inbox | Various |

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
2. Suggest running entity extraction if not done
3. Offer to run `/sync-tasks` for action item extraction
4. Offer to run `/sync-notion` for Notion integration

## Error Handling

- If ingestion script is not found, provide installation instructions
- If source type cannot be determined, ask for clarification
- On failure, preserve original file and show error details
