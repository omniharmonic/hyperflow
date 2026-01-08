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
    # Try multiple possible app identifiers (Meetily has used different ones)
    if sys.platform == 'darwin':
        app_support = Path.home() / 'Library' / 'Application Support'
        possible_dirs = [
            'com.meetily.ai',      # Current version
            'ai.meetily.app',      # Alternative
            'meetily',             # Simple name
            'com.meetily.app',     # Another variant
        ]
    elif sys.platform == 'win32':
        app_support = Path(os.environ.get('APPDATA', ''))
        possible_dirs = ['com.meetily.ai', 'ai.meetily.app', 'meetily']
    else:
        app_support = Path.home() / '.local' / 'share'
        possible_dirs = ['com.meetily.ai', 'ai.meetily.app', 'meetily']
    
    db_names = ['meeting_minutes.sqlite', 'meeting_minutes.db', 'meetily.db']
    
    for dir_name in possible_dirs:
        base = app_support / dir_name
        for db_name in db_names:
            path = base / db_name
            if path.exists():
                return path
    
    searched = [str(app_support / d) for d in possible_dirs]
    raise FileNotFoundError(
        f"Meetily database not found.\n"
        f"Searched: {', '.join(searched)}\n\n"
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
    """Parse summary JSON from database, handling various formats."""
    if not result_json:
        return None
    try:
        # Handle double-encoded JSON
        data = json.loads(result_json)
        if isinstance(data, str):
            data = json.loads(data)
        return data
    except (json.JSONDecodeError, TypeError) as e:
        print(f"  ⚠️ Summary parse warning: {e}")
        return None


def format_summary_sections(summary: Dict[str, Any]) -> str:
    """Format summary sections into markdown.
    
    Meetily stores summaries as {"markdown": "**Summary**\\n\\n..."}
    We extract and clean up the markdown content.
    """
    # Check if summary has 'markdown' key (Meetily's current format)
    if 'markdown' in summary:
        markdown_content = summary['markdown']
        
        # Convert **Header** to ## Header for better Obsidian formatting
        # and add checkboxes for action items
        lines = []
        in_action_items = False
        
        for line in markdown_content.split('\n'):
            # Convert bold headers to markdown headers
            if line.startswith('**') and line.endswith('**'):
                header = line.strip('*')
                lines.append(f'## {header}')
                in_action_items = 'action' in header.lower()
            elif line.strip().startswith('- ') and in_action_items:
                # Add checkbox for action items
                item = line.strip()[2:]  # Remove "- "
                lines.append(f'- [ ] {item}')
            elif line.strip().startswith('* ') and in_action_items:
                # Handle bullet points too
                item = line.strip()[2:]
                lines.append(f'- [ ] {item}')
            else:
                if line.strip() and not line.strip().startswith(('**', '- ', '* ')):
                    in_action_items = False
                lines.append(line)
        
        return '\n'.join(lines)
    
    # Fallback: Handle structured formats (older Meetily versions or other sources)
    lines = []
    section_mappings = [
        (['SessionSummary', 'Summary', 'summary'], 'Summary'),
        (['KeyItemsDecisions', 'KeyDecisions', 'key_decisions'], 'Key Decisions'),
        (['ImmediateActionItems', 'ActionItems', 'action_items'], 'Action Items'),
        (['NextSteps', 'next_steps'], 'Next Steps'),
        (['DiscussionHighlights', 'Discussion', 'highlights'], 'Discussion Highlights'),
    ]
    
    for keys, title in section_mappings:
        for key in keys:
            if key in summary:
                content = summary[key]
                if isinstance(content, str) and content.strip():
                    lines.append(f'## {title}\n')
                    lines.append(content)
                    lines.append('')
                elif isinstance(content, list) and content:
                    lines.append(f'## {title}\n')
                    for item in content:
                        prefix = '- [ ] ' if title == 'Action Items' else '- '
                        lines.append(f'{prefix}{item}')
                    lines.append('')
                break
    
    return '\n'.join(lines)


def export_meeting(meeting: dict, transcripts: list, summary: Optional[dict], export_dir: Path) -> Path:
    """Export a single meeting to markdown."""
    created_at = meeting.get('created_at', datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00').replace(' ', 'T'))
    except ValueError:
        dt = datetime.now()
    
    # Prefer meeting title from DB (already set by Meetily), fallback to summary or 'Untitled'
    title = meeting.get('title') or (summary.get('MeetingName') if summary else None) or 'Untitled'
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


def debug_database(db_path_override: str = None, meeting_id: str = None):
    """Debug: Show database schema and sample data."""
    db_path = get_meetily_db_path(db_path_override)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("DATABASE DEBUG INFO")
    print("=" * 60)
    print(f"\n📂 Database: {db_path}")
    
    # List all tables
    print("\n📋 TABLES:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row['name'] for row in cursor.fetchall()]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        count = cursor.fetchone()['count']
        print(f"  - {table} ({count} rows)")
    
    # Show schema for key tables
    for table in ['meetings', 'transcripts', 'summary_processes', 'summaries']:
        if table in tables:
            print(f"\n📐 SCHEMA: {table}")
            cursor.execute(f"PRAGMA table_info({table})")
            for col in cursor.fetchall():
                print(f"  - {col['name']} ({col['type']})")
    
    # Show sample summary data
    print("\n📊 SUMMARY DATA CHECK:")
    
    # Check summary_processes table
    if 'summary_processes' in tables:
        cursor.execute("SELECT meeting_id, status, result FROM summary_processes LIMIT 3")
        rows = cursor.fetchall()
        print(f"\n  summary_processes table ({len(rows)} samples):")
        for row in rows:
            result_preview = str(row['result'])[:200] if row['result'] else 'NULL'
            print(f"    meeting_id: {row['meeting_id'][:20]}...")
            print(f"    status: {row['status']}")
            print(f"    result: {result_preview}...")
            print()
    
    # Check summaries table (alternative location)
    if 'summaries' in tables:
        cursor.execute("SELECT * FROM summaries LIMIT 3")
        rows = cursor.fetchall()
        print(f"\n  summaries table ({len(rows)} samples):")
        for row in rows:
            print(f"    {dict(row)}")
    
    # If specific meeting requested, show all its data
    if meeting_id:
        print(f"\n🔍 SPECIFIC MEETING: {meeting_id}")
        
        cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
        meeting = cursor.fetchone()
        if meeting:
            print(f"\n  Meeting data:")
            for key in meeting.keys():
                val = str(meeting[key])[:100] if meeting[key] else 'NULL'
                print(f"    {key}: {val}")
        
        cursor.execute("SELECT COUNT(*) as count FROM transcripts WHERE meeting_id = ?", (meeting_id,))
        print(f"\n  Transcript segments: {cursor.fetchone()['count']}")
        
        if 'summary_processes' in tables:
            cursor.execute("SELECT * FROM summary_processes WHERE meeting_id = ?", (meeting_id,))
            summary = cursor.fetchone()
            if summary:
                print(f"\n  Summary process:")
                print(f"    status: {summary['status']}")
                if summary['result']:
                    print(f"    result (full):\n{summary['result']}")
            else:
                print(f"\n  No summary_processes entry found for this meeting")
    
    conn.close()
    print("\n" + "=" * 60)


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
    parser.add_argument('--debug', '-d', action='store_true', help='Debug: show database schema and summary data')
    parser.add_argument('--vault', type=str, help='Vault path (default: auto-detect from HYPERFLOW_VAULT or script location)')
    parser.add_argument('--db', type=str, help='Meetily database path (default: auto-detect from MEETILY_DB_PATH or standard location)')
    args = parser.parse_args()
    
    print("🔄 Meetily Sync\n" + "=" * 40)
    
    # Determine vault path first (needed for .hyperflow.env)
    vault_path = Path(args.vault) if args.vault else get_vault_path()
    
    # Load .hyperflow.env if it exists
    load_env_file(vault_path)
    
    if args.debug:
        debug_database(args.db, args.meeting_id)
        return
    
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

