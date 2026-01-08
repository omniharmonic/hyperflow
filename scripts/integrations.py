#!/usr/bin/env python3
"""
Hyperflow Integrations - Unified API layer for external services.

Provides direct API access to Notion, Gmail, and Google Calendar
without MCP dependencies for reliable, testable integrations.

Usage:
    from integrations import HyperflowIntegrations
    
    integrations = HyperflowIntegrations()
    integrations.notion.create_task(database_id, task_data)
    integrations.gmail.send_email(to, subject, body)
    integrations.calendar.find_event(date, title_hint)
"""

import os
import sys
import json
import yaml
import base64
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


# =============================================================================
# Configuration Management
# =============================================================================

@dataclass
class NotionConfig:
    token: str = ""
    default_workspace: str = ""


@dataclass
class GoogleConfig:
    credentials_file: str = ""
    token_file: str = ""
    scopes: List[str] = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ])


@dataclass
class ProjectConfig:
    name: str = ""
    notion_database: str = ""
    team_emails: List[str] = field(default_factory=list)


@dataclass  
class HyperflowConfig:
    notion: NotionConfig = field(default_factory=NotionConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    projects: Dict[str, ProjectConfig] = field(default_factory=dict)
    meetily_db_path: str = ""
    vault_path: str = ""
    
    @classmethod
    def load(cls, config_dir: Path = None) -> 'HyperflowConfig':
        """Load configuration from .hyperflow/ directory."""
        if config_dir is None:
            # Try to find config in current directory or parent
            for path in [Path.cwd(), Path.cwd().parent, Path(__file__).parent.parent]:
                if (path / '.hyperflow').exists():
                    config_dir = path / '.hyperflow'
                    break
                elif (path / '.hyperflow.env').exists():
                    config_dir = path
                    break
        
        config = cls()
        
        # Load from .hyperflow/config.yaml if exists
        yaml_path = config_dir / 'config.yaml' if config_dir else None
        if yaml_path and yaml_path.exists():
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
                config._load_from_dict(data)
        
        # Also load from .hyperflow.env (legacy support)
        env_path = config_dir / '.hyperflow.env' if config_dir else Path('.hyperflow.env')
        if env_path.exists():
            config._load_from_env(env_path)
        
        # Environment variables override config files
        config._load_from_environment()
        
        return config
    
    def _load_from_dict(self, data: dict):
        """Load config from dictionary (YAML)."""
        if 'notion' in data:
            self.notion.token = data['notion'].get('token', '')
            self.notion.default_workspace = data['notion'].get('default_workspace', '')
        
        if 'google' in data:
            self.google.credentials_file = data['google'].get('credentials_file', '')
            self.google.token_file = data['google'].get('token_file', '')
            if 'scopes' in data['google']:
                self.google.scopes = data['google']['scopes']
        
        if 'projects' in data:
            for name, proj_data in data['projects'].items():
                self.projects[name] = ProjectConfig(
                    name=name,
                    notion_database=proj_data.get('notion_database', ''),
                    team_emails=proj_data.get('team_emails', [])
                )
        
        self.meetily_db_path = data.get('meetily_db_path', '')
        self.vault_path = data.get('vault_path', '')
    
    def _load_from_env(self, env_path: Path):
        """Load config from .env file."""
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            
            if key == 'NOTION_TOKEN':
                self.notion.token = value
            elif key == 'GOOGLE_CREDENTIALS_FILE':
                self.google.credentials_file = value
            elif key == 'MEETILY_DB_PATH':
                self.meetily_db_path = value
            elif key == 'HYPERFLOW_VAULT':
                self.vault_path = value
    
    def _load_from_environment(self):
        """Load config from environment variables."""
        if os.environ.get('NOTION_TOKEN'):
            self.notion.token = os.environ['NOTION_TOKEN']
        if os.environ.get('GOOGLE_CREDENTIALS_FILE'):
            self.google.credentials_file = os.environ['GOOGLE_CREDENTIALS_FILE']
        if os.environ.get('MEETILY_DB_PATH'):
            self.meetily_db_path = os.environ['MEETILY_DB_PATH']
        if os.environ.get('HYPERFLOW_VAULT'):
            self.vault_path = os.environ['HYPERFLOW_VAULT']
    
    def save(self, config_dir: Path):
        """Save configuration to .hyperflow/config.yaml."""
        config_dir.mkdir(exist_ok=True)
        
        data = {
            'notion': {
                'token': self.notion.token,
                'default_workspace': self.notion.default_workspace,
            },
            'google': {
                'credentials_file': self.google.credentials_file,
                'token_file': self.google.token_file,
                'scopes': self.google.scopes,
            },
            'projects': {
                name: {
                    'notion_database': proj.notion_database,
                    'team_emails': proj.team_emails,
                }
                for name, proj in self.projects.items()
            },
            'meetily_db_path': self.meetily_db_path,
            'vault_path': self.vault_path,
        }
        
        with open(config_dir / 'config.yaml', 'w') as f:
            yaml.dump(data, f, default_flow_style=False)


# =============================================================================
# Notion Integration
# =============================================================================

class NotionClient:
    """Direct Notion API client."""
    
    BASE_URL = "https://api.notion.com/v1"
    
    def __init__(self, token: str):
        self.token = token
        self._session = None
    
    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make a request to Notion API."""
        import urllib.request
        import urllib.error
        
        url = f"{self.BASE_URL}/{endpoint}"
        body = json.dumps(data).encode() if data else None
        
        req = urllib.request.Request(url, data=body, headers=self._headers, method=method)
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise NotionError(f"Notion API error: {e.code} - {error_body}")
    
    def test_connection(self) -> bool:
        """Test if Notion connection works."""
        try:
            self._request("GET", "users/me")
            return True
        except Exception:
            return False
    
    def get_database(self, database_id: str) -> dict:
        """Get database metadata."""
        return self._request("GET", f"databases/{database_id}")
    
    def query_database(self, database_id: str, filter: dict = None, sorts: list = None) -> List[dict]:
        """Query a Notion database."""
        data = {}
        if filter:
            data['filter'] = filter
        if sorts:
            data['sorts'] = sorts
        
        result = self._request("POST", f"databases/{database_id}/query", data)
        return result.get('results', [])
    
    def create_page(self, parent: dict, properties: dict, children: list = None) -> dict:
        """Create a page in a database."""
        data = {
            "parent": parent,
            "properties": properties
        }
        if children:
            data['children'] = children
        
        return self._request("POST", "pages", data)
    
    def create_task(self, database_id: str, task: dict) -> dict:
        """
        Create a task in a Notion database.
        
        Args:
            database_id: Notion database ID
            task: Dict with keys: title, assignee, due_date, source, status
        """
        properties = {
            "Name": {"title": [{"text": {"content": task.get('title', 'Untitled Task')}}]},
        }
        
        if task.get('status'):
            properties["Status"] = {"select": {"name": task.get('status', 'To Do')}}
        
        if task.get('due_date'):
            properties["Due Date"] = {"date": {"start": task['due_date']}}
        
        if task.get('assignee'):
            properties["Assignee"] = {"rich_text": [{"text": {"content": task['assignee']}}]}
        
        if task.get('source'):
            properties["Source"] = {"url": task['source']}
        
        if task.get('project'):
            properties["Project"] = {"select": {"name": task['project']}}
        
        return self.create_page(
            parent={"database_id": database_id},
            properties=properties
        )
    
    def find_duplicate_task(self, database_id: str, source_contains: str) -> Optional[dict]:
        """Check if a task from a source already exists."""
        results = self.query_database(
            database_id,
            filter={
                "property": "Source",
                "url": {"contains": source_contains}
            }
        )
        return results[0] if results else None


class NotionError(Exception):
    pass


# =============================================================================
# Gmail Integration
# =============================================================================

class GmailClient:
    """Direct Gmail API client using OAuth2."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.compose'
    ]
    
    def __init__(self, credentials_file: str, token_file: str = None):
        self.credentials_file = Path(credentials_file).expanduser()
        self.token_file = Path(token_file or '~/.hyperflow/gmail_token.pickle').expanduser()
        self._service = None
    
    def _get_credentials(self):
        """Get or refresh OAuth credentials."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            raise GmailError(
                "Google API libraries not installed. Run:\n"
                "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
        
        creds = None
        
        # Load existing token
        if self.token_file.exists():
            with open(self.token_file, 'rb') as f:
                creds = pickle.load(f)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    raise GmailError(
                        f"Google credentials file not found: {self.credentials_file}\n"
                        "Run /setup-google to configure Google API access."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, 'wb') as f:
                pickle.dump(creds, f)
        
        return creds
    
    def _get_service(self):
        """Get Gmail API service."""
        if self._service is None:
            try:
                from googleapiclient.discovery import build
            except ImportError:
                raise GmailError("Google API client not installed. Run: pip install google-api-python-client")
            
            creds = self._get_credentials()
            self._service = build('gmail', 'v1', credentials=creds)
        return self._service
    
    def test_connection(self) -> bool:
        """Test if Gmail connection works."""
        try:
            service = self._get_service()
            service.users().getProfile(userId='me').execute()
            return True
        except Exception:
            return False
    
    def send_email(self, to: str, subject: str, body: str, html: bool = False) -> dict:
        """Send an email."""
        from email.mime.text import MIMEText
        
        message = MIMEText(body, 'html' if html else 'plain')
        message['to'] = to
        message['subject'] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service = self._get_service()
        return service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
    
    def create_draft(self, to: str, subject: str, body: str, html: bool = False) -> dict:
        """Create an email draft."""
        from email.mime.text import MIMEText
        
        message = MIMEText(body, 'html' if html else 'plain')
        message['to'] = to
        message['subject'] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service = self._get_service()
        return service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw}}
        ).execute()
    
    def send_followup(self, recipient: dict, meeting: dict, tasks: List[dict]) -> dict:
        """Send a follow-up email with action items."""
        first_name = recipient.get('name', 'there').split()[0]
        
        task_list = "\n".join([
            f"- [ ] {t['description']}" + (f" - Due: {t['due']}" if t.get('due') else "")
            for t in tasks
        ])
        
        body = f"""Hi {first_name},

