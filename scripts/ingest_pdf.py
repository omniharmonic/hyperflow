#!/usr/bin/env python3
"""
PDF to Markdown ingestion for Hyperflow.

Converts PDF documents to markdown with:
- Extracted text with structure preservation
- Table detection and conversion
- Image extraction (optional)
- Rich frontmatter metadata
- Automatic content classification

Usage:
    # Ingest a single PDF
    python ingest_pdf.py document.pdf

    # Ingest to specific directory
    python ingest_pdf.py document.pdf --output _inbox/papers/

    # Batch ingest
    python ingest_pdf.py ~/Downloads/*.pdf --output _inbox/papers/

    # With automatic classification and routing
    python ingest_pdf.py document.pdf --auto-route
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import subprocess

import click
import yaml

# Optional imports
try:
    from rich.console import Console
    from rich.progress import Progress
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None

# Try to import marker for high-quality PDF conversion
MARKER_AVAILABLE = False
try:
    from marker.convert import convert_single_pdf
    from marker.models import load_all_models
    MARKER_AVAILABLE = True
except ImportError:
    pass

# Fallback to PyMuPDF for basic extraction
PYMUPDF_AVAILABLE = False
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    pass


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to URL-friendly slug."""
    # Remove special characters and convert to lowercase
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
    # Replace spaces with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    # Trim and limit length
    return slug.strip('-')[:max_length]


def extract_with_marker(pdf_path: Path) -> tuple[str, dict, list]:
    """Extract PDF content using marker (high quality)."""
    if not MARKER_AVAILABLE:
        raise RuntimeError("marker not installed. Run: pip install marker-pdf")

    models = load_all_models()
    full_text, images, metadata = convert_single_pdf(str(pdf_path), models)

    return full_text, metadata, images


def extract_with_pymupdf(pdf_path: Path) -> tuple[str, dict, list]:
    """Extract PDF content using PyMuPDF (fallback)."""
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF not installed. Run: pip install pymupdf")

    doc = fitz.open(str(pdf_path))

    # Extract text from all pages
    text_parts = []
    for page_num, page in enumerate(doc, 1):
        text = page.get_text("text")
        if text.strip():
            text_parts.append(f"<!-- Page {page_num} -->\n{text}")

    full_text = "\n\n".join(text_parts)

    # Build metadata
    metadata = {
        'title': doc.metadata.get('title', pdf_path.stem),
        'author': doc.metadata.get('author', ''),
        'subject': doc.metadata.get('subject', ''),
        'pages': len(doc),
        'created': doc.metadata.get('creationDate', ''),
    }

    doc.close()
    return full_text, metadata, []


def extract_with_pdftotext(pdf_path: Path) -> tuple[str, dict, list]:
    """Extract PDF content using pdftotext CLI (basic fallback)."""
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', str(pdf_path), '-'],
            capture_output=True,
            text=True,
            check=True
        )
        text = result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("pdftotext not available. Install poppler-utils or use pip install marker-pdf")

    # Try to get page count with pdfinfo
    try:
        info_result = subprocess.run(
            ['pdfinfo', str(pdf_path)],
            capture_output=True,
            text=True
        )
        pages = 0
        for line in info_result.stdout.split('\n'):
            if line.startswith('Pages:'):
                pages = int(line.split(':')[1].strip())
                break
    except:
        pages = 0

    metadata = {
        'title': pdf_path.stem,
        'pages': pages,
    }

    return text, metadata, []


def classify_pdf(text: str, metadata: dict) -> str:
    """Classify PDF type based on content analysis."""
    text_lower = text.lower()

    # Research paper indicators
    paper_indicators = ['abstract', 'introduction', 'methodology', 'conclusion',
                       'references', 'bibliography', 'et al.', 'doi:']
    paper_score = sum(1 for ind in paper_indicators if ind in text_lower)

    # Book indicators
    book_indicators = ['chapter', 'table of contents', 'preface', 'foreword']
    book_score = sum(1 for ind in book_indicators if ind in text_lower)

    # Technical documentation
    doc_indicators = ['api', 'function', 'method', 'parameter', 'returns',
                     'example', 'usage', 'installation']
    doc_score = sum(1 for ind in doc_indicators if ind in text_lower)

    # Financial/business
    business_indicators = ['revenue', 'profit', 'quarterly', 'fiscal',
                          'shareholders', 'balance sheet']
    business_score = sum(1 for ind in business_indicators if ind in text_lower)

    # Determine type
    scores = {
        'research_paper': paper_score,
        'book': book_score,
        'documentation': doc_score,
        'business_report': business_score,
    }

    # Check page count
    pages = metadata.get('pages', 0)
    if pages > 100:
        scores['book'] += 2
    elif pages < 20:
        scores['research_paper'] += 1

    best_type = max(scores, key=scores.get)
    if scores[best_type] >= 2:
        return best_type

    return 'document'


def generate_frontmatter(pdf_path: Path, metadata: dict, content_type: str) -> dict:
    """Generate YAML frontmatter for the markdown file."""
    now = datetime.now()

    frontmatter = {
        'title': metadata.get('title', pdf_path.stem).strip() or pdf_path.stem,
        'date': now.isoformat(),
        'source': 'pdf',
        'source_file': str(pdf_path.absolute()),
        'status': 'pending_enrichment',
        'content_type': content_type,
        'pages': metadata.get('pages', 0),
        'tags': ['pdf', 'imported', content_type.replace('_', '-')],
    }

    # Add optional metadata
    if metadata.get('author'):
        frontmatter['author'] = metadata['author']
    if metadata.get('subject'):
        frontmatter['subject'] = metadata['subject']

    return frontmatter


