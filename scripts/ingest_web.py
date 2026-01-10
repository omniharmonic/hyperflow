#!/usr/bin/env python3
"""
Web content ingestion for Hyperflow using Jina Reader API.

Converts web pages to clean markdown with:
- Main content extraction (removes ads, navigation, etc.)
- Metadata extraction (title, author, date)
- Automatic content classification
- Rich frontmatter

Usage:
    # Ingest a single URL
    python ingest_web.py "https://example.com/article"

    # Ingest multiple URLs
    python ingest_web.py url1 url2 url3

    # Ingest from file containing URLs
    python ingest_web.py --file urls.txt

    # Custom output directory
    python ingest_web.py "https://..." --output _inbox/articles/
"""

import re
import sys
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
    print("Warning: httpx not installed. Run: pip install httpx")

try:
    from rich.console import Console
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None


# Jina Reader API base URL
JINA_READER_BASE = "https://r.jina.ai/"
JINA_SEARCH_BASE = "https://s.jina.ai/"


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to URL-friendly slug."""
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:max_length]


def fetch_with_jina(url: str, api_key: Optional[str] = None) -> tuple[str, dict]:
    """Fetch URL content using Jina Reader API."""
    if not HTTPX_AVAILABLE:
        raise RuntimeError("httpx not installed. Run: pip install httpx")

    headers = {
        "Accept": "text/markdown",
        "X-Return-Format": "markdown",
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Jina Reader: prepend r.jina.ai/ to any URL
    reader_url = f"{JINA_READER_BASE}{url}"

    try:
        response = httpx.get(reader_url, headers=headers, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        content = response.text
    except httpx.TimeoutException:
        raise RuntimeError(f"Timeout fetching URL: {url}")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error {e.response.status_code}: {url}")

    # Extract metadata from response headers or content
    metadata = parse_jina_response(content, url)

    return content, metadata


def fetch_with_requests(url: str) -> tuple[str, dict]:
    """Fallback: fetch raw HTML and do basic extraction."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("For fallback mode, install: pip install requests beautifulsoup4")

    response = requests.get(url, timeout=30, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; Hyperflow/1.0)'
    })
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # Remove script and style elements
    for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
        element.decompose()

    # Get title
    title = soup.find('title')
    title_text = title.get_text().strip() if title else urlparse(url).netloc

    # Get main content
    main = soup.find('main') or soup.find('article') or soup.find('body')
    content = main.get_text(separator='\n\n') if main else soup.get_text()

    # Clean up whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)

    metadata = {
        'title': title_text,
        'url': url,
    }

    return content, metadata


def parse_jina_response(content: str, url: str) -> dict:
    """Parse Jina Reader response to extract metadata."""
    metadata = {
        'url': url,
        'title': '',
        'author': None,
        'published': None,
        'description': None,
    }

    lines = content.split('\n')

    # Jina often includes title as first # heading
    for line in lines[:10]:
        if line.startswith('# '):
            metadata['title'] = line[2:].strip()
            break

    # Look for metadata in content
    for line in lines[:30]:
        line_lower = line.lower()
        if 'author:' in line_lower or 'by ' in line_lower[:10]:
            # Extract author
            match = re.search(r'(?:author:|by\s+)([^|,\n]+)', line, re.IGNORECASE)
            if match:
                metadata['author'] = match.group(1).strip()
        elif re.match(r'^\d{4}-\d{2}-\d{2}', line):
            metadata['published'] = line.strip()[:10]

    # Fallback title from URL
    if not metadata['title']:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if path:
            metadata['title'] = path.split('/')[-1].replace('-', ' ').replace('_', ' ').title()
        else:
            metadata['title'] = parsed.netloc

    return metadata


def classify_url(url: str, content: str) -> str:
    """Classify content type based on URL and content analysis."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()
    content_lower = content.lower()[:2000]

    # Research/academic
    if any(d in domain for d in ['arxiv', 'doi.org', 'scholar.google', 'pubmed',
                                  'researchgate', 'academia.edu', 'ssrn']):
        return 'research'

    # Documentation
    if any(d in domain for d in ['docs.', 'documentation', 'developer.',
                                  'readme.io', 'gitbook.io']) or '/docs/' in path:
        return 'documentation'

    # Blog/newsletter
    if any(d in domain for d in ['blog', 'medium.com', 'substack.com', 'dev.to',
                                  'hashnode', 'wordpress']):
        return 'blog'

    # News
    if any(d in domain for d in ['news', 'bbc', 'cnn', 'nytimes', 'reuters',
                                  'theguardian', 'techcrunch', 'verge']):
        return 'news'

    # Reference
    if any(d in domain for d in ['wikipedia', 'wiki', 'britannica']):
        return 'reference'

    # GitHub/code
    if 'github.com' in domain or 'gitlab.com' in domain:
        if '/blob/' in path or '/tree/' in path:
            return 'code'
        else:
            return 'documentation'

    # Video (won't have much content)
    if any(d in domain for d in ['youtube', 'vimeo', 'twitch']):
        return 'video'

    # Default: analyze content
    if any(term in content_lower for term in ['abstract', 'methodology', 'conclusion']):
        return 'research'
    if any(term in content_lower for term in ['tutorial', 'how to', 'step 1', 'step 2']):
        return 'tutorial'

    return 'article'


def generate_frontmatter(url: str, metadata: dict, content_type: str) -> dict:
    """Generate YAML frontmatter for the markdown file."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '')

    frontmatter = {
        'title': metadata.get('title', 'Untitled'),
        'date': datetime.now().isoformat(),
        'source': 'web',
        'source_url': url,
        'domain': domain,
        'status': 'pending_enrichment',
        'content_type': content_type,
        'tags': ['web', 'imported', content_type, domain.split('.')[0]],
    }

    if metadata.get('author'):
        frontmatter['author'] = metadata['author']
    if metadata.get('published'):
        frontmatter['published'] = metadata['published']
    if metadata.get('description'):
        frontmatter['description'] = metadata['description']

    return frontmatter


