# Hyperflow Evolution Strategy
## From Meeting Transcripts to Full Knowledge Management Suite

**Version:** 2.0
**Date:** January 2026
**Status:** Strategic Planning Document

---

## Executive Summary

Hyperflow is evolving from a meeting transcript ingestion pipeline into a comprehensive **AI-augmented knowledge management system**. This document outlines the strategy to transform Hyperflow into a standalone tool that:

1. **Ingests diverse content** — meetings, PDFs, websites, research papers, notes
2. **Extracts entities efficiently** — using LangExtract/spaCy to save Claude tokens for orchestration
3. **Manages knowledge** — tagging, linking, routing, and organizing content
4. **Automates productivity** — task reminders, email follow-ups, calendar integration
5. **Publishes knowledge** — static site generation via Quartz for public/team wikis

---

## Current State Analysis

### What We Have

```
Meetily → sync_meetily.py → _inbox/meetings/ → Claude Code Skills → Obsidian Vault
                                                      ↓
                                              Notion/Gmail/Calendar
```

**Strengths:**
- Privacy-first, local-first architecture
- Multi-source transcript support (Meetily, Fathom, Otter, manual)
- Sophisticated project matching algorithm (weighted scoring)
- Good integration layer (integrations.py)
- Well-structured slash commands and skills

**Limitations:**
- Single content type focus (meetings only)
- Entity extraction happens in Claude (expensive in tokens)
- No publishing capability
- Manual triggering of most workflows
- VS Code experience not optimized (Obsidian-centric)

---

## Strategic Vision

### The End State

```
                              ┌─────────────────────────────────────────────────────┐
                              │              HYPERFLOW KNOWLEDGE HUB                 │
                              └─────────────────────────────────────────────────────┘
                                                      │
     ┌───────────────────────────────────────────────┼───────────────────────────────────────────────┐
     │                                               │                                               │
     ▼                                               ▼                                               ▼
┌─────────────┐                              ┌─────────────────┐                           ┌─────────────────┐
│   INGEST    │                              │    PROCESS      │                           │    OUTPUT       │
├─────────────┤                              ├─────────────────┤                           ├─────────────────┤
│ • Meetings  │      ┌──────────────┐        │ • LangExtract   │      ┌──────────────┐     │ • Wiki Links    │
│ • PDFs      │─────▶│ Conversion   │───────▶│ • Entity NER    │─────▶│ Claude Code  │────▶│ • Notion Tasks  │
│ • Websites  │      │ Layer        │        │ • Classification│      │ Orchestrator │     │ • Email Drafts  │
│ • Papers    │      └──────────────┘        │ • Summarization │      └──────────────┘     │ • Calendar      │
│ • Notes     │                              └─────────────────┘                           │ • Quartz Site   │
│ • Clipboard │                                                                            └─────────────────┘
└─────────────┘
```

### Core Principles

1. **Separation of Concerns** — Heavy processing (entity extraction, PDF parsing) in dedicated scripts; Claude for orchestration
2. **Token Efficiency** — Use local/cheaper models for preprocessing, reserve Claude for judgment calls
3. **Format Agnostic** — Everything converts to Markdown with structured frontmatter
4. **Progressive Enhancement** — Works with simple text, gets smarter with more metadata
5. **Platform Flexible** — Works in Obsidian, Foam (VS Code), or plain filesystem

---

## Technology Stack

### New Components to Add