def save_images(images: list, output_dir: Path, slug: str) -> list[str]:
    """Save extracted images and return relative paths."""
    if not images:
        return []

    img_dir = output_dir / "attachments" / slug
    img_dir.mkdir(parents=True, exist_ok=True)

    image_paths = []
    for i, img in enumerate(images):
        img_path = img_dir / f"image_{i:03d}.png"
        if hasattr(img, 'save'):
            img.save(str(img_path))
        elif isinstance(img, bytes):
            img_path.write_bytes(img)
        image_paths.append(f"attachments/{slug}/image_{i:03d}.png")

    return image_paths


def get_route_directory(content_type: str, base_dir: Path) -> Path:
    """Determine output directory based on content type."""
    routes = {
        'research_paper': base_dir / '_inbox' / 'papers',
        'book': base_dir / '_inbox' / 'papers',
        'documentation': base_dir / '_inbox' / 'articles',
        'business_report': base_dir / '_inbox' / 'articles',
        'document': base_dir / '_inbox' / 'papers',
    }
    return routes.get(content_type, base_dir / '_inbox' / 'papers')


@click.command()
@click.argument('pdf_files', nargs=-1, type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--auto-route', is_flag=True, help='Automatically route based on content type')
@click.option('--extract-images', is_flag=True, help='Extract and save images from PDF')
@click.option('--method', type=click.Choice(['auto', 'marker', 'pymupdf', 'pdftotext']),
              default='auto', help='Extraction method to use')
def main(pdf_files: tuple, output: Optional[str], auto_route: bool,
         extract_images: bool, method: str):
    """Convert PDF files to markdown with metadata.

    PDF_FILES: One or more PDF files to convert.

    Examples:
        ingest_pdf.py document.pdf
        ingest_pdf.py *.pdf --output _inbox/papers/
        ingest_pdf.py paper.pdf --auto-route --extract-images
    """
    if not pdf_files:
        click.echo("No PDF files specified.", err=True)
        sys.exit(1)

    # Determine extraction method
    if method == 'auto':
        if MARKER_AVAILABLE:
            method = 'marker'
        elif PYMUPDF_AVAILABLE:
            method = 'pymupdf'
        else:
            method = 'pdftotext'

    click.echo(f"Using extraction method: {method}")

    # Get extraction function
    extractors = {
        'marker': extract_with_marker,
        'pymupdf': extract_with_pymupdf,
        'pdftotext': extract_with_pdftotext,
    }
    extract_fn = extractors[method]

    # Determine base output directory
    if output:
        output_dir = Path(output)
    else:
        output_dir = Path.cwd() / '_inbox' / 'papers'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each PDF
    results = []
    for pdf_file in pdf_files:
        pdf_path = Path(pdf_file)
        click.echo(f"\nProcessing: {pdf_path.name}")

        try:
            # Extract content
            full_text, metadata, images = extract_fn(pdf_path)

            # Classify content
            content_type = classify_pdf(full_text, metadata)
            click.echo(f"  Classified as: {content_type}")

            # Determine output directory
            if auto_route:
                final_output_dir = get_route_directory(content_type, Path.cwd())
            else:
                final_output_dir = output_dir

            final_output_dir.mkdir(parents=True, exist_ok=True)

            # Generate output filename
            slug = slugify(metadata.get('title', pdf_path.stem))
            date_prefix = datetime.now().strftime('%Y-%m-%d')
            output_filename = f"{date_prefix}_{slug}.md"
            output_path = final_output_dir / output_filename

            # Handle duplicate filenames
            counter = 1
            while output_path.exists():
                output_filename = f"{date_prefix}_{slug}_{counter}.md"
                output_path = final_output_dir / output_filename
                counter += 1

            # Generate frontmatter
            frontmatter = generate_frontmatter(pdf_path, metadata, content_type)

            # Save images if requested
            if extract_images and images:
                image_paths = save_images(images, final_output_dir, slug)
                frontmatter['images'] = image_paths
                click.echo(f"  Extracted {len(image_paths)} images")

            # Build markdown content
            md_content = "---\n"
            md_content += yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
            md_content += "---\n\n"
            md_content += f"# {frontmatter['title']}\n\n"

            # Add source reference
            md_content += f"> Imported from: `{pdf_path.name}` ({metadata.get('pages', '?')} pages)\n\n"

            # Add content
            md_content += full_text

            # Write output
            output_path.write_text(md_content, encoding='utf-8')
            click.echo(f"  Created: {output_path}")

            results.append({
                'source': str(pdf_path),
                'output': str(output_path),
                'type': content_type,
                'pages': metadata.get('pages', 0),
            })

        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            continue

    # Summary
    click.echo(f"\n{'='*50}")
    click.echo(f"Processed {len(results)} of {len(pdf_files)} PDFs")
    for r in results:
        click.echo(f"  [{r['type']}] {Path(r['output']).name}")


if __name__ == '__main__':
    main()
