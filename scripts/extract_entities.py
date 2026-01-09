#!/usr/bin/env python3
"""
Entity extraction for Hyperflow using spaCy and optionally LangExtract.

This module provides hybrid entity extraction:
- Fast layer: spaCy for quick NER (people, orgs, dates, locations)
- Deep layer: LangExtract/Ollama for structured extraction (tasks, concepts, relationships)

Usage:
    # Extract from a single file
    python extract_entities.py file.md --output entities.json

    # Batch process a directory
    python extract_entities.py _inbox/ --recursive

    # Use deep extraction with Ollama
    python extract_entities.py file.md --deep --model llama3.2

    # Domain-specific extraction
    python extract_entities.py file.md --domain meeting
"""

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml

# Optional imports with graceful fallback
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("Warning: spaCy not installed. Run: pip install spacy && python -m spacy download en_core_web_md")

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


@dataclass
class Entity:
    """Represents an extracted entity with position information."""
    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Complete extraction result for a document."""
    filepath: str
    extracted_at: str
    people: list[Entity] = field(default_factory=list)
    organizations: list[Entity] = field(default_factory=list)
    dates: list[Entity] = field(default_factory=list)
    locations: list[Entity] = field(default_factory=list)
    concepts: list[Entity] = field(default_factory=list)
    tasks: list[dict] = field(default_factory=list)
    suggested_links: list[str] = field(default_factory=list)
    suggested_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert Entity objects to dicts
        for key in ['people', 'organizations', 'dates', 'locations', 'concepts']:
            result[key] = [asdict(e) if isinstance(e, Entity) else e for e in result[key]]
        return result


class SpacyExtractor:
    """Fast entity extraction using spaCy."""

    def __init__(self, model: str = "en_core_web_md"):
        if not SPACY_AVAILABLE:
            raise RuntimeError("spaCy not available. Install with: pip install spacy")

        try:
            self.nlp = spacy.load(model)
        except OSError:
            print(f"Model '{model}' not found. Downloading...")
            spacy.cli.download(model)
            self.nlp = spacy.load(model)

    def extract(self, text: str) -> dict[str, list[Entity]]:
        """Extract entities from text using spaCy NER."""
        doc = self.nlp(text)

        entities = {
            'people': [],
            'organizations': [],
            'dates': [],
            'locations': [],
        }

        label_map = {
            'PERSON': 'people',
            'ORG': 'organizations',
            'DATE': 'dates',
            'TIME': 'dates',
            'GPE': 'locations',
            'LOC': 'locations',
            'FAC': 'locations',
        }

        for ent in doc.ents:
            category = label_map.get(ent.label_)
            if category:
                entity = Entity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.9,  # spaCy doesn't provide confidence scores
                )
                entities[category].append(entity)

        # Deduplicate by text (keep first occurrence)
        for category in entities:
            seen = set()
            unique = []
            for e in entities[category]:
                if e.text.lower() not in seen:
                    seen.add(e.text.lower())
                    unique.append(e)
            entities[category] = unique

        return entities


class OllamaExtractor:
    """Deep extraction using Ollama for structured entity extraction."""

    def __init__(self, model: str = "llama3.2"):
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama not available. Install with: pip install ollama")
        self.model = model

    def extract_tasks(self, text: str) -> list[dict]:
        """Extract action items and tasks from text."""
        prompt = """Extract action items and tasks from this text. For each task, identify:
- task: The action to be taken
- assignee: Who is responsible (if mentioned)
- deadline: Due date (if mentioned)
- confidence: high/medium/low based on clarity

Return as JSON array. Only include clear action items.

Text:
{text}

JSON (array of tasks):"""

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt.format(text=text[:4000]),  # Limit input size
                format="json",
            )
            return json.loads(response['response'])
        except Exception as e:
            print(f"Warning: Ollama extraction failed: {e}")
            return []

    def extract_concepts(self, text: str) -> list[Entity]:
        """Extract key concepts and technical terms."""
        prompt = """Identify key concepts, technical terms, and important topics from this text.
For each concept, provide:
- term: The concept name
- definition: Brief explanation (1 sentence)
- importance: high/medium/low

Return as JSON array. Focus on domain-specific terminology and important ideas.

Text:
{text}

