#!/usr/bin/env python3
"""
Unified inbox processor for Hyperflow.

Auto-detects file types in _inbox/ and routes them to appropriate processors:
- PDFs → ingest_pdf.py → _inbox/papers/
- URLs (in .url or .txt files) → ingest_web.py → _inbox/articles/
- Markdown files → extract_entities.py → appropriate folder
- Meetily exports → process as meetings → _inbox/meetings/

Usage:
    # Process all files in inbox
    python process_inbox.py

    # Process specific file
    python process_inbox.py document.pdf

    # Watch mode (continuous monitoring)
    python process_inbox.py --watch

    # Dry run (show what would be processed)
    python process_inbox.py --dry-run
"""

import mimetypes
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml

# Initialize mimetypes
mimetypes.init()


@dataclass
class FileClassification:
    """Classification result for an inbox file."""
    file_type: str  # pdf, url, markdown, meeting, paper_id, image, unknown
    processor: str  # Script or action to use
    destination: str  # Target directory
    metadata: dict  # Additional info (url, arxiv_id, etc.)


class InboxProcessor:
    """Unified processor for all inbox file types."""

    # File patterns to ignore
    IGNORE_PATTERNS = [
        r'^\..*',  # Hidden files
        r'^_.*',  # Files starting with _
        r'\.gitkeep$',
        r'\.DS_Store$',
    ]

    # URL patterns for detection
    URL_PATTERN = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        re.IGNORECASE
    )
    ARXIV_PATTERN = re.compile(r'arxiv[:\s]*(\d{4}\.\d{4,5})', re.IGNORECASE)
    DOI_PATTERN = re.compile(r'doi[:\s]*(10\.\d{4,}/[^\s]+)', re.IGNORECASE)

    def __init__(self, inbox_path: Path, vault_path: Path):
        self.inbox_path = inbox_path
        self.vault_path = vault_path

        # Ensure subdirectories exist
        for subdir in ['meetings', 'papers', 'articles', 'clippings']:
            (inbox_path / subdir).mkdir(parents=True, exist_ok=True)

    def should_ignore(self, filepath: Path) -> bool:
        """Check if file should be ignored."""
        name = filepath.name
        for pattern in self.IGNORE_PATTERNS:
            if re.match(pattern, name):
                return True
        return False

    def classify(self, filepath: Path) -> FileClassification:
        """Classify a file and determine processing strategy."""
        name = filepath.name
        suffix = filepath.suffix.lower()
        content = None

        # Try to read content for text files
        if suffix in ['.txt', '.url', '.md', '.markdown', '.webloc']:
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                pass

        # PDF files
        if suffix == '.pdf':
            return FileClassification(
                file_type='pdf',
                processor='ingest_pdf.py',
                destination='papers',
                metadata={'original_name': name}
            )

        # URL files (Windows .url or macOS .webloc)
        if suffix == '.url':
            url = self._extract_url_from_shortcut(filepath)
            if url:
                return FileClassification(
                    file_type='url',
                    processor='ingest_web.py',
                    destination='articles',
                    metadata={'url': url}
                )

        # Plain text that might contain a URL or paper ID
        if suffix == '.txt' and content:
            # Check for arXiv ID
            arxiv_match = self.ARXIV_PATTERN.search(content)
            if arxiv_match:
                return FileClassification(
                    file_type='paper_id',
                    processor='ingest_paper.py',
                    destination='papers',
                    metadata={'arxiv_id': arxiv_match.group(1)}
                )

            # Check for DOI
            doi_match = self.DOI_PATTERN.search(content)
            if doi_match:
                return FileClassification(
                    file_type='paper_id',
                    processor='ingest_paper.py',
                    destination='papers',
                    metadata={'doi': doi_match.group(1)}
                )

            # Check for URL
            url_match = self.URL_PATTERN.search(content)
            if url_match:
                url = url_match.group(0)
                # Determine if it's a paper or article
                if 'arxiv.org' in url or 'doi.org' in url or 'semanticscholar' in url:
                    return FileClassification(
                        file_type='url',
                        processor='ingest_paper.py',
                        destination='papers',
                        metadata={'url': url}
                    )
                return FileClassification(
                    file_type='url',
                    processor='ingest_web.py',
                    destination='articles',
                    metadata={'url': url}
                )

        # Markdown files
        if suffix in ['.md', '.markdown']:
            # Check if it's a Meetily export
            if content:
                if 'source: meetily' in content.lower() or '**[' in content:
                    return FileClassification(
                        file_type='meeting',
                        processor='extract_entities.py',
                        destination='meetings',
                        metadata={'domain': 'meeting'}
                    )

                # Check frontmatter for content type hints
                frontmatter = self._parse_frontmatter(content)
                content_type = frontmatter.get('content_type', '').lower()
                source = frontmatter.get('source', '').lower()

                if content_type in ['research_paper', 'paper'] or source == 'paper':
                    return FileClassification(
                        file_type='markdown',
                        processor='extract_entities.py',
                        destination='papers',
                        metadata={'domain': 'research'}
                    )
                if content_type == 'article' or source == 'web':
                    return FileClassification(
                        file_type='markdown',
                        processor='extract_entities.py',
                        destination='articles',
                        metadata={'domain': 'article'}
                    )

            # Default markdown handling
            return FileClassification(
                file_type='markdown',
                processor='extract_entities.py',
                destination='clippings',
                metadata={'domain': 'general'}
            )

        # Image files
        if suffix in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            return FileClassification(
                file_type='image',
                processor='copy',
                destination='clippings',
                metadata={'original_name': name}
            )

        # Unknown file type
        return FileClassification(
            file_type='unknown',
            processor='copy',
            destination='clippings',
            metadata={'original_name': name}
        )

    def _extract_url_from_shortcut(self, filepath: Path) -> Optional[str]:
        """Extract URL from .url or .webloc file."""
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')

            # Windows .url format
            url_match = re.search(r'URL=(.+)', content)
            if url_match:
                return url_match.group(1).strip()

            # Try as plain URL
            url_match = self.URL_PATTERN.search(content)
            if url_match:
                return url_match.group(0)
        except Exception:
            pass
        return None

    def _parse_frontmatter(self, content: str) -> dict:
        """Parse YAML frontmatter from markdown content."""
        if not content.startswith('---'):
            return {}
        try:
            parts = content.split('---', 2)
            if len(parts) >= 3:
                return yaml.safe_load(parts[1]) or {}
        except Exception:
            pass
        return {}

    def process_file(self, filepath: Path, dry_run: bool = False) -> bool:
        """Process a single file in the inbox."""
        if self.should_ignore(filepath):
            return False

        if not filepath.is_file():
            return False

        classification = self.classify(filepath)
        dest_dir = self.inbox_path / classification.destination

        click.echo(f"Processing: {filepath.name}")
        click.echo(f"  Type: {classification.file_type}")
        click.echo(f"  Processor: {classification.processor}")
        click.echo(f"  Destination: {classification.destination}/")

        if dry_run:
            click.echo("  [DRY RUN - no action taken]")
            return True

        try:
            scripts_dir = self.vault_path / 'scripts'

            if classification.processor == 'copy':
                # Simple copy to destination
                dest_path = dest_dir / filepath.name
                shutil.copy2(filepath, dest_path)
                filepath.unlink()
                click.echo(f"  Copied to: {dest_path}")

            elif classification.processor == 'ingest_pdf.py':
                # Run PDF ingestion
                result = subprocess.run(
                    [sys.executable, str(scripts_dir / 'ingest_pdf.py'),
                     str(filepath), '--output-dir', str(dest_dir)],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    filepath.unlink()
                    click.echo(f"  PDF ingested successfully")
                else:
                    click.echo(f"  Error: {result.stderr}", err=True)
                    return False

            elif classification.processor == 'ingest_web.py':
                # Run web ingestion
                url = classification.metadata.get('url')
                if url:
                    result = subprocess.run(
                        [sys.executable, str(scripts_dir / 'ingest_web.py'),
                         url, '--output-dir', str(dest_dir)],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        filepath.unlink()
                        click.echo(f"  Web article ingested successfully")
                    else:
                        click.echo(f"  Error: {result.stderr}", err=True)
                        return False

            elif classification.processor == 'ingest_paper.py':
                # Run paper ingestion
                paper_id = classification.metadata.get('arxiv_id')
                if paper_id:
                    source = f"arxiv:{paper_id}"
                else:
                    doi = classification.metadata.get('doi')
                    if doi:
                        source = f"doi:{doi}"
                    else:
                        source = classification.metadata.get('url', '')

                if source:
                    result = subprocess.run(
                        [sys.executable, str(scripts_dir / 'ingest_paper.py'),
                         source, '--output-dir', str(dest_dir)],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        filepath.unlink()
                        click.echo(f"  Paper ingested successfully")
                    else:
                        click.echo(f"  Error: {result.stderr}", err=True)
                        return False

            elif classification.processor == 'extract_entities.py':
                # For markdown, move then run entity extraction
                dest_path = dest_dir / filepath.name
                shutil.move(str(filepath), str(dest_path))

                # Run entity extraction
                domain = classification.metadata.get('domain', 'general')
                result = subprocess.run(
                    [sys.executable, str(scripts_dir / 'extract_entities.py'),
                     str(dest_path), '--domain', domain, '--format', 'json'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    click.echo(f"  Moved and extracted entities")
                else:
                    click.echo(f"  Moved, but extraction warning: {result.stderr}")

            return True

        except Exception as e:
            click.echo(f"  Error processing: {e}", err=True)
            return False

    def process_inbox(self, dry_run: bool = False) -> tuple[int, int]:
        """Process all files in the inbox root directory."""
        processed = 0
        failed = 0

        # Only process files in root inbox, not subdirectories
        for filepath in self.inbox_path.iterdir():
            if filepath.is_file() and not self.should_ignore(filepath):
                if self.process_file(filepath, dry_run):
                    processed += 1
                else:
                    failed += 1

        return processed, failed

    def watch(self, interval: int = 5) -> None:
        """Watch inbox for new files and process them."""
        click.echo(f"Watching {self.inbox_path} for new files... (Ctrl+C to stop)")
        seen_files = set()

        try:
            while True:
                current_files = set(
                    f for f in self.inbox_path.iterdir()
                    if f.is_file() and not self.should_ignore(f)
                )

                new_files = current_files - seen_files
                for filepath in new_files:
                    # Wait a moment for file to finish writing
                    time.sleep(1)
                    self.process_file(filepath)

                seen_files = current_files
                time.sleep(interval)

        except KeyboardInterrupt:
            click.echo("\nStopped watching.")


@click.command()
@click.argument('file', type=click.Path(), required=False)
@click.option('--inbox', '-i', type=click.Path(exists=True),
              help='Path to inbox directory')
@click.option('--watch', '-w', is_flag=True, help='Watch for new files continuously')
@click.option('--dry-run', '-n', is_flag=True, help='Show what would be processed')
@click.option('--interval', default=5, help='Watch interval in seconds')
def main(file: Optional[str], inbox: Optional[str], watch: bool, dry_run: bool, interval: int):
    """Process files in the inbox directory.

    If FILE is provided, process only that file.
    Otherwise, process all files in the inbox.

    Examples:
        process_inbox.py                    # Process all inbox files
        process_inbox.py document.pdf       # Process specific file
        process_inbox.py --watch            # Watch for new files
        process_inbox.py --dry-run          # Preview what would happen
    """
    # Find vault and inbox paths
    vault_path = Path(__file__).parent.parent
    if inbox:
        inbox_path = Path(inbox)
    else:
        inbox_path = vault_path / '_inbox'

    if not inbox_path.exists():
        click.echo(f"Inbox directory not found: {inbox_path}", err=True)
        sys.exit(1)

    processor = InboxProcessor(inbox_path, vault_path)

    if file:
        # Process single file
        filepath = Path(file)
        if not filepath.exists():
            filepath = inbox_path / file
        if not filepath.exists():
            click.echo(f"File not found: {file}", err=True)
            sys.exit(1)
        processor.process_file(filepath, dry_run)

    elif watch:
        # Watch mode
        processor.watch(interval)

    else:
        # Process all inbox files
        processed, failed = processor.process_inbox(dry_run)
        click.echo(f"\nProcessed: {processed}, Failed: {failed}")


if __name__ == '__main__':
    main()