| Component | Purpose | Why This Choice |
|-----------|---------|-----------------|
| **[LangExtract](https://github.com/google/langextract)** | Entity extraction with source grounding | Google's new library; supports Ollama for local LLMs; precise character offsets |
| **[marker](https://github.com/VikParuchuri/marker)** | PDF to Markdown conversion | Best-in-class accuracy; handles tables, equations, complex layouts |
| **[Jina Reader](https://github.com/jina-ai/reader)** | Web to Markdown | Clean extraction; free tier; or self-host ReaderLM-v2 |
| **[spaCy](https://spacy.io/)** | Fast offline NER | Preprocessing layer; no API calls; multiple model sizes |
| **[Quartz](https://github.com/jackyzha0/quartz)** | Static site generator | Built for Obsidian vaults; graph view; full-text search |
| **[Foam](https://foambubble.github.io/foam/)** | VS Code wiki (optional) | Native VS Code experience; Git-based; open source |

### Revised Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    INGESTION LAYER                                       │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │
│  │ sync_meetily  │  │ ingest_pdf    │  │ ingest_web    │  │ ingest_paper  │            │
│  │     .py       │  │     .py       │  │     .py       │  │     .py       │            │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘            │
│          │                  │                  │                  │                     │
│          └──────────────────┴──────────────────┴──────────────────┘                     │
│                                         │                                               │
│                                         ▼                                               │
│                              ┌─────────────────────┐                                    │
│                              │    _inbox/          │                                    │
│                              │    ├── meetings/    │                                    │
│                              │    ├── papers/      │                                    │
│                              │    ├── articles/    │                                    │
│                              │    └── clippings/   │                                    │
│                              └──────────┬──────────┘                                    │
└─────────────────────────────────────────┼───────────────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────┼───────────────────────────────────────────────┐
│                                 EXTRACTION LAYER                                         │
│                                         ▼                                               │
│                              ┌─────────────────────┐                                    │
│                              │   extract_entities  │ ◄── LangExtract + spaCy            │
│                              │        .py          │     (Ollama / local models)        │
│                              └──────────┬──────────┘                                    │
│                                         │                                               │
│                                         ▼                                               │
│                    ┌────────────────────────────────────────┐                           │
│                    │  Structured JSON:                      │                           │
│                    │  • people: [{name, spans, confidence}] │                           │
│                    │  • orgs: [{name, spans}]               │                           │
│                    │  • concepts: [{term, definition}]      │                           │
│                    │  • dates: [{date, context}]            │                           │
│                    │  • tasks: [{task, assignee, due}]      │                           │
│                    └────────────────────┬───────────────────┘                           │
└─────────────────────────────────────────┼───────────────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────┼───────────────────────────────────────────────┐
│                              ORCHESTRATION LAYER                                         │
│                                         ▼                                               │
│                              ┌─────────────────────┐                                    │
│                              │    Claude Code      │                                    │
│                              │    Skills/Commands  │                                    │
│                              └──────────┬──────────┘                                    │
│                                         │                                               │
│      ┌──────────────┬──────────────┬────┴────┬──────────────┬──────────────┐           │
│      ▼              ▼              ▼         ▼              ▼              ▼           │
│ ┌─────────┐   ┌─────────┐   ┌─────────┐ ┌─────────┐   ┌─────────┐   ┌─────────┐       │
│ │/ingest  │   │/extract │   │/sync    │ │/send    │   │/publish │   │/search  │       │
│ │         │   │-actions │   │-notion  │ │-followup│   │         │   │         │       │
│ └─────────┘   └─────────┘   └─────────┘ └─────────┘   └─────────┘   └─────────┘       │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────┼───────────────────────────────────────────────┐
│                                 OUTPUT LAYER                                             │
│                                         ▼                                               │
│    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                   │
│    │  Obsidian Vault │    │  Notion Tasks   │    │  Quartz Site    │                   │
│    │  (or Foam)      │    │  Gmail Drafts   │    │  GitHub Pages   │                   │
│    │                 │    │  Calendar Events│    │                 │                   │
│    └─────────────────┘    └─────────────────┘    └─────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Script Specifications

### 1. `scripts/extract_entities.py` — LangExtract Integration

**Purpose:** Pre-process content to extract entities before Claude orchestration

```python
"""
Entity extraction using LangExtract with Ollama backend.
Saves Claude tokens by doing heavy lifting locally.
"""

from langextract import Extractor
from langextract.llms import OllamaLLM
import spacy
from pathlib import Path
import json

class HyperflowExtractor:
    """Hybrid entity extraction: spaCy for speed, LangExtract for depth."""

    def __init__(self, model: str = "llama3.2"):
        # Fast layer: spaCy for basic NER
        self.nlp = spacy.load("en_core_web_md")

        # Deep layer: LangExtract for structured extraction
        self.llm = OllamaLLM(model=model)
        self.extractor = Extractor(llm=self.llm)

    def extract_fast(self, text: str) -> dict:
        """Quick spaCy extraction for preprocessing."""
        doc = self.nlp(text)
        return {
            "people": [{"name": ent.text, "start": ent.start_char, "end": ent.end_char}
                      for ent in doc.ents if ent.label_ == "PERSON"],
            "orgs": [{"name": ent.text, "start": ent.start_char, "end": ent.end_char}
                    for ent in doc.ents if ent.label_ == "ORG"],
            "dates": [{"text": ent.text, "start": ent.start_char, "end": ent.end_char}
                     for ent in doc.ents if ent.label_ == "DATE"],
        }

    def extract_deep(self, text: str, domain: str = "general") -> dict:
        """Deep LangExtract for structured domain-specific extraction."""
        # Define extraction schema based on domain
        schemas = {
            "meeting": MeetingSchema,  # tasks, decisions, attendees
            "research": ResearchSchema,  # claims, citations, methods
            "general": GeneralSchema,   # people, concepts, relationships
        }

        result = self.extractor.extract(
            text=text,
            schema=schemas.get(domain, GeneralSchema),
            return_spans=True  # Get character offsets for wiki-linking
        )

        return result.to_dict()

    def process_file(self, filepath: Path, domain: str = "general") -> dict:
        """Process a markdown file, return enriched metadata."""
        content = filepath.read_text()

        # Stage 1: Fast NER
        fast_entities = self.extract_fast(content)

        # Stage 2: Deep extraction (if needed based on content length/complexity)
        if len(content) > 1000:
            deep_entities = self.extract_deep(content, domain)
        else:
            deep_entities = {}

        return {
            "filepath": str(filepath),
            "fast_entities": fast_entities,
            "deep_entities": deep_entities,
            "suggested_links": self._generate_link_suggestions(fast_entities, deep_entities),
            "suggested_tags": self._generate_tag_suggestions(fast_entities, deep_entities),
        }
```

**CLI Usage:**
```bash
# Extract entities from a single file
python scripts/extract_entities.py file.md --domain meeting --output entities.json

# Batch process inbox
python scripts/extract_entities.py _inbox/ --recursive --output-dir _processed/

# Use with specific Ollama model
python scripts/extract_entities.py file.md --model mistral --deep
```

---

### 2. `scripts/ingest_pdf.py` — PDF Ingestion

**Purpose:** Convert PDFs to markdown with extracted metadata

```python
"""
PDF to Markdown conversion using marker library.
Extracts text, tables, images, and generates frontmatter.
"""

from marker.convert import convert_single_pdf
from marker.models import load_all_models
from pathlib import Path
import yaml
from datetime import datetime

class PDFIngester:
    def __init__(self):
        self.models = load_all_models()

    def ingest(self, pdf_path: Path, output_dir: Path = None) -> Path:
        """Convert PDF to markdown with frontmatter."""

        # Convert PDF
        full_text, images, metadata = convert_single_pdf(
            str(pdf_path),
            self.models
        )

        # Generate output path
        output_dir = output_dir or Path("_inbox/papers")
        output_dir.mkdir(parents=True, exist_ok=True)

        slug = self._slugify(pdf_path.stem)
        output_path = output_dir / f"{datetime.now():%Y-%m-%d}_{slug}.md"

        # Build frontmatter
        frontmatter = {
            "title": metadata.get("title", pdf_path.stem),
            "date": datetime.now().isoformat(),
            "source": "pdf",
            "source_file": str(pdf_path),
            "status": "pending_enrichment",
            "content_type": self._classify_pdf(metadata),
            "pages": metadata.get("pages", 0),
            "tags": ["pdf", "imported"],
        }

        # Write output
        content = f"---\n{yaml.dump(frontmatter)}---\n\n{full_text}"
        output_path.write_text(content)

        # Save images if any
        if images:
            img_dir = output_dir / "attachments" / slug
            img_dir.mkdir(parents=True, exist_ok=True)
            for i, img in enumerate(images):
                img.save(img_dir / f"image_{i}.png")

        return output_path

    def _classify_pdf(self, metadata: dict) -> str:
        """Classify PDF type: paper, book, article, document."""
        # Heuristics based on structure
        if "abstract" in str(metadata).lower():
            return "research_paper"
        elif metadata.get("pages", 0) > 50:
            return "book"
        else:
            return "document"
```

**CLI Usage:**
```bash
# Ingest single PDF
python scripts/ingest_pdf.py paper.pdf

# Batch ingest with custom output
python scripts/ingest_pdf.py ~/Downloads/*.pdf --output _inbox/papers/

# Classify and route automatically
python scripts/ingest_pdf.py paper.pdf --auto-route
```

---

### 3. `scripts/ingest_web.py` — Web Content Ingestion

**Purpose:** Convert web pages to clean markdown

```python
"""
Web to Markdown using Jina Reader API or local ReaderLM.
Cleans HTML, extracts main content, generates frontmatter.
"""

import httpx
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import yaml

class WebIngester:
    def __init__(self, use_local: bool = False, api_key: str = None):
        self.use_local = use_local
        self.api_key = api_key
        self.jina_base = "https://r.jina.ai/"

    def ingest(self, url: str, output_dir: Path = None) -> Path:
        """Fetch URL and convert to markdown."""

        # Fetch via Jina Reader
        if self.use_local:
            content, metadata = self._fetch_local(url)
        else:
            content, metadata = self._fetch_jina(url)

        # Generate output
        output_dir = output_dir or Path("_inbox/articles")
        output_dir.mkdir(parents=True, exist_ok=True)

        domain = urlparse(url).netloc.replace("www.", "")
        slug = self._slugify(metadata.get("title", domain))
        output_path = output_dir / f"{datetime.now():%Y-%m-%d}_{slug}.md"

        # Build frontmatter
        frontmatter = {
            "title": metadata.get("title", "Untitled"),
            "date": datetime.now().isoformat(),
            "source": "web",
            "source_url": url,
            "domain": domain,
            "status": "pending_enrichment",
            "content_type": self._classify_content(url, metadata),
            "author": metadata.get("author"),
            "published": metadata.get("published"),
            "tags": ["web", "imported", domain.split(".")[0]],
        }

        # Write output
        full_content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n"
        full_content += f"# {frontmatter['title']}\n\n"
        full_content += f"> Source: [{url}]({url})\n\n"
        full_content += content

        output_path.write_text(full_content)
        return output_path

    def _fetch_jina(self, url: str) -> tuple[str, dict]:
        """Fetch via Jina Reader API."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers["X-Return-Format"] = "markdown"

        response = httpx.get(f"{self.jina_base}{url}", headers=headers, timeout=30)
        response.raise_for_status()

        # Parse response (Jina returns markdown with metadata in comments)
        content = response.text
        metadata = self._parse_jina_metadata(content)

        return content, metadata

    def _classify_content(self, url: str, metadata: dict) -> str:
        """Classify: article, documentation, blog, reference."""
        domain = urlparse(url).netloc.lower()

        if any(d in domain for d in ["arxiv", "doi.org", "scholar"]):
            return "research"
        elif any(d in domain for d in ["docs.", "documentation", "readme"]):
            return "documentation"
        elif any(d in domain for d in ["blog", "medium", "substack"]):
            return "blog"
        elif any(d in domain for d in ["wikipedia", "wiki"]):
            return "reference"
        else:
            return "article"
```

**CLI Usage:**
```bash
# Ingest single URL
python scripts/ingest_web.py "https://example.com/article"

# Batch from URL list
python scripts/ingest_web.py --file urls.txt --output _inbox/articles/

# Use local ReaderLM model
python scripts/ingest_web.py "https://..." --local
```

---

### 4. `scripts/ingest_paper.py` — Academic Paper Ingestion

**Purpose:** Specialized ingestion for research papers (arXiv, DOI, etc.)

```python
"""
Research paper ingestion with citation extraction.
Handles arXiv, DOI resolution, and structured metadata.
"""

import arxiv
import httpx
from pathlib import Path
from datetime import datetime
import yaml

class PaperIngester:
    def __init__(self):
        self.arxiv_client = arxiv.Client()

    def ingest_arxiv(self, arxiv_id: str, output_dir: Path = None) -> Path:
        """Ingest paper from arXiv ID."""

        # Fetch metadata
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(self.arxiv_client.results(search))

        # Download PDF and convert
        pdf_path = Path(f"/tmp/{arxiv_id.replace('/', '_')}.pdf")
        paper.download_pdf(filename=str(pdf_path))

        # Use PDF ingester for content
        from ingest_pdf import PDFIngester
        pdf_ingester = PDFIngester()

        output_dir = output_dir or Path("_inbox/papers")
        output_path = pdf_ingester.ingest(pdf_path, output_dir)

        # Enrich with arXiv metadata
        self._enrich_with_arxiv_metadata(output_path, paper)

        return output_path

    def _enrich_with_arxiv_metadata(self, path: Path, paper) -> None:
        """Add rich arXiv metadata to frontmatter."""
        content = path.read_text()

        # Parse existing frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2]
        else:
            frontmatter = {}
            body = content

        # Enrich frontmatter
        frontmatter.update({
            "title": paper.title,
            "authors": [a.name for a in paper.authors],
            "abstract": paper.summary,
            "arxiv_id": paper.entry_id,
            "published": paper.published.isoformat(),
            "updated": paper.updated.isoformat() if paper.updated else None,
            "categories": paper.categories,
            "doi": paper.doi,
            "content_type": "research_paper",
            "tags": ["paper", "arxiv"] + list(paper.categories[:3]),
        })

        # Add abstract section
        abstract_section = f"\n## Abstract\n\n{paper.summary}\n\n"

        # Write back
        new_content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n"
        new_content += abstract_section + body
        path.write_text(new_content)
```

**CLI Usage:**
```bash
# Ingest from arXiv
python scripts/ingest_paper.py arxiv:2301.00001

# Ingest from DOI
python scripts/ingest_paper.py doi:10.1234/example

# Ingest from Semantic Scholar
python scripts/ingest_paper.py s2:12345678
```

---

### 5. `scripts/publish_quartz.py` — Static Site Publishing

**Purpose:** Build and deploy knowledge base as Quartz static site

```python
"""
Publish Obsidian/Foam vault to GitHub Pages via Quartz.
Handles selective export, privacy filtering, and deployment.
"""

import subprocess
import shutil
from pathlib import Path
import yaml

class QuartzPublisher:
    def __init__(self, vault_path: Path, quartz_path: Path):
        self.vault_path = vault_path
        self.quartz_path = quartz_path
        self.content_path = quartz_path / "content"

    def publish(self,
                include_patterns: list[str] = None,
                exclude_patterns: list[str] = None,
                public_only: bool = True) -> None:
        """Build and optionally deploy Quartz site."""

        # Step 1: Clear content directory
        if self.content_path.exists():
            shutil.rmtree(self.content_path)
        self.content_path.mkdir(parents=True)

        # Step 2: Copy eligible files
        copied = self._copy_files(include_patterns, exclude_patterns, public_only)
        print(f"Copied {len(copied)} files to Quartz content/")

        # Step 3: Build site
        self._build()

    def _copy_files(self, include, exclude, public_only) -> list[Path]:
        """Copy files that match criteria."""
        copied = []

        default_include = ["projects/**/*.md", "concepts/**/*.md", "people/**/*.md"]
        default_exclude = ["_*/**", ".*/**", "**/PROJECT.md", "**/*private*"]

        include = include or default_include
        exclude = exclude or default_exclude

        for pattern in include:
            for file in self.vault_path.glob(pattern):
                if self._should_exclude(file, exclude):
                    continue
                if public_only and not self._is_public(file):
                    continue

                # Copy to quartz content
                rel_path = file.relative_to(self.vault_path)
                dest = self.content_path / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)

                # Process file (strip private sections, etc.)
                content = self._process_for_publish(file)
                dest.write_text(content)
                copied.append(dest)

        return copied

    def _is_public(self, file: Path) -> bool:
        """Check if file is marked public in frontmatter."""
        content = file.read_text()
        if not content.startswith("---"):
            return False

        try:
            frontmatter = yaml.safe_load(content.split("---")[1])
            return frontmatter.get("public", False) or "public" in frontmatter.get("tags", [])
        except:
            return False

    def _process_for_publish(self, file: Path) -> str:
        """Strip private content, fix links for Quartz."""
        content = file.read_text()

        # Remove sections marked private
        # (implementation: strip content between <!-- private --> markers)

        # Convert Obsidian links to Quartz format if needed
        # [[page]] → [page](page.md)

        return content

    def _build(self) -> None:
        """Run Quartz build."""
        subprocess.run(
            ["npx", "quartz", "build"],
            cwd=self.quartz_path,
            check=True
        )

    def deploy(self, target: str = "github-pages") -> None:
        """Deploy to hosting platform."""
        if target == "github-pages":
            subprocess.run(
                ["npx", "quartz", "sync", "--no-pull"],
                cwd=self.quartz_path,
                check=True
            )
```

**CLI Usage:**
```bash
# Build site with public content only
python scripts/publish_quartz.py build --public-only

# Include specific folders
python scripts/publish_quartz.py build --include "projects/opencivics/**" "concepts/**"

# Build and deploy to GitHub Pages
python scripts/publish_quartz.py deploy --target github-pages

# Preview locally
python scripts/publish_quartz.py preview --port 8080
```

---

## Claude Code Skills & Commands

### New Commands to Add

| Command | Purpose | Implementation |
|---------|---------|----------------|
| `/ingest` | Universal ingestion dispatcher | Routes to appropriate ingester based on input type |
| `/publish` | Build and deploy Quartz site | Runs publish_quartz.py with configured options |
| `/search` | Semantic search across vault | Uses embeddings for similarity search |
| `/summarize` | Generate summary of any content | Works with meetings, papers, articles |
| `/clip` | Quick capture from clipboard | Instant ingestion of text/URLs |

### `/ingest` Command (Universal Dispatcher)

**File:** `.claude/commands/ingest.md`

```markdown
---
name: ingest
description: Universal content ingestion - automatically routes to appropriate handler
---

# Universal Ingest

Intelligently ingest content from various sources into the knowledge base.

## Usage

```
/ingest [source]
```

## Source Detection

Automatically detect and route based on input:

| Input Pattern | Handler | Destination |
|---------------|---------|-------------|
| `*.pdf` | ingest_pdf.py | _inbox/papers/ |
| `http(s)://arxiv.org/*` | ingest_paper.py | _inbox/papers/ |
| `http(s)://*` | ingest_web.py | _inbox/articles/ |
| `doi:*` | ingest_paper.py | _inbox/papers/ |
| `_inbox/meetings/*.md` | /ingest-meetings | projects/*/meetings/ |
| Raw text (clipboard) | ingest_note.py | _inbox/clippings/ |

## Workflow

1. **Detect source type** from input pattern
2. **Run appropriate ingestion script**
3. **Extract entities** using extract_entities.py
4. **Route to appropriate folder** based on content type and project matching
5. **Create stub files** for new people/concepts/organizations
6. **Report results** with suggested actions

## Examples

```bash
# Ingest a PDF
/ingest ~/Downloads/paper.pdf

# Ingest from URL
/ingest https://arxiv.org/abs/2301.00001

# Ingest from arXiv ID
/ingest arxiv:2301.00001

# Process all pending inbox items
/ingest --all
```
```

### `/publish` Command

**File:** `.claude/commands/publish.md`

```markdown
---
name: publish
description: Build and deploy knowledge base as Quartz static site
---

# Publish Knowledge Base

Build and deploy your knowledge base to GitHub Pages as a searchable static site.

## Usage

```
/publish [options]
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--preview` | Build and serve locally | false |
| `--deploy` | Deploy to GitHub Pages | false |
| `--include` | Glob patterns to include | projects/, concepts/ |
| `--public-only` | Only publish files tagged #public | true |

## Workflow

1. **Check Quartz installation** (install if missing)
2. **Scan vault** for publishable content
3. **Copy eligible files** to Quartz content/
4. **Process for publishing**:
   - Strip private sections
   - Convert wiki links
   - Generate index pages
5. **Build static site**
6. **Deploy** (if --deploy flag)

## Privacy Filtering

Files are published only if:
- Tagged with `#public` in frontmatter
- OR in a folder marked public in config
- AND not matching exclude patterns

Files automatically excluded:
- `_*/**` (inbox, drafts, templates)
- `**/PROJECT.md` (project configs)
- `**/*private*`, `**/*personal*`
- Files with `private: true` in frontmatter

## Configuration

In `.hyperflow/config.yaml`:

```yaml
publishing:
  quartz_path: ~/projects/my-quartz-site
  default_public_folders:
    - concepts/
    - projects/*/index.md
  exclude_patterns:
    - "**/meetings/**"
    - "**/personal/**"
  site_title: "My Knowledge Base"
  site_url: "https://username.github.io/knowledge"
```
```

### `/clip` Command (Quick Capture)

**File:** `.claude/commands/clip.md`

```markdown
---
name: clip
description: Quick capture from clipboard to knowledge base
---

# Quick Clip

Instantly capture clipboard content to knowledge base.

## Usage

```
/clip [title]
```

## Behavior

1. **Read clipboard** content
2. **Detect content type**:
   - URL → run web ingester
   - Text with structure → create note
   - Plain text → create clipping
3. **Extract entities** inline
4. **Save to** `_inbox/clippings/YYYY-MM-DD_title.md`
5. **Suggest tags and links**

## Output Format

```markdown
---
title: "[Title or auto-generated]"
date: 2026-01-09T20:30:00
source: clipboard
status: pending_review
tags:
  - clipping
---

# [Title]

[Clipboard content]

---
*Clipped on 2026-01-09 at 20:30*
```
```

---

## Platform Decision: Obsidian vs Foam

### Recommendation: **Support Both, Optimize for Foam**

The architecture should be platform-agnostic (markdown files work everywhere), but development workflow should optimize for **Foam in VS Code** because:

| Factor | Obsidian | Foam (VS Code) |
|--------|----------|----------------|
| Claude Code integration | Terminal plugin required | Native, seamless |
| Git workflow | Third-party plugin | Native |
| Extension ecosystem | Obsidian plugins | Full VS Code extensions |
| Multi-language support | Limited | Excellent |
| File editing | Single file focus | Multi-file, split views |
| Price | Free (sync paid) | Free |
| Open source | No | Yes |

### Hybrid Approach

```
Knowledge Vault (Markdown files)
       │
       ├── Foam (VS Code) ← Primary editing & Claude Code
       │     • Daily work
       │     • Code integration
       │     • Git operations
       │
       └── Obsidian ← Reading & visualization
             • Graph view
             • Mobile access
             • Presentation
```

### Foam Setup for Hyperflow

1. **Install Foam extension pack** in VS Code
2. **Configure workspace settings**:

```json
// .vscode/settings.json
{
  "foam.edit.linkReferenceDefinitions": "withoutExtensions",
  "foam.openDailyNote.directory": "journal",
  "foam.graph.style": {
    "node": {
      "meetings": "#4CAF50",
      "people": "#2196F3",
      "concepts": "#FF9800",
      "projects": "#9C27B0"
    }
  }
}
```

3. **Add Foam-specific templates** in `.foam/templates/`

---

## Implementation Phases

### Phase 1: Entity Extraction Layer (Week 1-2)

**Goal:** Reduce Claude token usage by 60-70% with local entity extraction

**Tasks:**
- [ ] Install dependencies: `pip install langextract spacy`
- [ ] Download spaCy model: `python -m spacy download en_core_web_md`
- [ ] Implement `scripts/extract_entities.py`
- [ ] Create extraction schemas for meetings, papers, articles
- [ ] Integrate with existing `/ingest-meetings` command
- [ ] Benchmark: compare Claude-only vs hybrid extraction

**Success Metric:** Entity extraction accuracy ≥90%, token reduction ≥50%

### Phase 2: Multi-Source Ingestion (Week 3-4)

**Goal:** Ingest PDFs, websites, and papers alongside meetings

**Tasks:**
- [ ] Install marker: `pip install marker-pdf`
- [ ] Implement `scripts/ingest_pdf.py`
- [ ] Implement `scripts/ingest_web.py` (Jina Reader)
- [ ] Implement `scripts/ingest_paper.py` (arXiv/DOI)
- [ ] Create `/ingest` universal command
- [ ] Add new inbox folders: `_inbox/papers/`, `_inbox/articles/`
- [ ] Update routing logic for new content types

**Success Metric:** Successfully ingest 10 PDFs, 10 articles, 5 papers

### Phase 3: Publishing Pipeline (Week 5-6)

**Goal:** Publish knowledge base to GitHub Pages

**Tasks:**
- [ ] Set up Quartz in sibling directory
- [ ] Implement `scripts/publish_quartz.py`
- [ ] Create `/publish` command
- [ ] Configure privacy filtering rules
- [ ] Set up GitHub Actions for automatic deployment
- [ ] Add `#public` tagging workflow to existing commands

**Success Metric:** Live site with 50+ pages, graph view working

### Phase 4: Foam Optimization (Week 7-8)

**Goal:** First-class VS Code/Foam experience

**Tasks:**
- [ ] Create Foam workspace configuration
- [ ] Add VS Code tasks for common operations
- [ ] Create snippets for quick note creation
- [ ] Integrate Foam templates with Hyperflow templates
- [ ] Add graph styling by content type
- [ ] Document Foam + Obsidian hybrid workflow

**Success Metric:** Full Hyperflow workflow possible without leaving VS Code

### Phase 5: Advanced Automation (Ongoing)

**Goal:** Intelligent automation and productivity features

**Tasks:**
- [ ] Implement `/clip` quick capture
- [ ] Add scheduled task reminders
- [ ] Create weekly review generator
- [ ] Add concept relationship extraction
- [ ] Implement cross-reference suggestions
- [ ] Build reading list management

---

## File Structure (Evolved)

```
hyperflow/
├── .claude/
│   ├── commands/
│   │   ├── ingest.md              # NEW: Universal ingestion
│   │   ├── ingest-meetings.md     # Existing
│   │   ├── publish.md             # NEW: Quartz publishing
│   │   ├── clip.md                # NEW: Quick capture
│   │   ├── search.md              # NEW: Semantic search
│   │   └── [existing commands]
│   ├── skills/
│   │   └── meeting-processor/
│   └── CLAUDE.md
├── scripts/
│   ├── extract_entities.py        # NEW: LangExtract/spaCy
│   ├── ingest_pdf.py              # NEW: PDF ingestion
│   ├── ingest_web.py              # NEW: Web ingestion
│   ├── ingest_paper.py            # NEW: Academic papers
│   ├── publish_quartz.py          # NEW: Static site build
│   ├── integrations.py            # Existing
│   ├── sync_meetily.py            # Existing
│   └── setup_google.py            # Existing
├── _inbox/
│   ├── meetings/                  # Existing
│   ├── papers/                    # NEW
│   ├── articles/                  # NEW
│   └── clippings/                 # NEW
├── _templates/
│   ├── paper.md                   # NEW
│   ├── article.md                 # NEW
│   └── [existing templates]
├── .foam/                         # NEW: Foam configuration
│   ├── templates/
│   └── snippets/
├── .vscode/                       # NEW: VS Code/Foam settings
│   ├── settings.json
│   ├── tasks.json
│   └── extensions.json
├── quartz/                        # NEW: Quartz site (or sibling repo)
│   ├── content/
│   ├── quartz.config.ts
│   └── ...
├── requirements.txt               # Updated with new deps
└── README.md
```

---

## Updated Requirements

```
# requirements.txt - Hyperflow 2.0

# Existing
pyyaml>=6.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
google-api-python-client>=2.0.0

# NEW: Entity Extraction
langextract>=0.1.0              # Google's entity extraction
spacy>=3.7.0                    # Fast NER
en-core-web-md @ https://...    # spaCy model (or install separately)

# NEW: Content Ingestion
marker-pdf>=0.2.0               # PDF to Markdown
httpx>=0.27.0                   # Modern HTTP client (for Jina)
arxiv>=2.1.0                    # arXiv API client
scholarly>=1.7.0                # Google Scholar (optional)

# NEW: Publishing
# (Quartz is Node-based, installed separately via npm)

# Optional: Local LLM
ollama>=0.1.0                   # Ollama Python client
```

---

## Conclusion

This strategy transforms Hyperflow from a meeting-focused tool into a comprehensive knowledge management system by:

1. **Adding efficient entity extraction** with LangExtract + spaCy (saves Claude tokens)
2. **Expanding content types** to PDFs, web articles, and research papers
3. **Enabling publishing** via Quartz static site generator
4. **Optimizing for VS Code/Foam** while maintaining Obsidian compatibility
5. **Maintaining privacy-first principles** with local processing

The modular architecture means each component can be developed and tested independently, and the system remains useful at every stage of implementation.

**Next Action:** Begin Phase 1 by implementing `extract_entities.py` with LangExtract integration.
