#!/usr/bin/env python3
"""
Multi-platform static site publishing for Hyperflow.

Supports:
- Quartz (Obsidian-native, best graph view)
- Jekyll Garden (simple, great with Netlify)
- Eleventy (fast, flexible)
- Gatsby KB (rich interactivity)

Features:
- Privacy filtering (only publish #public content)
- Wikilink conversion for each platform
- Automatic frontmatter normalization
- Multiple deployment targets

Usage:
    # Build with Quartz
    python publish_site.py build --framework quartz

    # Build and deploy to GitHub Pages
    python publish_site.py deploy --framework quartz --target github-pages

    # Build with Jekyll for Netlify
    python publish_site.py build --framework jekyll

    # Preview locally
    python publish_site.py preview --framework quartz --port 8080
"""

import re
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import click
import yaml

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None


class SitePublisher(ABC):
    """Base class for static site publishers."""

    def __init__(self, vault_path: Path, site_path: Path):
        self.vault_path = vault_path
        self.site_path = site_path

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this publisher."""
        pass

    @abstractmethod
    def get_content_path(self) -> Path:
        """Return the content directory for this framework."""
        pass

    @abstractmethod
    def build(self) -> bool:
        """Build the static site. Returns success status."""
        pass

    @abstractmethod
    def preview(self, port: int = 8080) -> None:
        """Start local preview server."""
        pass

    @abstractmethod
    def deploy(self, target: str) -> bool:
        """Deploy to hosting platform. Returns success status."""
        pass

    def publish(self,
                include_patterns: Optional[list[str]] = None,
                exclude_patterns: Optional[list[str]] = None,
                public_only: bool = True) -> int:
        """Copy files and build site. Returns count of files copied."""
        content_path = self.get_content_path()

        # Clear and recreate content directory
        if content_path.exists():
            shutil.rmtree(content_path)
        content_path.mkdir(parents=True)

        # Copy eligible files
        copied = self._copy_files(content_path, include_patterns,
                                   exclude_patterns, public_only)
        click.echo(f"Copied {len(copied)} files to {content_path}")

        return len(copied)

    def _copy_files(self,
                    dest_root: Path,
                    include: Optional[list[str]],
                    exclude: Optional[list[str]],
                    public_only: bool) -> list[Path]:
        """Copy files matching criteria with privacy filtering."""
        copied = []

        default_include = [
            "projects/**/*.md",
            "concepts/**/*.md",
            "people/**/*.md",
            "index.md",
            "README.md",
        ]
        default_exclude = [
            "_*/**",           # _inbox, _templates, _drafts
            ".*/**",           # .claude, .obsidian, .vscode
            "**/PROJECT.md",   # Project config files
            "**/*private*",    # Anything with 'private' in name
            "**/*personal*",   # Anything with 'personal' in name
            "**/attachments/**/*.pdf",  # Don't copy PDFs
        ]

        include = include or default_include
        exclude = exclude or default_exclude

        for pattern in include:
            for file in self.vault_path.glob(pattern):
                if self._should_exclude(file, exclude):
                    continue
                if public_only and not self._is_public(file):
                    continue

                rel_path = file.relative_to(self.vault_path)
                dest = dest_root / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)

                content = self._process_for_publish(file)
                dest.write_text(content, encoding='utf-8')
                copied.append(dest)

        return copied

    def _is_public(self, file: Path) -> bool:
        """Check if file is marked as public."""
        try:
            content = file.read_text(encoding='utf-8')
            if not content.startswith('---'):
                return False

            # Parse frontmatter
            parts = content.split('---', 2)
            if len(parts) < 3:
                return False

            frontmatter = yaml.safe_load(parts[1])
            if not frontmatter:
                return False

            # Check for public flag or tag
            if frontmatter.get('public', False):
                return True
            if 'public' in frontmatter.get('tags', []):
                return True

            return False
        except Exception:
            return False

    def _should_exclude(self, file: Path, patterns: list[str]) -> bool:
        """Check if file matches any exclude pattern."""
        rel_path = str(file.relative_to(self.vault_path))
        for pattern in patterns:
            if file.match(pattern):
                return True
            # Also check relative path
            if Path(rel_path).match(pattern):
                return True
        return False

    def _process_for_publish(self, file: Path) -> str:
        """Process file content for publishing."""
        content = file.read_text(encoding='utf-8')

        # Remove private sections
        content = re.sub(
            r'<!--\s*private\s*-->.*?<!--\s*/private\s*-->',
            '', content, flags=re.DOTALL
        )

        # Remove private YAML blocks
        content = re.sub(
            r'```private\n.*?```',
            '', content, flags=re.DOTALL
        )

        # Convert wikilinks for this platform
        content = self._convert_wikilinks(content)

        return content

    def _convert_wikilinks(self, content: str) -> str:
        """Convert wikilinks to platform-specific format. Override in subclasses."""
        return content


class QuartzPublisher(SitePublisher):
    """Quartz 4.x publisher - best for Obsidian-style vaults."""

    @property
    def name(self) -> str:
        return "Quartz"

    def get_content_path(self) -> Path:
        return self.site_path / "content"

    def build(self) -> bool:
        """Build Quartz site."""
        try:
            result = subprocess.run(
                ["npx", "quartz", "build"],
                cwd=self.site_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                click.echo(f"Build error: {result.stderr}", err=True)
                return False
            return True
        except FileNotFoundError:
            click.echo("Error: npx not found. Install Node.js first.", err=True)
            return False

    def preview(self, port: int = 8080) -> None:
        """Start Quartz preview server."""
        click.echo(f"Starting Quartz preview on port {port}...")
        subprocess.run(
            ["npx", "quartz", "build", "--serve", "--port", str(port)],
            cwd=self.site_path
        )

    def deploy(self, target: str = "github-pages") -> bool:
        """Deploy Quartz site."""
        if target == "github-pages":
            try:
                result = subprocess.run(
                    ["npx", "quartz", "sync", "--no-pull"],
                    cwd=self.site_path,
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            except Exception as e:
                click.echo(f"Deploy error: {e}", err=True)
                return False
        else:
            click.echo(f"Unknown deploy target: {target}", err=True)
            return False


class JekyllGardenPublisher(SitePublisher):
    """Jekyll Digital Garden publisher."""

    @property
    def name(self) -> str:
        return "Jekyll Garden"

    def get_content_path(self) -> Path:
        return self.site_path / "_notes"

    def build(self) -> bool:
        """Build Jekyll site."""
        try:
            # Install dependencies first
            subprocess.run(
                ["bundle", "install"],
                cwd=self.site_path,
                capture_output=True
            )

            result = subprocess.run(
                ["bundle", "exec", "jekyll", "build"],
                cwd=self.site_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                click.echo(f"Build error: {result.stderr}", err=True)
                return False
            return True
        except FileNotFoundError:
            click.echo("Error: bundle not found. Install Ruby and Bundler first.", err=True)
            return False

    def preview(self, port: int = 4000) -> None:
        """Start Jekyll preview server."""
        click.echo(f"Starting Jekyll preview on port {port}...")
        subprocess.run(
            ["bundle", "exec", "jekyll", "serve", "--port", str(port)],
            cwd=self.site_path
        )

    def deploy(self, target: str = "netlify") -> bool:
        """Deploy Jekyll site."""
        if target == "netlify":
            try:
                result = subprocess.run(
                    ["netlify", "deploy", "--prod", "--dir=_site"],
                    cwd=self.site_path,
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            except FileNotFoundError:
                click.echo("Error: netlify CLI not found. Install with: npm install -g netlify-cli", err=True)
                return False
        elif target == "github-pages":
            try:
                result = subprocess.run(
                    ["ghp-import", "-n", "-p", "-f", "_site"],
                    cwd=self.site_path,
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            except FileNotFoundError:
                click.echo("Error: ghp-import not found. Install with: pip install ghp-import", err=True)
                return False
        else:
            click.echo(f"Unknown deploy target: {target}", err=True)
            return False

    def _process_for_publish(self, file: Path) -> str:
        """Jekyll needs specific frontmatter format."""
        content = super()._process_for_publish(file)

        # Ensure Jekyll-compatible frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                    # Jekyll Garden expects 'title' in frontmatter
                    if 'title' not in fm:
                        fm['title'] = file.stem.replace('-', ' ').replace('_', ' ').title()
                    parts[1] = '\n' + yaml.dump(fm, default_flow_style=False)
                    content = '---'.join(parts)
                except:
                    pass

        return content


class EleventyPublisher(SitePublisher):
    """Eleventy (11ty) publisher - fast and flexible."""

    @property
    def name(self) -> str:
        return "Eleventy"

    def get_content_path(self) -> Path:
        return self.site_path / "notes"

    def build(self) -> bool:
        """Build Eleventy site."""
        try:
            result = subprocess.run(
                ["npx", "@11ty/eleventy"],
                cwd=self.site_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                click.echo(f"Build error: {result.stderr}", err=True)
                return False
            return True
        except FileNotFoundError:
            click.echo("Error: npx not found. Install Node.js first.", err=True)
            return False

    def preview(self, port: int = 8080) -> None:
        """Start Eleventy preview server."""
        click.echo(f"Starting Eleventy preview on port {port}...")
        subprocess.run(
            ["npx", "@11ty/eleventy", "--serve", "--port", str(port)],
            cwd=self.site_path
        )

    def deploy(self, target: str = "netlify") -> bool:
        """Deploy Eleventy site."""
        if target == "netlify":
            try:
                result = subprocess.run(
                    ["netlify", "deploy", "--prod", "--dir=_site"],
                    cwd=self.site_path,
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            except FileNotFoundError:
                click.echo("Error: netlify CLI not found.", err=True)
                return False
        elif target == "vercel":
            try:
                result = subprocess.run(
                    ["vercel", "--prod"],
                    cwd=self.site_path,
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            except FileNotFoundError:
                click.echo("Error: vercel CLI not found.", err=True)
                return False
        else:
            click.echo(f"Unknown deploy target: {target}", err=True)
            return False


class GatsbyKBPublisher(SitePublisher):
    """Gatsby Knowledge Base publisher."""

    @property
    def name(self) -> str:
        return "Gatsby KB"

    def get_content_path(self) -> Path:
        return self.site_path / "content"

    def build(self) -> bool:
        """Build Gatsby site."""
        try:
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=self.site_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                click.echo(f"Build error: {result.stderr}", err=True)
                return False
            return True
        except FileNotFoundError:
            click.echo("Error: npm not found. Install Node.js first.", err=True)
            return False

    def preview(self, port: int = 8000) -> None:
        """Start Gatsby preview server."""
        click.echo(f"Starting Gatsby preview on port {port}...")
        subprocess.run(
            ["npm", "run", "develop", "--", "-p", str(port)],
            cwd=self.site_path
        )

    def deploy(self, target: str = "github-pages") -> bool:
        """Deploy Gatsby site."""
        if target == "github-pages":
            try:
                result = subprocess.run(
                    ["npm", "run", "deploy"],
                    cwd=self.site_path,
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            except Exception as e:
                click.echo(f"Deploy error: {e}", err=True)
                return False
        elif target == "vercel":
            try:
                result = subprocess.run(
                    ["vercel", "--prod"],
                    cwd=self.site_path,
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            except FileNotFoundError:
                click.echo("Error: vercel CLI not found.", err=True)
                return False
        else:
            click.echo(f"Unknown deploy target: {target}", err=True)
            return False


def get_publisher(framework: str, vault_path: Path, site_path: Path) -> SitePublisher:
    """Factory function to get the right publisher."""
    publishers = {
        "quartz": QuartzPublisher,
        "jekyll": JekyllGardenPublisher,
        "eleventy": EleventyPublisher,
        "gatsby": GatsbyKBPublisher,
    }

    if framework not in publishers:
        raise ValueError(f"Unknown framework: {framework}. "
                        f"Available: {', '.join(publishers.keys())}")

    return publishers[framework](vault_path, site_path)


def get_default_targets(framework: str) -> dict[str, str]:
    """Get default deployment targets for each framework."""
    return {
        "quartz": "github-pages",
        "jekyll": "netlify",
        "eleventy": "netlify",
        "gatsby": "github-pages",
    }


@click.group()
def cli():
    """Multi-platform static site publishing for Hyperflow."""
    pass


@cli.command()
@click.option('--framework', '-f', type=click.Choice(['quartz', 'jekyll', 'eleventy', 'gatsby']),
              default='quartz', help='Static site framework to use')
@click.option('--vault', '-v', type=click.Path(exists=True), default='.',
              help='Path to knowledge vault')
@click.option('--site', '-s', type=click.Path(), help='Path to site directory')
@click.option('--include', '-i', multiple=True, help='Glob patterns to include')
@click.option('--exclude', '-e', multiple=True, help='Glob patterns to exclude')
@click.option('--all-files', is_flag=True, help='Include all files (not just public)')
def build(framework: str, vault: str, site: Optional[str],
          include: tuple, exclude: tuple, all_files: bool):
    """Build static site from vault content."""
    vault_path = Path(vault).resolve()

    # Default site path based on framework
    if site:
        site_path = Path(site).resolve()
    else:
        site_path = vault_path.parent / f"{vault_path.name}-{framework}"

    click.echo(f"Building {framework} site...")
    click.echo(f"  Vault: {vault_path}")
    click.echo(f"  Site: {site_path}")

    # Check if site exists
    if not site_path.exists():
        click.echo(f"\nSite directory not found: {site_path}")
        click.echo(f"Create it first with the appropriate template:")
        click.echo(f"  Quartz: npx quartz create")
        click.echo(f"  Jekyll: git clone https://github.com/maximevaillancourt/digital-garden-jekyll-template")
        click.echo(f"  Eleventy: git clone https://github.com/juanfrank77/foam-eleventy-template")
        click.echo(f"  Gatsby: git clone https://github.com/hikerpig/foam-template-gatsby-kb")
        sys.exit(1)

    # Get publisher
    publisher = get_publisher(framework, vault_path, site_path)

    # Copy files
    include_patterns = list(include) if include else None
    exclude_patterns = list(exclude) if exclude else None
    copied = publisher.publish(include_patterns, exclude_patterns, not all_files)

    if copied == 0:
        click.echo("\nNo files to publish. Make sure files are marked with 'public: true' or have #public tag.")
        click.echo("Or use --all-files to include all matching files.")
        sys.exit(1)

    # Build
    click.echo(f"\nBuilding {publisher.name}...")
    if publisher.build():
        click.echo("Build successful!")
    else:
        click.echo("Build failed.", err=True)
        sys.exit(1)


@cli.command()
@click.option('--framework', '-f', type=click.Choice(['quartz', 'jekyll', 'eleventy', 'gatsby']),
              default='quartz', help='Static site framework')
@click.option('--vault', '-v', type=click.Path(exists=True), default='.',
              help='Path to knowledge vault')
@click.option('--site', '-s', type=click.Path(), help='Path to site directory')
@click.option('--port', '-p', type=int, default=8080, help='Preview server port')
def preview(framework: str, vault: str, site: Optional[str], port: int):
    """Start local preview server."""
    vault_path = Path(vault).resolve()
    site_path = Path(site).resolve() if site else vault_path.parent / f"{vault_path.name}-{framework}"

    if not site_path.exists():
        click.echo(f"Site directory not found: {site_path}", err=True)
        sys.exit(1)

    publisher = get_publisher(framework, vault_path, site_path)
    publisher.preview(port)


@cli.command()
@click.option('--framework', '-f', type=click.Choice(['quartz', 'jekyll', 'eleventy', 'gatsby']),
              default='quartz', help='Static site framework')
@click.option('--vault', '-v', type=click.Path(exists=True), default='.',
              help='Path to knowledge vault')
@click.option('--site', '-s', type=click.Path(), help='Path to site directory')
@click.option('--target', '-t', type=click.Choice(['github-pages', 'netlify', 'vercel']),
              help='Deployment target (defaults based on framework)')
def deploy(framework: str, vault: str, site: Optional[str], target: Optional[str]):
    """Deploy site to hosting platform."""
    vault_path = Path(vault).resolve()
    site_path = Path(site).resolve() if site else vault_path.parent / f"{vault_path.name}-{framework}"

    if not site_path.exists():
        click.echo(f"Site directory not found: {site_path}", err=True)
        sys.exit(1)

    # Default target based on framework
    if not target:
        target = get_default_targets(framework).get(framework, 'github-pages')

    publisher = get_publisher(framework, vault_path, site_path)

    click.echo(f"Deploying {publisher.name} to {target}...")
    if publisher.deploy(target):
        click.echo("Deploy successful!")
    else:
        click.echo("Deploy failed.", err=True)
        sys.exit(1)


@cli.command()
def list_frameworks():
    """List available publishing frameworks and their features."""
    click.echo("\nAvailable Publishing Frameworks:")
    click.echo("=" * 60)

    frameworks = [
        ("quartz", "Quartz", "GitHub Pages", "Best for Obsidian; built-in graph, search"),
        ("jekyll", "Jekyll Garden", "Netlify", "Simple; wikilinks, backlinks, graph"),
        ("eleventy", "Eleventy", "Netlify/Vercel", "Fast; highly flexible"),
        ("gatsby", "Gatsby KB", "GitHub Pages/Vercel", "Rich interactivity; React-based"),
    ]

    for key, name, deploy, features in frameworks:
        click.echo(f"\n  {key:10} - {name}")
        click.echo(f"             Deploy: {deploy}")
        click.echo(f"             {features}")


if __name__ == '__main__':
    cli()