JSON (array of concepts):"""

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt.format(text=text[:4000]),
                format="json",
            )
            concepts_data = json.loads(response['response'])
            return [
                Entity(
                    text=c.get('term', ''),
                    label='CONCEPT',
                    start=0,  # Ollama doesn't provide positions
                    end=0,
                    confidence=0.8 if c.get('importance') == 'high' else 0.6,
                    metadata={'definition': c.get('definition', '')}
                )
                for c in concepts_data if c.get('term')
            ]
        except Exception as e:
            print(f"Warning: Concept extraction failed: {e}")
            return []


class HyperflowExtractor:
    """Main extractor combining spaCy and Ollama for hybrid extraction."""

    def __init__(self, model: str = "llama3.2", use_deep: bool = False):
        self.spacy_extractor = SpacyExtractor() if SPACY_AVAILABLE else None
        self.ollama_extractor = OllamaExtractor(model) if (use_deep and OLLAMA_AVAILABLE) else None
        self.use_deep = use_deep

    def extract(self, text: str, domain: str = "general") -> ExtractionResult:
        """Extract all entities from text."""
        result = ExtractionResult(
            filepath="",
            extracted_at=datetime.now().isoformat(),
        )

        # Fast extraction with spaCy
        if self.spacy_extractor:
            spacy_entities = self.spacy_extractor.extract(text)
            result.people = spacy_entities['people']
            result.organizations = spacy_entities['organizations']
            result.dates = spacy_entities['dates']
            result.locations = spacy_entities['locations']

        # Deep extraction with Ollama (if enabled)
        if self.ollama_extractor and self.use_deep:
            result.tasks = self.ollama_extractor.extract_tasks(text)
            result.concepts = self.ollama_extractor.extract_concepts(text)

        # Generate suggestions
        result.suggested_links = self._generate_link_suggestions(result)
        result.suggested_tags = self._generate_tag_suggestions(result, domain)

        return result

    def process_file(self, filepath: Path, domain: str = "general") -> ExtractionResult:
        """Process a markdown file and extract entities."""
        content = filepath.read_text(encoding='utf-8')

        # Strip frontmatter for cleaner extraction
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]

        result = self.extract(content, domain)
        result.filepath = str(filepath)

        return result

    def _generate_link_suggestions(self, result: ExtractionResult) -> list[str]:
        """Generate wiki-link suggestions based on extracted entities."""
        suggestions = []

        # People → [[people/Name]]
        for person in result.people:
            name = person.text.strip()
            if len(name.split()) >= 2:  # Full names only
                suggestions.append(f"[[people/{name}]]")

        # Organizations → [[organizations/Name]]
        for org in result.organizations:
            suggestions.append(f"[[organizations/{org.text}]]")

        # Concepts → [[concepts/Term]]
        for concept in result.concepts:
            suggestions.append(f"[[concepts/{concept.text}]]")

        return suggestions[:15]  # Limit to 15 suggestions

    def _generate_tag_suggestions(self, result: ExtractionResult, domain: str) -> list[str]:
        """Generate tag suggestions based on content."""
        tags = set()

        # Domain-based tags
        if domain == "meeting":
            tags.add("meeting")
        elif domain == "research":
            tags.add("research")
            tags.add("paper")

        # Entity-based tags
        if len(result.tasks) > 0:
            tags.add("action-items")

        if any('project' in c.text.lower() for c in result.concepts):
            tags.add("project")

        # Add concept-based tags (up to 5)
        for concept in result.concepts[:5]:
            tag = concept.text.lower().replace(' ', '-')
            if len(tag) <= 20:
                tags.add(tag)

        return list(tags)


def extract_tasks_regex(text: str) -> list[dict]:
    """Fallback task extraction using regex patterns (no LLM required)."""
    patterns = [
        r'\[\s*\]\s*(?:\*\*)?(.+?)(?:\*\*)?(?:\s*\(due:?\s*([^)]+)\))?',  # - [ ] Task (due: date)
        r'(?:TODO|Action|Task):\s*(.+)',  # TODO: task
        r'(\w+)\s+(?:will|should|needs? to|must)\s+(.+?)(?:\.|$)',  # Name will do something
        r'@(\w+)\s+(.+?)(?:\.|$)',  # @name task
    ]

    tasks = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            groups = match.groups()
            if len(groups) >= 1:
                task = {
                    'task': groups[0].strip() if groups[0] else '',
                    'assignee': groups[1].strip() if len(groups) > 1 and groups[1] else None,
                    'deadline': None,
                    'confidence': 'medium',
                    'source_pattern': pattern[:30],
                }
                if task['task']:
                    tasks.append(task)

    return tasks


@click.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file for JSON results')
@click.option('--recursive', '-r', is_flag=True, help='Process directories recursively')
@click.option('--domain', '-d', type=click.Choice(['general', 'meeting', 'research', 'article']),
              default='general', help='Content domain for specialized extraction')
@click.option('--deep', is_flag=True, help='Use deep extraction with Ollama LLM')
@click.option('--model', '-m', default='llama3.2', help='Ollama model for deep extraction')
@click.option('--format', '-f', 'output_format', type=click.Choice(['json', 'table', 'markdown']),
              default='json', help='Output format')
def main(input_path: str, output: Optional[str], recursive: bool, domain: str,
         deep: bool, model: str, output_format: str):
    """Extract entities from markdown files.

    INPUT_PATH can be a single file or directory.

    Examples:
        extract_entities.py meeting.md -o entities.json
        extract_entities.py _inbox/meetings/ -r --domain meeting
        extract_entities.py paper.md --deep --model mistral
    """
    input_path = Path(input_path)

    # Initialize extractor
    try:
        extractor = HyperflowExtractor(model=model, use_deep=deep)
    except Exception as e:
        click.echo(f"Error initializing extractor: {e}", err=True)
        sys.exit(1)

    # Collect files to process
    if input_path.is_file():
        files = [input_path]
    else:
        pattern = '**/*.md' if recursive else '*.md'
        files = list(input_path.glob(pattern))

    if not files:
        click.echo("No markdown files found.")
        sys.exit(0)

    # Process files
    results = []
    for filepath in files:
        click.echo(f"Processing: {filepath}")
        try:
            result = extractor.process_file(filepath, domain)

            # Add regex-based task extraction as fallback
            if not result.tasks:
                content = filepath.read_text()
                result.tasks = extract_tasks_regex(content)

            results.append(result)
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)

    # Output results
    if output_format == 'json':
        output_data = [r.to_dict() for r in results]
        if len(output_data) == 1:
            output_data = output_data[0]

        if output:
            Path(output).write_text(json.dumps(output_data, indent=2))
            click.echo(f"Results written to: {output}")
        else:
            click.echo(json.dumps(output_data, indent=2))

    elif output_format == 'table' and RICH_AVAILABLE:
        for result in results:
            console.print(f"\n[bold]{result.filepath}[/bold]")

            table = Table(title="Extracted Entities")
            table.add_column("Type", style="cyan")
            table.add_column("Entity", style="green")
            table.add_column("Count", style="yellow")

            table.add_row("People", ", ".join(e.text for e in result.people[:5]), str(len(result.people)))
            table.add_row("Organizations", ", ".join(e.text for e in result.organizations[:5]), str(len(result.organizations)))
            table.add_row("Dates", ", ".join(e.text for e in result.dates[:5]), str(len(result.dates)))
            table.add_row("Concepts", ", ".join(e.text for e in result.concepts[:5]), str(len(result.concepts)))
            table.add_row("Tasks", str(len(result.tasks)), "")

            console.print(table)

            if result.suggested_links:
                console.print("\n[bold]Suggested Links:[/bold]")
                for link in result.suggested_links[:10]:
                    console.print(f"  {link}")

    elif output_format == 'markdown':
        for result in results:
            md = f"# Entity Extraction: {Path(result.filepath).name}\n\n"
            md += f"*Extracted: {result.extracted_at}*\n\n"

            if result.people:
                md += "## People\n"
                for p in result.people:
                    md += f"- {p.text}\n"
                md += "\n"

            if result.organizations:
                md += "## Organizations\n"
                for o in result.organizations:
                    md += f"- {o.text}\n"
                md += "\n"

            if result.tasks:
                md += "## Action Items\n"
                for t in result.tasks:
                    assignee = f" (@{t['assignee']})" if t.get('assignee') else ""
                    md += f"- [ ] {t['task']}{assignee}\n"
                md += "\n"

            if result.suggested_links:
                md += "## Suggested Links\n"
                for link in result.suggested_links:
                    md += f"- {link}\n"

            if output:
                Path(output).write_text(md)
            else:
                click.echo(md)

    # Summary
    total_entities = sum(
        len(r.people) + len(r.organizations) + len(r.dates) + len(r.concepts)
        for r in results
    )
    total_tasks = sum(len(r.tasks) for r in results)
    click.echo(f"\nProcessed {len(files)} file(s): {total_entities} entities, {total_tasks} tasks extracted")


if __name__ == '__main__':
    main()