Thanks for joining the {meeting.get('title', 'meeting')} on {meeting.get('date', 'recently')}.

Here's a summary of your action items:

{task_list}

{meeting.get('summary', '')}

Let me know if you have any questions!

Best regards
"""
        
        return self.send_email(
            to=recipient.get('email'),
            subject=f"Follow-up: {meeting.get('title', 'Meeting')} - Action Items",
            body=body
        )


class GmailError(Exception):
    pass


# =============================================================================
# Google Calendar Integration
# =============================================================================

class CalendarClient:
    """Direct Google Calendar API client."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    def __init__(self, credentials_file: str, token_file: str = None):
        self.credentials_file = Path(credentials_file).expanduser()
        self.token_file = Path(token_file or '~/.hyperflow/calendar_token.pickle').expanduser()
        self._service = None
    
    def _get_credentials(self):
        """Get or refresh OAuth credentials."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            raise CalendarError(
                "Google API libraries not installed. Run:\n"
                "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
        
        creds = None
        
        if self.token_file.exists():
            with open(self.token_file, 'rb') as f:
                creds = pickle.load(f)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    raise CalendarError(
                        f"Google credentials file not found: {self.credentials_file}\n"
                        "Run /setup-google to configure Google API access."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, 'wb') as f:
                pickle.dump(creds, f)
        
        return creds
    
    def _get_service(self):
        """Get Calendar API service."""
        if self._service is None:
            try:
                from googleapiclient.discovery import build
            except ImportError:
                raise CalendarError("Google API client not installed.")
            
            creds = self._get_credentials()
            self._service = build('calendar', 'v3', credentials=creds)
        return self._service
    
    def test_connection(self) -> bool:
        """Test if Calendar connection works."""
        try:
            service = self._get_service()
            service.calendarList().list().execute()
            return True
        except Exception:
            return False
    
    def list_calendars(self) -> List[dict]:
        """List available calendars."""
        service = self._get_service()
        result = service.calendarList().list().execute()
        return result.get('items', [])
    
    def find_events(self, start_time: datetime, end_time: datetime = None, 
                    calendar_id: str = 'primary', query: str = None) -> List[dict]:
        """Find events in a time range."""
        service = self._get_service()
        
        if end_time is None:
            end_time = start_time + timedelta(hours=2)
        
        params = {
            'calendarId': calendar_id,
            'timeMin': start_time.isoformat() + 'Z',
            'timeMax': end_time.isoformat() + 'Z',
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        if query:
            params['q'] = query
        
        result = service.events().list(**params).execute()
        return result.get('items', [])
    
    def update_event(self, event_id: str, updates: dict, calendar_id: str = 'primary') -> dict:
        """Update an event."""
        service = self._get_service()
        
        # Get current event
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        # Apply updates
        for key, value in updates.items():
            event[key] = value
        
        return service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()
    
    def add_meeting_notes(self, event_id: str, meeting: dict, calendar_id: str = 'primary') -> dict:
        """Add meeting notes to a calendar event."""
        notes_section = f"""