def get_output_directory(content_type: str, base_dir: Path) -> Path:
    """Determine output directory based on content type."""
    routes = {
        'research': base_dir / '_inbox' / 'papers',
        'documentation': base_dir / '_inbox' / 'articles',
        'blog': base_dir / '_inbox' / 'articles',
        'news': base_dir / '_inbox' / 'articles',
        'reference': base_dir / '_inbox' / 'articles',
        'tutorial': base_dir / '_inbox' / 'articles',
        'article': base_dir / '_inbox' / 'articles',
        'code': base_dir / '_inbox' / 'articles',
        'video': base_dir / '_inbox' / 'clippings',
    }
    return routes.get(content_type, base_dir / '_inbox' / 'articles')


@click.command()
@click.argument('urls', nargs=-1)
@click.option('--file', '-f', 'url_file', type=click.Path(exists=True),
              help='File containing URLs (one per line)')
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--auto-route', is_flag=True, help='Automatically route based on content type')
@click.option('--api-key', envvar='JINA_API_KEY', help='Jina Reader API key (optional)')
@click.option('--method', type=click.Choice(['jina', 'requests']), default='jina',
              help='Extraction method')
def main(urls: tuple, url_file: Optional[str], output: Optional[str],
         auto_route: bool, api_key: Optional[str], method: str):
    """Convert web pages to markdown files.

    URLS: One or more URLs to convert.

    Examples:
        ingest_web.py "https://example.com/article"
        ingest_web.py --file urls.txt --output _inbox/articles/
        ingest_web.py url1 url2 --auto-route
    """
    # Collect URLs
    all_urls = list(urls)

    if url_file:
        file_urls = Path(url_file).read_text().strip().split('\n')
        all_urls.extend(u.strip() for u in file_urls if u.strip() and not u.startswith('#'))

    if not all_urls:
        click.echo("No URLs specified. Use --file or provide URLs as arguments.", err=True)
        sys.exit(1)

    # Determine output directory
    if output:
        output_dir = Path(output)
    else:
        output_dir = Path.cwd() / '_inbox' / 'articles'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Select fetch method
    if method == 'jina':
        fetch_fn = lambda u: fetch_with_jina(u, api_key)
    else:
        fetch_fn = fetch_with_requests

    click.echo(f"Using method: {method}")

    # Process each URL
    results = []
    for url in all_urls:
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        click.echo(f"\nFetching: {url}")

        try:
            # Fetch content
            content, metadata = fetch_fn(url)

            # Classify content
            content_type = classify_url(url, content)
            click.echo(f"  Classified as: {content_type}")

            # Determine output directory
            if auto_route:
                final_output_dir = get_output_directory(content_type, Path.cwd())
            else:
                final_output_dir = output_dir

            final_output_dir.mkdir(parents=True, exist_ok=True)

            # Generate output filename
            slug = slugify(metadata.get('title', 'untitled'))
            date_prefix = datetime.now().strftime('%Y-%m-%d')
            output_filename = f"{date_prefix}_{slug}.md"
            output_path = final_output_dir / output_filename

            # Handle duplicates
            counter = 1
            while output_path.exists():
                output_filename = f"{date_prefix}_{slug}_{counter}.md"
                output_path = final_output_dir / output_filename
                counter += 1

            # Generate frontmatter
            frontmatter = generate_frontmatter(url, metadata, content_type)

            # Build markdown
            md_content = "---\n"
            md_content += yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
            md_content += "---\n\n"

            # Add title if not already in content
            if not content.strip().startswith('# '):
                md_content += f"# {frontmatter['title']}\n\n"

            # Add source reference
            md_content += f"> Source: [{url}]({url})\n\n"

            # Add content
            md_content += content

            # Write output
            output_path.write_text(md_content, encoding='utf-8')
            click.echo(f"  Created: {output_path}")

            results.append({
                'url': url,
                'output': str(output_path),
                'type': content_type,
                'title': frontmatter['title'],
            })

        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            continue

    # Summary
    click.echo(f"\n{'='*50}")
    click.echo(f"Processed {len(results)} of {len(all_urls)} URLs")
    for r in results:
        click.echo(f"  [{r['type']}] {r['title'][:40]}...")


if __name__ == '__main__':
    main()
