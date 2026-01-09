#!/usr/bin/env python3
"""
Academic paper ingestion for Hyperflow.

Supports:
- arXiv papers (by ID or URL)
- DOI resolution
- Semantic Scholar lookup
- Direct PDF URLs

Features:
- Automatic metadata extraction (authors, abstract, citations)
- PDF download and conversion
- BibTeX generation
- Rich frontmatter

Usage:
    # Ingest from arXiv
    python ingest_paper.py arxiv:2301.00001
    python ingest_paper.py "https://arxiv.org/abs/2301.00001"

    # Ingest from DOI
    python ingest_paper.py doi:10.1234/example

    # Ingest from Semantic Scholar
    python ingest_paper.py s2:649def34f8be52c8b66281af98ae884c09aef38b

    # Direct PDF URL
    python ingest_paper.py "https://example.com/paper.pdf"
"""

import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import click
import yaml

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import arxiv
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False

try:
    from rich.console import Console
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to URL-friendly slug."""
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:max_length]


def parse_paper_reference(ref: str) -> tuple[str, str]:
    """Parse paper reference into (type, id).

    Returns:
        (type, identifier) where type is one of: arxiv, doi, s2, url
    """
    ref = ref.strip()

    # arXiv reference
    if ref.startswith('arxiv:'):
        return ('arxiv', ref[6:])
    if 'arxiv.org' in ref:
        # Extract ID from URL
        match = re.search(r'arxiv\.org/(?:abs|pdf)/([0-9.]+)', ref)
        if match:
            return ('arxiv', match.group(1))

    # DOI reference
    if ref.startswith('doi:'):
        return ('doi', ref[4:])
    if ref.startswith('10.'):
        return ('doi', ref)
    if 'doi.org' in ref:
        match = re.search(r'doi\.org/(10\.[^/\s]+/.+)', ref)
        if match:
            return ('doi', match.group(1))

    # Semantic Scholar
    if ref.startswith('s2:'):
        return ('s2', ref[3:])
    if 'semanticscholar.org' in ref:
        match = re.search(r'/paper/[^/]+/([a-f0-9]+)', ref)
        if match:
            return ('s2', match.group(1))

    # Direct URL (probably PDF)
    if ref.startswith(('http://', 'https://')):
        return ('url', ref)

    # Unknown format
    return ('unknown', ref)


def fetch_arxiv_paper(arxiv_id: str) -> dict:
    """Fetch paper metadata from arXiv."""
    if not ARXIV_AVAILABLE:
        raise RuntimeError("arxiv package not installed. Run: pip install arxiv")

    client = arxiv.Client()
    search = arxiv.Search(id_list=[arxiv_id])

    try:
        paper = next(client.results(search))
    except StopIteration:
        raise ValueError(f"arXiv paper not found: {arxiv_id}")

    return {
        'title': paper.title,
        'authors': [a.name for a in paper.authors],
        'abstract': paper.summary,
        'published': paper.published.isoformat() if paper.published else None,
        'updated': paper.updated.isoformat() if paper.updated else None,
        'categories': list(paper.categories),
        'doi': paper.doi,
        'pdf_url': paper.pdf_url,
        'arxiv_id': paper.entry_id,
        'arxiv_url': f"https://arxiv.org/abs/{arxiv_id}",
        'source_type': 'arxiv',
    }


def fetch_doi_paper(doi: str) -> dict:
    """Fetch paper metadata from CrossRef via DOI."""
    if not HTTPX_AVAILABLE:
        raise RuntimeError("httpx not installed. Run: pip install httpx")

    url = f"https://api.crossref.org/works/{doi}"
    headers = {'Accept': 'application/json'}

    response = httpx.get(url, headers=headers, timeout=30.0)
    response.raise_for_status()

    data = response.json()['message']

    # Extract authors
    authors = []
    for author in data.get('author', []):
        name = f"{author.get('given', '')} {author.get('family', '')}".strip()
        if name:
            authors.append(name)

    # Extract publication date
    published = None
    if 'published-print' in data:
        parts = data['published-print'].get('date-parts', [[]])[0]
        if len(parts) >= 1:
            published = f"{parts[0]}"
            if len(parts) >= 2:
                published += f"-{parts[1]:02d}"
            if len(parts) >= 3:
                published += f"-{parts[2]:02d}"

    return {
        'title': data.get('title', [''])[0],
        'authors': authors,
        'abstract': data.get('abstract', ''),
        'published': published,
        'doi': doi,
        'doi_url': f"https://doi.org/{doi}",
        'journal': data.get('container-title', [''])[0],
        'publisher': data.get('publisher', ''),
        'source_type': 'doi',
    }


def fetch_semantic_scholar_paper(paper_id: str) -> dict:
    """Fetch paper metadata from Semantic Scholar."""
    if not HTTPX_AVAILABLE:
        raise RuntimeError("httpx not installed. Run: pip install httpx")

    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
    params = {
        'fields': 'title,authors,abstract,year,venue,openAccessPdf,externalIds,citationCount'
    }

    response = httpx.get(url, params=params, timeout=30.0)
    response.raise_for_status()

    data = response.json()

    return {
        'title': data.get('title', ''),
        'authors': [a['name'] for a in data.get('authors', [])],
        'abstract': data.get('abstract', ''),
        'published': str(data.get('year', '')),
        'venue': data.get('venue', ''),
        'citation_count': data.get('citationCount', 0),
        'pdf_url': data.get('openAccessPdf', {}).get('url'),
        'doi': data.get('externalIds', {}).get('DOI'),
        'arxiv_id': data.get('externalIds', {}).get('ArXiv'),
        's2_id': paper_id,
        's2_url': f"https://www.semanticscholar.org/paper/{paper_id}",
        'source_type': 's2',
    }


def download_pdf(url: str, output_path: Path) -> bool:
    """Download PDF from URL."""
    if not HTTPX_AVAILABLE:
        raise RuntimeError("httpx not installed. Run: pip install httpx")

    try:
        response = httpx.get(url, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        output_path.write_bytes(response.content)
        return True
    except Exception as e:
        click.echo(f"  Warning: Could not download PDF: {e}", err=True)
        return False


def convert_pdf_to_text(pdf_path: Path) -> str:
    """Convert PDF to text using available tools."""
    # Try pdftotext first (fast)
    try:
        import subprocess
        result = subprocess.run(
            ['pdftotext', '-layout', str(pdf_path), '-'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except:
        pass

    # Try PyMuPDF
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        text = '\n\n'.join(page.get_text() for page in doc)
        doc.close()
        return text
    except:
        pass

    return ""


def generate_bibtex(metadata: dict) -> str:
    """Generate BibTeX entry for the paper."""
    # Create citation key
    first_author = metadata['authors'][0].split()[-1] if metadata['authors'] else 'unknown'
    year = metadata.get('published', '')[:4] if metadata.get('published') else 'nd'
    title_word = slugify(metadata.get('title', 'paper').split()[0])
    cite_key = f"{first_author.lower()}{year}{title_word}"

    # Build BibTeX
    bibtex = f"@article{{{cite_key},\n"
    bibtex += f"  title = {{{metadata.get('title', '')}}},\n"
    bibtex += f"  author = {{{' and '.join(metadata.get('authors', []))}}},\n"

    if metadata.get('published'):
        bibtex += f"  year = {{{metadata['published'][:4]}}},\n"
    if metadata.get('journal'):
        bibtex += f"  journal = {{{metadata['journal']}}},\n"
    if metadata.get('doi'):
        bibtex += f"  doi = {{{metadata['doi']}}},\n"
    if metadata.get('arxiv_id'):
        bibtex += f"  eprint = {{{metadata['arxiv_id']}}},\n"
        bibtex += f"  archiveprefix = {{arXiv}},\n"

    bibtex += "}\n"
    return bibtex


def generate_frontmatter(metadata: dict) -> dict:
    """Generate YAML frontmatter for the paper."""
    frontmatter = {
        'title': metadata.get('title', 'Untitled Paper'),
        'date': datetime.now().isoformat(),
        'source': 'paper',
        'source_type': metadata.get('source_type', 'unknown'),
        'status': 'pending_enrichment',
        'content_type': 'research_paper',
        'authors': metadata.get('authors', []),
        'tags': ['paper', 'research', 'imported'],
    }

    # Add optional fields
    if metadata.get('published'):
        frontmatter['published'] = metadata['published']
    if metadata.get('doi'):
        frontmatter['doi'] = metadata['doi']
    if metadata.get('arxiv_id'):
        frontmatter['arxiv_id'] = metadata['arxiv_id']
    if metadata.get('journal'):
        frontmatter['journal'] = metadata['journal']
    if metadata.get('venue'):
        frontmatter['venue'] = metadata['venue']
    if metadata.get('citation_count'):
        frontmatter['citations'] = metadata['citation_count']
    if metadata.get('categories'):
        frontmatter['categories'] = metadata['categories']
        # Add first category as tag
        if metadata['categories']:
            frontmatter['tags'].append(metadata['categories'][0].lower())

    # Add source URLs
    urls = {}
    if metadata.get('arxiv_url'):
        urls['arxiv'] = metadata['arxiv_url']
    if metadata.get('doi_url'):
        urls['doi'] = metadata['doi_url']
    if metadata.get('s2_url'):
        urls['semantic_scholar'] = metadata['s2_url']
    if metadata.get('pdf_url'):
        urls['pdf'] = metadata['pdf_url']
    if urls:
        frontmatter['source_urls'] = urls

    return frontmatter


@click.command()
@click.argument('references', nargs=-1)
@click.option('--output', '-o', type=click.Path(), default='_inbox/papers',
              help='Output directory')
@click.option('--download-pdf', is_flag=True, help='Download PDF if available')
@click.option('--include-text', is_flag=True, help='Include extracted PDF text in markdown')
@click.option('--bibtex', is_flag=True, help='Generate BibTeX file alongside markdown')
def main(references: tuple, output: str, download_pdf: bool,
         include_text: bool, bibtex: bool):
    """Ingest academic papers from various sources.

    REFERENCES can be:
    - arXiv IDs: arxiv:2301.00001
    - DOIs: doi:10.1234/example
    - Semantic Scholar IDs: s2:649def34...
    - URLs: https://arxiv.org/abs/...

    Examples:
        ingest_paper.py arxiv:2301.00001
        ingest_paper.py doi:10.1038/nature12373
        ingest_paper.py arxiv:2301.00001 doi:10.1234/example --download-pdf
    """
    if not references:
        click.echo("No paper references provided.", err=True)
        sys.exit(1)

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for ref in references:
        click.echo(f"\nProcessing: {ref}")

        try:
            # Parse reference
            ref_type, ref_id = parse_paper_reference(ref)
            click.echo(f"  Type: {ref_type}, ID: {ref_id}")

            # Fetch metadata
            if ref_type == 'arxiv':
                metadata = fetch_arxiv_paper(ref_id)
            elif ref_type == 'doi':
                metadata = fetch_doi_paper(ref_id)
            elif ref_type == 's2':
                metadata = fetch_semantic_scholar_paper(ref_id)
            elif ref_type == 'url':
                # Direct URL - try to extract as PDF
                click.echo("  Direct URL - will attempt PDF download")
                metadata = {
                    'title': Path(urlparse(ref_id).path).stem,
                    'authors': [],
                    'abstract': '',
                    'pdf_url': ref_id,
                    'source_type': 'url',
                }
            else:
                click.echo(f"  Unknown reference type: {ref_type}", err=True)
                continue

            click.echo(f"  Title: {metadata.get('title', 'Unknown')[:60]}...")
            click.echo(f"  Authors: {', '.join(metadata.get('authors', [])[:3])}...")

            # Generate output filename
            slug = slugify(metadata.get('title', 'paper'))
            date_prefix = datetime.now().strftime('%Y-%m-%d')
            output_filename = f"{date_prefix}_{slug}.md"
            output_path = output_dir / output_filename

            # Handle duplicates
            counter = 1
            while output_path.exists():
                output_filename = f"{date_prefix}_{slug}_{counter}.md"
                output_path = output_dir / output_filename
                counter += 1

            # Download PDF if requested
            pdf_text = ""
            if download_pdf and metadata.get('pdf_url'):
                pdf_path = output_dir / f"{date_prefix}_{slug}.pdf"
                click.echo(f"  Downloading PDF...")
                if download_pdf(metadata['pdf_url'], pdf_path):
                    click.echo(f"  PDF saved: {pdf_path.name}")
                    if include_text:
                        pdf_text = convert_pdf_to_text(pdf_path)
                        click.echo(f"  Extracted {len(pdf_text)} characters from PDF")

            # Generate frontmatter
            frontmatter = generate_frontmatter(metadata)

            # Build markdown content
            md_content = "---\n"
            md_content += yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
            md_content += "---\n\n"

            md_content += f"# {metadata.get('title', 'Untitled')}\n\n"

            # Authors
            if metadata.get('authors'):
                md_content += f"**Authors:** {', '.join(metadata['authors'])}\n\n"

            # Publication info
            pub_info = []
            if metadata.get('published'):
                pub_info.append(f"Published: {metadata['published']}")
            if metadata.get('journal'):
                pub_info.append(f"Journal: {metadata['journal']}")
            if metadata.get('venue'):
                pub_info.append(f"Venue: {metadata['venue']}")
            if pub_info:
                md_content += f"*{' | '.join(pub_info)}*\n\n"

            # Links
            links = []
            if metadata.get('arxiv_url'):
                links.append(f"[arXiv]({metadata['arxiv_url']})")
            if metadata.get('doi'):
                links.append(f"[DOI](https://doi.org/{metadata['doi']})")
            if metadata.get('pdf_url'):
                links.append(f"[PDF]({metadata['pdf_url']})")
            if metadata.get('s2_url'):
                links.append(f"[Semantic Scholar]({metadata['s2_url']})")
            if links:
                md_content += f"**Links:** {' | '.join(links)}\n\n"

            # Abstract
            if metadata.get('abstract'):
                md_content += "## Abstract\n\n"
                md_content += metadata['abstract'] + "\n\n"

            # PDF text if extracted
            if pdf_text:
                md_content += "## Full Text\n\n"
                md_content += pdf_text + "\n"

            # Notes section
            md_content += "## Notes\n\n"
            md_content += "*Add your notes here...*\n"

            # Write markdown
            output_path.write_text(md_content, encoding='utf-8')
            click.echo(f"  Created: {output_path}")

            # Generate BibTeX if requested
            if bibtex:
                bibtex_content = generate_bibtex(metadata)
                bibtex_path = output_path.with_suffix('.bib')
                bibtex_path.write_text(bibtex_content, encoding='utf-8')
                click.echo(f"  BibTeX: {bibtex_path}")

            results.append({
                'ref': ref,
                'output': str(output_path),
                'title': metadata.get('title', ''),
                'source_type': metadata.get('source_type', 'unknown'),
            })

        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            continue

    # Summary
    click.echo(f"\n{'='*50}")
    click.echo(f"Processed {len(results)} of {len(references)} papers")
    for r in results:
        click.echo(f"  [{r['source_type']}] {r['title'][:50]}...")


if __name__ == '__main__':
    main()
