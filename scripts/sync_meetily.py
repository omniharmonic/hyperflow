#!/usr/bin/env python3
"""
Meetily Sync - Export meetings from Meetily to Obsidian markdown.

Reads directly from Meetily's native SQLite database. No fork required!

Usage:
    python3 scripts/sync_meetily.py              # Export new meetings
    python3 scripts/sync_meetily.py --all        # Re-export all
    python3 scripts/sync_meetily.py --list       # List meetings in DB
    python3 scripts/sync_meetily.py --db /path/to/db.sqlite  # Custom DB path

Configuration (in order of priority):
    1. Command-line arguments (--db, --vault)
    2. Environment variables (MEETILY_DB_PATH, HYPERFLOW_VAULT)
    3. .hyperflow.env file in vault root
    4. Auto-detection from standard locations
"""

import os
import re
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List


def load_env_file(vault_path: Path) -> None:
    """Load configuration from .hyperflow.env if it exists."""
    env_file = vault_path / '.hyperflow.env'
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value


def get_vault_path() -> Path:
    """
    Get the vault path.
    
    Priority:
    1. HYPERFLOW_VAULT environment variable
    2. Script's parent's parent directory (assumes scripts/ in vault root)
    """
    env_vault = os.environ.get('HYPERFLOW_VAULT')
    if env_vault:
        return Path(env_vault).expanduser()
    return Path(__file__).parent.parent


def get_meetily_db_path(custom_path: Optional[str] = None) -> Path:
    """
    Find Meetily's native database location.
    
    Priority:
    1. custom_path argument (from --db flag)
    2. MEETILY_DB_PATH environment variable
    3. Auto-detect from standard locations
    """
    # 1. Custom path from argument
    if custom_path:
        path = Path(custom_path).expanduser()
        if path.exists():
            return path
        raise FileNotFoundError(f"Custom database path not found: {custom_path}")
    
    # 2. Environment variable
    env_path = os.environ.get('MEETILY_DB_PATH')
    if env_path:
        path = Path(env_path).expanduser()
        if path.exists():
            return path
        raise FileNotFoundError(f"MEETILY_DB_PATH not found: {env_path}")
    
    # 3. Auto-detect standard location
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support' / 'ai.meetily.app'
    elif sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', '')) / 'ai.meetily.app'
    else:
        base = Path.home() / '.local' / 'share' / 'ai.meetily.app'
    
    for name in ['meeting_minutes.sqlite', 'meeting_minutes.db']:
        path = base / name
        if path.exists():
            return path
    
    raise FileNotFoundError(
        f"Meetily database not found at {base}\n"
        "Options:\n"
        "  1. Run Meetily at least once to create the database\n"
        "  2. Use --db /path/to/database.sqlite\n"
        "  3. Set MEETILY_DB_PATH environment variable"
    )


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """Convert title to kebab-case filename slug."""
    if not title:
        return 'untitled-meeting'
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower())
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit('-', 1)[0]
    return slug or 'untitled-meeting'


def parse_summary(result_json: str) -> Optional[Dict[str, Any]]:
    """Parse summary JSON from database."""
    if not result_json:
        return None
    try:
        data = json.loads(result_json)
        return json.loads(data) if isinstance(data, str) else data
    except (json.JSONDecodeError, TypeError):
        return None


def format_summary_sections(summary: Dict[str, Any]) -> str:
    """Format summary sections into markdown."""
    lines = []
    sections = [
        ('SessionSummary', 'Summary'),
        ('KeyItemsDecisions', 'Key Decisions'),
        ('ImmediateActionItems', 'Action Items'),
        ('NextSteps', 'Next Steps'),
        ('CriticalDeadlines', 'Deadlines'),
        ('People', 'Participants'),
    ]
    
    for key, title in sections:
        if key in summary and summary[key].get('blocks'):
            lines.append(f'## {title}\n')
            for block in summary[key]['blocks']:
                content = block.get('content', str(block)) if isinstance(block, dict) else str(block)
                prefix = '- [ ] ' if key == 'ImmediateActionItems' else '- '
                lines.append(f'{prefix}{content}')
            lines.append('')
    
    return '\n'.join(lines)


