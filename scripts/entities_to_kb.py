#!/usr/bin/env python3
"""
Entity to Knowledge Base Processor for Hyperflow.

Converts extracted entities into markdown knowledge base entries:
- Creates/updates person profiles in people/
- Creates/updates organization profiles in organizations/
- Creates/updates concept notes in concepts/
- Links entities back to source documents

Usage:
    # Process entities from a JSON file
    python entities_to_kb.py entities.json

    # Process extraction output directly from a meeting
    python entities_to_kb.py --from-file meeting.md

    # Batch process all meetings
    python entities_to_kb.py --batch _inbox/meetings/
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml


def slugify(text: str) -> str:
    """Convert text to a safe filename slug."""
    # Replace spaces with dashes
    slug = re.sub(r'\s+', '-', text.strip())
    # Remove non-alphanumeric except dashes
    slug = re.sub(r'[^\w\-]', '', slug)
    # Remove multiple dashes
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def title_case_name(name: str) -> str:
    """Properly title case a person's name."""
    # Handle common suffixes/prefixes
    parts = name.split()
    result = []
    for part in parts:
        if part.lower() in ['van', 'von', 'de', 'del', 'la', 'le']:
            result.append(part.lower())
        elif part.upper() in ['II', 'III', 'IV', 'JR', 'SR', 'PHD', 'MD']:
            result.append(part.upper())
        else:
            result.append(part.capitalize())
    return ' '.join(result)


class KnowledgeBaseWriter:
    """Writes extracted entities to markdown knowledge base files."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.people_dir = vault_path / 'people'
        self.orgs_dir = vault_path / 'organizations'
        self.concepts_dir = vault_path / 'concepts'

        # Ensure directories exist
        for d in [self.people_dir, self.orgs_dir, self.concepts_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def process_extraction(self, extraction: dict, source_file: Optional[str] = None) -> dict:
        """Process extraction results and create/update KB entries."""
        stats = {
            'people_created': 0,
            'people_updated': 0,
            'orgs_created': 0,
            'orgs_updated': 0,
            'concepts_created': 0,
            'concepts_updated': 0,
        }

        source_link = None
        if source_file:
            # Create a relative link to the source
            source_path = Path(source_file)
            if source_path.is_absolute():
                try:
                    source_path = source_path.relative_to(self.vault_path)
                except ValueError:
                    pass
            source_link = f"[[{source_path}]]"

        # Process people
        for person in extraction.get('people', []):
            name = person.get('text', '') if isinstance(person, dict) else person
            if name and len(name) > 1:
                created = self.create_or_update_person(name, source_link)
                if created:
                    stats['people_created'] += 1
                else:
                    stats['people_updated'] += 1

        # Process organizations
        for org in extraction.get('organizations', []):
            name = org.get('text', '') if isinstance(org, dict) else org
            if name and len(name) > 1:
                created = self.create_or_update_org(name, source_link)
                if created:
                    stats['orgs_created'] += 1
                else:
                    stats['orgs_updated'] += 1

        # Process concepts
        for concept in extraction.get('concepts', []):
            if isinstance(concept, dict):
                name = concept.get('text', '')
                definition = concept.get('metadata', {}).get('definition', '')
            else:
                name = concept
                definition = ''

            if name and len(name) > 1:
                created = self.create_or_update_concept(name, definition, source_link)
                if created:
                    stats['concepts_created'] += 1
                else:
                    stats['concepts_updated'] += 1

        return stats

    def create_or_update_person(self, name: str, source_link: Optional[str] = None) -> bool:
        """Create or update a person profile. Returns True if created, False if updated."""
        name = title_case_name(name)
        filepath = self.people_dir / f"{name}.md"

        if filepath.exists():
            # Update existing - add source to mentions if not present
            if source_link:
                content = filepath.read_text(encoding='utf-8')
                if source_link not in content:
                    # Add to Mentions section
                    if '## Mentions' in content:
                        content = content.replace(
                            '## Mentions\n',
                            f'## Mentions\n\n- {source_link}\n'
                        )
                    else:
                        content += f"\n## Mentions\n\n- {source_link}\n"
                    filepath.write_text(content, encoding='utf-8')
            return False

        # Create new profile
        frontmatter = {
            'title': name,
            'type': 'person',
            'created': datetime.now().strftime('%Y-%m-%d'),
            'tags': ['person'],
        }

        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False).strip()}
---

# {name}

## Contact

- Email:
- Role:
- Organization:

## Context

<!-- How do you know this person? What's their relevance? -->

## Notes

## Mentions

{f'- {source_link}' if source_link else ''}

## Related

- [[]]
"""
        filepath.write_text(content, encoding='utf-8')
        return True

    def create_or_update_org(self, name: str, source_link: Optional[str] = None) -> bool:
        """Create or update an organization profile."""
        filepath = self.orgs_dir / f"{name}.md"

        if filepath.exists():
            if source_link:
                content = filepath.read_text(encoding='utf-8')
                if source_link not in content:
                    if '## Mentions' in content:
                        content = content.replace(
                            '## Mentions\n',
                            f'## Mentions\n\n- {source_link}\n'
                        )
                    else:
                        content += f"\n## Mentions\n\n- {source_link}\n"
                    filepath.write_text(content, encoding='utf-8')
            return False

        frontmatter = {
            'title': name,
            'type': 'organization',
            'created': datetime.now().strftime('%Y-%m-%d'),
            'tags': ['organization'],
        }

        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False).strip()}