---
📝 Meeting Notes: {meeting.get('vault_path', '')}

Summary: {meeting.get('summary', 'No summary available')[:500]}

Action Items:
{chr(10).join(['- ' + t for t in meeting.get('action_items', [])])}
---
"""
        
        service = self._get_service()
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        current_description = event.get('description', '')
        if '📝 Meeting Notes' not in current_description:
            event['description'] = current_description + notes_section
        
        return service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()
    
    def match_event_to_meeting(self, meeting_datetime: datetime, meeting_title: str,
                                attendees: List[str] = None) -> Optional[dict]:
        """Find the calendar event that best matches a meeting."""
        # Search 1 hour before to 1 hour after meeting time
        events = self.find_events(
            start_time=meeting_datetime - timedelta(hours=1),
            end_time=meeting_datetime + timedelta(hours=2)
        )
        
        if not events:
            return None
        
        # Score each event
        best_match = None
        best_score = 0
        
        for event in events:
            score = 0
            
            # Time proximity
            event_start = datetime.fromisoformat(
                event['start'].get('dateTime', event['start'].get('date')).replace('Z', '+00:00')
            )
            time_diff = abs((event_start - meeting_datetime).total_seconds() / 60)
            if time_diff <= 30:
                score += 5
            elif time_diff <= 60:
                score += 3
            
            # Title similarity
            event_title = event.get('summary', '').lower()
            meeting_words = set(meeting_title.lower().split())
            title_matches = sum(1 for word in meeting_words if word in event_title and len(word) > 3)
            score += title_matches * 2
            
            # Attendee match
            if attendees:
                event_attendees = [a.get('email', '').lower() for a in event.get('attendees', [])]
                attendee_matches = sum(1 for a in attendees if a.lower() in event_attendees)
                score += attendee_matches * 2
            
            if score > best_score:
                best_score = score
                best_match = event
        
        return best_match if best_score >= 4 else None


class CalendarError(Exception):
    pass


# =============================================================================
# Unified Integration Manager
# =============================================================================

class HyperflowIntegrations:
    """
    Unified interface for all Hyperflow integrations.
    
    Usage:
        integrations = HyperflowIntegrations()
        
        # Test all connections
        status = integrations.test_all()
        
        # Use individual services
        integrations.notion.create_task(...)
        integrations.gmail.send_email(...)
        integrations.calendar.find_events(...)
    """
    
    def __init__(self, config: HyperflowConfig = None):
        self.config = config or HyperflowConfig.load()
        
        self._notion = None
        self._gmail = None
        self._calendar = None
    
    @property
    def notion(self) -> NotionClient:
        """Get Notion client."""
        if self._notion is None:
            if not self.config.notion.token:
                raise IntegrationError("Notion token not configured. Add NOTION_TOKEN to config.")
            self._notion = NotionClient(self.config.notion.token)
        return self._notion
    
    @property
    def gmail(self) -> GmailClient:
        """Get Gmail client."""
        if self._gmail is None:
            if not self.config.google.credentials_file:
                raise IntegrationError("Google credentials not configured. Run /setup-google.")
            self._gmail = GmailClient(
                self.config.google.credentials_file,
                self.config.google.token_file or None
            )
        return self._gmail
    
    @property
    def calendar(self) -> CalendarClient:
        """Get Calendar client."""
        if self._calendar is None:
            if not self.config.google.credentials_file:
                raise IntegrationError("Google credentials not configured. Run /setup-google.")
            self._calendar = CalendarClient(
                self.config.google.credentials_file,
                self.config.google.token_file or None
            )
        return self._calendar
    
    def test_all(self) -> Dict[str, bool]:
        """Test all integrations and return status."""
        status = {}
        
        # Test Notion
        try:
            status['notion'] = self.notion.test_connection() if self.config.notion.token else False
        except Exception as e:
            status['notion'] = False
            status['notion_error'] = str(e)
        
        # Test Gmail
        try:
            status['gmail'] = self.gmail.test_connection() if self.config.google.credentials_file else False
        except Exception as e:
            status['gmail'] = False
            status['gmail_error'] = str(e)
        
        # Test Calendar
        try:
            status['calendar'] = self.calendar.test_connection() if self.config.google.credentials_file else False
        except Exception as e:
            status['calendar'] = False
            status['calendar_error'] = str(e)
        
        return status
    
    def sync_task_to_notion(self, project_slug: str, task: dict) -> Optional[dict]:
        """
        Sync a task to Notion for a specific project.
        
        Args:
            project_slug: Project identifier (e.g., 'opencivics')
            task: Task data with title, assignee, due_date, source
        
        Returns:
            Created Notion page or None if project not configured
        """
        project = self.config.projects.get(project_slug)
        if not project or not project.notion_database:
            return None
        
        # Check for duplicate
        if task.get('source'):
            existing = self.notion.find_duplicate_task(
                project.notion_database,
                task['source']
            )
            if existing:
                return None  # Skip duplicate
        
        return self.notion.create_task(project.notion_database, task)
    
    def send_followup_emails(self, meeting: dict, tasks_by_person: Dict[str, List[dict]], 
                             draft_only: bool = True) -> List[dict]:
        """
        Send follow-up emails to meeting participants.
        
        Args:
            meeting: Meeting data with title, date, summary
            tasks_by_person: Dict mapping person email to their tasks
            draft_only: If True, create drafts instead of sending
        
        Returns:
            List of sent/drafted email results
        """
        results = []
        
        for email, tasks in tasks_by_person.items():
            recipient = {'email': email, 'name': email.split('@')[0]}
            
            if draft_only:
                result = self.gmail.create_draft(
                    to=email,
                    subject=f"Follow-up: {meeting.get('title', 'Meeting')} - Action Items",
                    body=self._format_followup_body(recipient, meeting, tasks)
                )
            else:
                result = self.gmail.send_followup(recipient, meeting, tasks)
            
            results.append({'email': email, 'result': result, 'status': 'draft' if draft_only else 'sent'})
        
        return results
    
    def _format_followup_body(self, recipient: dict, meeting: dict, tasks: List[dict]) -> str:
        """Format follow-up email body."""
        first_name = recipient.get('name', 'there').split()[0]
        
        task_list = "\n".join([
            f"- [ ] {t.get('description', t.get('title', 'Task'))}" + 
            (f" - Due: {t['due']}" if t.get('due') else "")
            for t in tasks
        ])
        
        return f"""Hi {first_name},

