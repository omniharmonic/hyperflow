#!/usr/bin/env python3
"""
Task synchronization for Hyperflow.

Extracts tasks from meeting notes and syncs them to:
1. Person profiles (tasks mentioning/assigned to them)
2. Project task lists
3. Central task dashboard

Usage:
    # Sync tasks from recent meetings
    python sync_tasks.py

    # Sync from specific meeting
    python sync_tasks.py meeting.md

    # Sync all meetings in a project
    python sync_tasks.py --project opencivics

    # Dry run to see what would be synced
    python sync_tasks.py --dry-run
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return {}
    try:
        parts = content.split('---', 2)
        if len(parts) >= 3:
            return yaml.safe_load(parts[1]) or {}
    except Exception:
        pass
    return {}


def extract_tasks_from_content(content: str) -> list[dict]:
    """Extract task items from markdown content."""
    tasks = []

    # Pattern for markdown checkboxes
    task_pattern = re.compile(
        r'^(\s*)-\s*\[\s*([xX ]?)\s*\]\s*(.+)$',
        re.MULTILINE
    )

    for match in task_pattern.finditer(content):
        indent = len(match.group(1))
        completed = match.group(2).lower() == 'x'
        text = match.group(3).strip()

        # Extract assignee if present
        assignee = None
        assignee_match = re.search(r'@(\w+)', text)
        if assignee_match:
            assignee = assignee_match.group(1)

        # Extract due date if present
        due_date = None
        due_match = re.search(r'\((?:due|by):?\s*([^)]+)\)', text, re.IGNORECASE)
        if due_match:
            due_date = due_match.group(1)

        # Extract linked people
        people_links = re.findall(r'\[\[people/([^\]]+)\]\]', text)

        tasks.append({
            'text': text,
            'completed': completed,
            'assignee': assignee,
            'due_date': due_date,
            'people': people_links,
            'indent': indent,
        })

    return tasks


def find_person_file(name: str, vault_path: Path) -> Optional[Path]:
    """Find a person's profile file."""
    people_dir = vault_path / 'people'
    if not people_dir.exists():
        return None

    # Try exact match first
    exact = people_dir / f"{name}.md"
    if exact.exists():
        return exact

    # Try case-insensitive match
    for f in people_dir.glob('*.md'):
        if f.stem.lower() == name.lower():
            return f

    return None


def add_task_to_person(person_file: Path, task: dict, source_file: Path, vault_path: Path) -> bool:
    """Add a task reference to a person's profile."""
    content = person_file.read_text(encoding='utf-8')

    # Create task reference
    source_link = str(source_file.relative_to(vault_path))
    task_line = f"- [ ] {task['text']} (from [[{source_link}]])"

    if task_line in content:
        return False  # Already exists

    # Find or create Tasks section
    if '## Tasks' in content:
        content = content.replace(
            '## Tasks\n',
            f"## Tasks\n\n{task_line}\n"
        )
    elif '## Mentions' in content:
        content = content.replace(
            '## Mentions',
            f"## Tasks\n\n{task_line}\n\n## Mentions"
        )
    else:
        content += f"\n## Tasks\n\n{task_line}\n"

    person_file.write_text(content, encoding='utf-8')
    return True