---

# {name}

## Overview

<!-- What is this organization? What do they do? -->

## Key People

- [[]]

## Links

- Website:

## Notes

## Mentions

{f'- {source_link}' if source_link else ''}

## Related

- [[]]
"""
        filepath.write_text(content, encoding='utf-8')
        return True

    def create_or_update_concept(self, name: str, definition: str = '',
                                  source_link: Optional[str] = None) -> bool:
        """Create or update a concept note."""
        filepath = self.concepts_dir / f"{name}.md"

        if filepath.exists():
            if source_link:
                content = filepath.read_text(encoding='utf-8')
                if source_link not in content:
                    if '## Mentions' in content:
                        content = content.replace(
                            '## Mentions\n',
                            f'## Mentions\n\n- {source_link}\n'
                        )
                    else:
                        content += f"\n## Mentions\n\n- {source_link}\n"
                    filepath.write_text(content, encoding='utf-8')
            return False

        frontmatter = {
            'title': name,
            'type': 'concept',
            'created': datetime.now().strftime('%Y-%m-%d'),
            'tags': ['concept'],
        }

        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False).strip()}
---

# {name}

## Definition

{definition if definition else '<!-- What is this concept? -->'}

## Notes

## Examples

## Mentions

{f'- {source_link}' if source_link else ''}

## Related

- [[]]
"""
        filepath.write_text(content, encoding='utf-8')
        return True


def run_entity_extraction(filepath: Path, vault_path: Path) -> Optional[dict]:
    """Run entity extraction on a file and return results."""
    import subprocess

    scripts_dir = vault_path / 'scripts'
    result = subprocess.run(
        [sys.executable, str(scripts_dir / 'extract_entities.py'),
         str(filepath), '--format', 'json'],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        click.echo(f"Extraction failed: {result.stderr}", err=True)
        return None

    # Parse JSON from stdout (skip warning lines and summary)
    json_output = result.stdout
    try:
        # Find the JSON object boundaries
        json_start = json_output.find('{')
        if json_start == -1:
            return None

        # Find matching closing brace by counting braces
        brace_count = 0
        json_end = json_start
        for i, char in enumerate(json_output[json_start:], json_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

        json_str = json_output[json_start:json_end]
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        click.echo(f"Failed to parse extraction output: {e}", err=True)

    return None


@click.command()
@click.argument('input_path', type=click.Path(), required=False)
@click.option('--from-file', '-f', type=click.Path(exists=True),
              help='Extract entities from this file first')
@click.option('--batch', '-b', type=click.Path(exists=True),
              help='Process all markdown files in directory')
@click.option('--vault', '-v', type=click.Path(exists=True),
              help='Path to vault root')
def main(input_path: Optional[str], from_file: Optional[str],
         batch: Optional[str], vault: Optional[str]):
    """Convert extracted entities to knowledge base entries.

    INPUT_PATH can be a JSON file with extraction results.

    Examples:
        entities_to_kb.py entities.json
        entities_to_kb.py --from-file meeting.md
        entities_to_kb.py --batch _inbox/meetings/
    """
    vault_path = Path(vault) if vault else Path(__file__).parent.parent

    kb_writer = KnowledgeBaseWriter(vault_path)
    total_stats = {
        'people_created': 0, 'people_updated': 0,
        'orgs_created': 0, 'orgs_updated': 0,
        'concepts_created': 0, 'concepts_updated': 0,
    }

    if batch:
        # Process all markdown files in directory
        batch_path = Path(batch)
        files = list(batch_path.glob('**/*.md'))
        click.echo(f"Processing {len(files)} files...")

        for filepath in files:
            click.echo(f"\n{filepath.name}")
            extraction = run_entity_extraction(filepath, vault_path)
            if extraction:
                stats = kb_writer.process_extraction(extraction, str(filepath))
                for key in total_stats:
                    total_stats[key] += stats[key]
                click.echo(f"  Created: {stats['people_created']}P, {stats['orgs_created']}O, {stats['concepts_created']}C")

    elif from_file:
        # Extract then process
        filepath = Path(from_file)
        click.echo(f"Extracting entities from: {filepath}")
        extraction = run_entity_extraction(filepath, vault_path)
        if extraction:
            total_stats = kb_writer.process_extraction(extraction, str(filepath))

    elif input_path:
        # Process JSON file
        input_path = Path(input_path)
        if not input_path.exists():
            click.echo(f"File not found: {input_path}", err=True)
            sys.exit(1)

        extraction = json.loads(input_path.read_text())

        # Handle both single extraction and array
        if isinstance(extraction, list):
            for ext in extraction:
                source = ext.get('filepath', '')
                stats = kb_writer.process_extraction(ext, source)
                for key in total_stats:
                    total_stats[key] += stats[key]
        else:
            source = extraction.get('filepath', '')
            total_stats = kb_writer.process_extraction(extraction, source)

    else:
        click.echo("Please provide input: JSON file, --from-file, or --batch")
        sys.exit(1)

    # Summary
    click.echo(f"\n{'='*50}")
    click.echo("Knowledge Base Update Summary:")
    click.echo(f"  People:        {total_stats['people_created']} created, {total_stats['people_updated']} updated")
    click.echo(f"  Organizations: {total_stats['orgs_created']} created, {total_stats['orgs_updated']} updated")
    click.echo(f"  Concepts:      {total_stats['concepts_created']} created, {total_stats['concepts_updated']} updated")


if __name__ == '__main__':
    main()