def export_meeting(meeting: dict, transcripts: list, summary: Optional[dict], export_dir: Path) -> Path:
    """Export a single meeting to markdown."""
    created_at = meeting.get('created_at', datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00').replace(' ', 'T'))
    except ValueError:
        dt = datetime.now()
    
    title = summary.get('MeetingName', meeting.get('title', 'Untitled')) if summary else meeting.get('title', 'Untitled')
    slug = sanitize_filename(title)
    filename = f"{dt.strftime('%Y-%m-%dT%H-%M')}_{slug}.md"
    filepath = export_dir / filename
    
    # Frontmatter
    safe_title = title.replace('"', '\\"')
    content = f'''---
title: "{safe_title}"
date: {created_at}
status: pending_enrichment
source: meetily
tags:
  - meeting
  - unprocessed
---

# {title}

'''
    
    # Summary sections
    if summary:
        content += format_summary_sections(summary)
    
    # Transcript
    content += '## Transcript\n\n'
    for t in transcripts:
        text = t.get('transcript', '')
        ts = t.get('timestamp', '')
        if text:
            if ts:
                content += f'*{ts}*\n\n'
            content += f'{text}\n\n'
    
    export_dir.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding='utf-8')
    return filepath


def sync_meetings(vault_path: Path, force_all: bool = False, meeting_id: str = None, db_path_override: str = None) -> List[str]:
    """Sync meetings from Meetily database to vault."""
    db_path = get_meetily_db_path(db_path_override)
    export_dir = vault_path / '_inbox' / 'meetings'
    sync_file = export_dir / '.meetily_synced'
    
    print(f"📂 Database: {db_path}")
    print(f"📁 Export to: {export_dir}")
    
    synced = set()
    if not force_all and sync_file.exists():
        synced = set(sync_file.read_text().strip().split('\n'))
    
    exported = []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if meeting_id:
        cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
    else:
        cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC")
    
    meetings = cursor.fetchall()
    print(f"📋 Found {len(meetings)} meeting(s)")
    
    for meeting in meetings:
        mid = meeting['id']
        if mid in synced and not force_all:
            continue
        
        cursor.execute("SELECT * FROM transcripts WHERE meeting_id = ? ORDER BY timestamp", (mid,))
        transcripts = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT result FROM summary_processes WHERE meeting_id = ? AND status = 'completed'", (mid,))
        summary_row = cursor.fetchone()
        summary = parse_summary(summary_row['result']) if summary_row else None
        
        try:
            filepath = export_meeting(dict(meeting), transcripts, summary, export_dir)
            exported.append(str(filepath))
            synced.add(mid)
            print(f"✅ {filepath.name}")
        except Exception as e:
            print(f"❌ {mid}: {e}")
    
    sync_file.parent.mkdir(parents=True, exist_ok=True)
    sync_file.write_text('\n'.join(sorted(synced)))
    conn.close()
    return exported


def list_meetings(db_path_override: str = None):
    """List all meetings in Meetily database."""
    db_path = get_meetily_db_path(db_path_override)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, created_at FROM meetings ORDER BY created_at DESC")
    
    print(f"\n{'ID':<25} {'Title':<40} {'Date'}")
    print("-" * 80)
    for row in cursor.fetchall():
        print(f"{row['id'][:23]:<25} {(row['title'] or 'Untitled')[:38]:<40} {row['created_at']}")
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Sync Meetily meetings to Obsidian',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Environment Variables:
  MEETILY_DB_PATH   Path to Meetily's SQLite database
  HYPERFLOW_VAULT   Path to your Obsidian vault

Examples:
  %(prog)s                           # Sync new meetings
  %(prog)s --all                     # Re-export all meetings  
  %(prog)s --db ~/custom/path.db     # Use custom database
  %(prog)s --list                    # Show available meetings
'''
    )
    parser.add_argument('--all', '-a', action='store_true', help='Re-export all meetings')
    parser.add_argument('--meeting-id', '-m', type=str, help='Export specific meeting')
    parser.add_argument('--list', '-l', action='store_true', help='List meetings only')
    parser.add_argument('--vault', type=str, help='Vault path (default: auto-detect from HYPERFLOW_VAULT or script location)')
    parser.add_argument('--db', type=str, help='Meetily database path (default: auto-detect from MEETILY_DB_PATH or standard location)')
    args = parser.parse_args()
    
    print("🔄 Meetily Sync\n" + "=" * 40)
    
    # Determine vault path first (needed for .hyperflow.env)
    vault_path = Path(args.vault) if args.vault else get_vault_path()
    
    # Load .hyperflow.env if it exists
    load_env_file(vault_path)
    
    if args.list:
        list_meetings(args.db)
        return
    
    try:
        exported = sync_meetings(vault_path, args.all, args.meeting_id, args.db)
        print("=" * 40)
        if exported:
            print(f"✨ Exported {len(exported)} meeting(s)")
            print("\n→ Next: Run /ingest-meetings to process")
        else:
            print("📭 No new meetings to export")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