class TaskSyncer:
    """Synchronizes tasks across the knowledge vault."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.people_dir = vault_path / 'people'
        self.projects_dir = vault_path / 'projects'

    def process_file(self, filepath: Path, dry_run: bool = False) -> dict:
        """Process a file and sync its tasks."""
        stats = {
            'tasks_found': 0,
            'people_updated': 0,
            'projects_updated': 0,
        }

        content = filepath.read_text(encoding='utf-8')
        frontmatter = extract_frontmatter(content)
        tasks = extract_tasks_from_content(content)

        stats['tasks_found'] = len(tasks)

        if not tasks:
            return stats

        # Get project context
        project_name = frontmatter.get('project', '')
        if not project_name and 'projects/' in str(filepath):
            # Extract project from path
            parts = filepath.parts
            if 'projects' in parts:
                idx = parts.index('projects')
                if idx + 1 < len(parts):
                    project_name = parts[idx + 1]

        for task in tasks:
            if task['completed']:
                continue  # Skip completed tasks

            # Sync to assigned person
            if task['assignee']:
                person_file = find_person_file(task['assignee'], self.vault_path)
                if person_file:
                    if dry_run:
                        click.echo(f"  Would add task to {person_file.stem}")
                    else:
                        if add_task_to_person(person_file, task, filepath, self.vault_path):
                            stats['people_updated'] += 1

            # Sync to mentioned people
            for person_name in task['people']:
                person_file = find_person_file(person_name, self.vault_path)
                if person_file:
                    if dry_run:
                        click.echo(f"  Would add task to {person_file.stem}")
                    else:
                        if add_task_to_person(person_file, task, filepath, self.vault_path):
                            stats['people_updated'] += 1

        return stats

    def sync_directory(self, directory: Path, dry_run: bool = False) -> dict:
        """Sync tasks from all markdown files in a directory."""
        total_stats = {
            'files_processed': 0,
            'tasks_found': 0,
            'people_updated': 0,
            'projects_updated': 0,
        }

        for filepath in directory.glob('**/*.md'):
            click.echo(f"Processing: {filepath.name}")
            stats = self.process_file(filepath, dry_run)
            total_stats['files_processed'] += 1
            for key in ['tasks_found', 'people_updated', 'projects_updated']:
                total_stats[key] += stats[key]

        return total_stats


@click.command()
@click.argument('file', type=click.Path(), required=False)
@click.option('--project', '-p', help='Sync tasks from specific project')
@click.option('--all-meetings', '-a', is_flag=True, help='Sync all meeting folders')
@click.option('--recent', '-r', type=int, default=0,
              help='Only process files modified in last N days')
@click.option('--dry-run', '-n', is_flag=True, help='Show what would be synced')
@click.option('--vault', '-v', type=click.Path(exists=True), help='Vault path')
def main(file: Optional[str], project: Optional[str], all_meetings: bool,
         recent: int, dry_run: bool, vault: Optional[str]):
    """Sync tasks from meeting notes to person profiles and project lists.

    Examples:
        sync_tasks.py meeting.md           # Sync from specific file
        sync_tasks.py --project opencivics # Sync project meetings
        sync_tasks.py --all-meetings       # Sync all meetings
        sync_tasks.py --recent 7           # Sync files from last 7 days
    """
    vault_path = Path(vault) if vault else Path(__file__).parent.parent
    syncer = TaskSyncer(vault_path)

    if file:
        filepath = Path(file)
        if not filepath.exists():
            filepath = vault_path / file
        if not filepath.exists():
            click.echo(f"File not found: {file}", err=True)
            sys.exit(1)

        click.echo(f"Syncing tasks from: {filepath}")
        stats = syncer.process_file(filepath, dry_run)

    elif project:
        project_dir = vault_path / 'projects' / project
        if not project_dir.exists():
            click.echo(f"Project not found: {project}", err=True)
            sys.exit(1)

        click.echo(f"Syncing tasks from project: {project}")
        stats = syncer.sync_directory(project_dir, dry_run)

    elif all_meetings:
        click.echo("Syncing tasks from all meetings...")
        stats = {'files_processed': 0, 'tasks_found': 0, 'people_updated': 0, 'projects_updated': 0}

        # Process meetings folder
        meetings_dir = vault_path / 'meetings'
        if meetings_dir.exists():
            s = syncer.sync_directory(meetings_dir, dry_run)
            for k in stats:
                stats[k] += s[k]

        # Process inbox meetings
        inbox_meetings = vault_path / '_inbox' / 'meetings'
        if inbox_meetings.exists():
            s = syncer.sync_directory(inbox_meetings, dry_run)
            for k in stats:
                stats[k] += s[k]

        # Process project meetings
        projects_dir = vault_path / 'projects'
        if projects_dir.exists():
            for project_folder in projects_dir.iterdir():
                meetings_folder = project_folder / 'meetings'
                if meetings_folder.exists():
                    s = syncer.sync_directory(meetings_folder, dry_run)
                    for k in stats:
                        stats[k] += s[k]
    else:
        # Default: process recent inbox meetings
        inbox_meetings = vault_path / '_inbox' / 'meetings'
        if inbox_meetings.exists():
            click.echo("Syncing tasks from inbox meetings...")
            stats = syncer.sync_directory(inbox_meetings, dry_run)
        else:
            click.echo("No files to process. Use --all-meetings or specify a file.")
            sys.exit(0)

    # Summary
    click.echo(f"\n{'='*50}")
    click.echo("Task Sync Summary:")
    if 'files_processed' in stats:
        click.echo(f"  Files processed: {stats['files_processed']}")
    click.echo(f"  Tasks found: {stats['tasks_found']}")
    click.echo(f"  People profiles updated: {stats['people_updated']}")
    click.echo(f"  Projects updated: {stats['projects_updated']}")

    if dry_run:
        click.echo("\n[DRY RUN - no changes made]")


if __name__ == '__main__':
    main()