Thanks for joining the {meeting.get('title', 'meeting')} on {meeting.get('date', 'recently')}.

Here's a summary of your action items:

{task_list}

{meeting.get('summary', '')}

Let me know if you have any questions!

Best regards
"""
    
    def link_meeting_to_calendar(self, meeting: dict) -> Optional[dict]:
        """
        Find and link a meeting to its calendar event.
        
        Args:
            meeting: Meeting data with date, title, participants
        
        Returns:
            Updated calendar event or None if no match
        """
        meeting_dt = datetime.fromisoformat(meeting.get('date', '').replace('Z', '+00:00'))
        
        event = self.calendar.match_event_to_meeting(
            meeting_datetime=meeting_dt,
            meeting_title=meeting.get('title', ''),
            attendees=meeting.get('participant_emails', [])
        )
        
        if event:
            return self.calendar.add_meeting_notes(event['id'], meeting)
        
        return None


class IntegrationError(Exception):
    pass


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI for testing integrations."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hyperflow Integrations')
    parser.add_argument('--test', action='store_true', help='Test all integrations')
    parser.add_argument('--test-notion', action='store_true', help='Test Notion connection')
    parser.add_argument('--test-gmail', action='store_true', help='Test Gmail connection')
    parser.add_argument('--test-calendar', action='store_true', help='Test Calendar connection')
    args = parser.parse_args()
    
    integrations = HyperflowIntegrations()
    
    if args.test or args.test_notion or args.test_gmail or args.test_calendar:
        print("🔄 Testing Hyperflow Integrations\n" + "=" * 40)
        
        if args.test or args.test_notion:
            try:
                if integrations.config.notion.token:
                    result = integrations.notion.test_connection()
                    print(f"{'✅' if result else '❌'} Notion: {'Connected' if result else 'Failed'}")
                else:
                    print("⚠️ Notion: Not configured")
            except Exception as e:
                print(f"❌ Notion: {e}")
        
        if args.test or args.test_gmail:
            try:
                if integrations.config.google.credentials_file:
                    result = integrations.gmail.test_connection()
                    print(f"{'✅' if result else '❌'} Gmail: {'Connected' if result else 'Failed'}")
                else:
                    print("⚠️ Gmail: Not configured")
            except Exception as e:
                print(f"❌ Gmail: {e}")
        
        if args.test or args.test_calendar:
            try:
                if integrations.config.google.credentials_file:
                    result = integrations.calendar.test_connection()
                    print(f"{'✅' if result else '❌'} Calendar: {'Connected' if result else 'Failed'}")
                else:
                    print("⚠️ Calendar: Not configured")
            except Exception as e:
                print(f"❌ Calendar: {e}")
        
        print("=" * 40)


if __name__ == '__main__':
    main()

