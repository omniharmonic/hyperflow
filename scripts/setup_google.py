#!/usr/bin/env python3
"""
Google API Setup Script for Hyperflow

Automates the OAuth setup process for Gmail and Calendar integration.

Usage:
    python scripts/setup_google.py
    python scripts/setup_google.py --credentials ~/Downloads/client_secret.json
    python scripts/setup_google.py --test

What it does:
    1. Checks for existing credentials
    2. Guides you through getting credentials from Google Cloud Console
    3. Sets up OAuth tokens for Gmail and Calendar
    4. Tests the connections
    5. Updates configuration files
"""

import os
import sys
import json
import pickle
import shutil
import webbrowser
from pathlib import Path
from typing import Optional, Tuple

# Color output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def success(msg): print(f"{Colors.GREEN}✅ {msg}{Colors.END}")
def warning(msg): print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")
def error(msg): print(f"{Colors.RED}❌ {msg}{Colors.END}")
def info(msg): print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")
def header(msg): print(f"\n{Colors.BOLD}{msg}{Colors.END}")


# Configuration
HYPERFLOW_DIR = Path.home() / '.hyperflow'
CREDENTIALS_FILE = HYPERFLOW_DIR / 'google-oauth.json'
GMAIL_TOKEN_FILE = HYPERFLOW_DIR / 'gmail_token.pickle'
CALENDAR_TOKEN_FILE = HYPERFLOW_DIR / 'calendar_token.pickle'

GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
]

CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
]

GOOGLE_CLOUD_CONSOLE_URL = "https://console.cloud.google.com"


def check_dependencies() -> bool:
    """Check if required Google API packages are installed."""
    try:
        import google.oauth2.credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        return True
    except ImportError:
        return False


def install_dependencies():
    """Install required packages."""
    header("Installing Google API dependencies...")
    import subprocess
    
    packages = [
        'google-auth',
        'google-auth-oauthlib', 
        'google-auth-httplib2',
        'google-api-python-client'
    ]
    
    subprocess.run([sys.executable, '-m', 'pip', 'install'] + packages, check=True)
    success("Dependencies installed!")


def find_credentials_file() -> Optional[Path]:
    """Look for credentials file in common locations."""
    locations = [
        CREDENTIALS_FILE,
        Path.home() / 'Downloads' / 'credentials.json',
        Path.home() / 'Downloads' / 'client_secret.json',
        Path.home() / '.gmail-mcp' / 'gcp-oauth.keys.json',
        Path.cwd() / 'credentials.json',
        Path.cwd() / 'client_secret.json',
    ]
    
    # Also check Downloads for any Google OAuth file
    downloads = Path.home() / 'Downloads'
    if downloads.exists():
        for f in downloads.glob('client_secret_*.json'):
            locations.insert(1, f)
    
    for loc in locations:
        if loc.exists():
            return loc
    
    return None


def validate_credentials_file(path: Path) -> Tuple[bool, str]:
    """Validate that a credentials file is valid Google OAuth JSON."""
    try:
        with open(path) as f:
            data = json.load(f)
        
        # Check for OAuth 2.0 client structure
        if 'installed' in data:
            client_data = data['installed']
        elif 'web' in data:
            return False, "This is a 'web' credential. You need 'Desktop app' credentials."
        else:
            return False, "Invalid credentials file format."
        
        required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
        missing = [f for f in required_fields if f not in client_data]
        
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        
        return True, "Valid OAuth credentials"
        
    except json.JSONDecodeError:
        return False, "Not a valid JSON file"
    except Exception as e:
        return False, str(e)


def setup_credentials(credentials_path: Optional[Path] = None) -> bool:
    """Set up Google OAuth credentials."""
    header("Setting up Google OAuth credentials")
    
    HYPERFLOW_DIR.mkdir(exist_ok=True)
    
    # Check if credentials already exist and are valid
    if CREDENTIALS_FILE.exists():
        valid, msg = validate_credentials_file(CREDENTIALS_FILE)
        if valid:
            info(f"Existing credentials found at {CREDENTIALS_FILE}")
            use_existing = input("Use existing credentials? [Y/n]: ").strip().lower()
            if use_existing != 'n':
                success("Using existing credentials")
                return True
    
    # Look for credentials file
    if credentials_path and credentials_path.exists():
        source_file = credentials_path
    else:
        source_file = find_credentials_file()
    
    if source_file:
        valid, msg = validate_credentials_file(source_file)
        if valid:
            info(f"Found credentials at: {source_file}")
            use_found = input("Use these credentials? [Y/n]: ").strip().lower()
            if use_found != 'n':
                shutil.copy(source_file, CREDENTIALS_FILE)
                success(f"Credentials copied to {CREDENTIALS_FILE}")
                return True
        else:
            warning(f"Found file but invalid: {msg}")
    
    # Guide user to create credentials
    header("No valid credentials found. Let's create them!")
    print("""
To use Gmail and Calendar integration, you need to:

1. Go to Google Cloud Console: https://console.cloud.google.com
2. Create a new project (or select existing)
3. Enable APIs:
   - Search for "Gmail API" and enable it
   - Search for "Google Calendar API" and enable it
4. Create OAuth credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "+ CREATE CREDENTIALS" → "OAuth client ID"
   - Choose "Desktop app" as application type
   - Name it "Hyperflow"
   - Click "Create"
5. Download the JSON file and save it

""")
    
    open_browser = input("Open Google Cloud Console in browser? [Y/n]: ").strip().lower()
    if open_browser != 'n':
        webbrowser.open(GOOGLE_CLOUD_CONSOLE_URL)
    
    print("\nAfter downloading, enter the path to your credentials file:")
    while True:
        creds_input = input("Path to credentials.json (or 'skip' to continue later): ").strip()
        
        if creds_input.lower() == 'skip':
            warning("Skipping credentials setup. Gmail/Calendar won't work.")
            return False
        
        creds_path = Path(creds_input).expanduser()
        if not creds_path.exists():
            error(f"File not found: {creds_path}")
            continue
        
        valid, msg = validate_credentials_file(creds_path)
        if not valid:
            error(f"Invalid credentials: {msg}")
            continue
        
        shutil.copy(creds_path, CREDENTIALS_FILE)
        success(f"Credentials saved to {CREDENTIALS_FILE}")
        return True


def authenticate_gmail() -> bool:
    """Authenticate with Gmail API."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    header("Authenticating Gmail...")
    
    if GMAIL_TOKEN_FILE.exists():
        info("Existing Gmail token found")
        reauth = input("Re-authenticate Gmail? [y/N]: ").strip().lower()
        if reauth != 'y':
            return True
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE), GMAIL_SCOPES
        )
        
        info("Opening browser for Gmail authentication...")
        creds = flow.run_local_server(port=0)
        
        with open(GMAIL_TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
        
        success("Gmail authenticated!")
        return True
        
    except Exception as e:
        error(f"Gmail authentication failed: {e}")
        return False


def authenticate_calendar() -> bool:
    """Authenticate with Calendar API."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    header("Authenticating Google Calendar...")
    
    if CALENDAR_TOKEN_FILE.exists():
        info("Existing Calendar token found")
        reauth = input("Re-authenticate Calendar? [y/N]: ").strip().lower()
        if reauth != 'y':
            return True
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE), CALENDAR_SCOPES
        )
        
        info("Opening browser for Calendar authentication...")
        creds = flow.run_local_server(port=0)
        
        with open(CALENDAR_TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
        
        success("Calendar authenticated!")
        return True
        
    except Exception as e:
        error(f"Calendar authentication failed: {e}")
        return False


def test_gmail_connection() -> bool:
    """Test Gmail API connection."""
    from googleapiclient.discovery import build
    
    if not GMAIL_TOKEN_FILE.exists():
        return False
    
    try:
        with open(GMAIL_TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)
        
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        
        info(f"Gmail connected as: {profile.get('emailAddress')}")
        return True
        
    except Exception as e:
        error(f"Gmail test failed: {e}")
        return False


def test_calendar_connection() -> bool:
    """Test Calendar API connection."""
    from googleapiclient.discovery import build
    
    if not CALENDAR_TOKEN_FILE.exists():
        return False
    
    try:
        with open(CALENDAR_TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)
        
        service = build('calendar', 'v3', credentials=creds)
        calendars = service.calendarList().list(maxResults=3).execute()
        
        num_calendars = len(calendars.get('items', []))
        info(f"Calendar connected. Found {num_calendars} calendars.")
        return True
        
    except Exception as e:
        error(f"Calendar test failed: {e}")
        return False


def update_config():
    """Update Hyperflow configuration files."""
    header("Updating configuration...")
    
    # Find vault .hyperflow.env
    vault_env_path = None
    for path in [Path.cwd(), Path.cwd().parent, Path(__file__).parent.parent]:
        if (path / '.hyperflow.env').exists():
            vault_env_path = path / '.hyperflow.env'
            break
    
    if vault_env_path:
        # Update .hyperflow.env
        content = vault_env_path.read_text()
        
        if 'GOOGLE_CREDENTIALS_FILE' not in content:
            with open(vault_env_path, 'a') as f:
                f.write(f'\n# Google API credentials\n')
                f.write(f'GOOGLE_CREDENTIALS_FILE="{CREDENTIALS_FILE}"\n')
            success(f"Updated {vault_env_path}")
        else:
            info("GOOGLE_CREDENTIALS_FILE already in config")
    
    # Create/update .hyperflow/config.yaml
    config_yaml = HYPERFLOW_DIR / 'config.yaml'
    
    if not config_yaml.exists():
        config = {
            'google': {
                'credentials_file': str(CREDENTIALS_FILE),
                'token_file': str(GMAIL_TOKEN_FILE),  # Shared token location
            },
            'notion': {
                'token': '',
                'default_workspace': '',
            },
            'meetily_db_path': '',
            'vault_path': '',
            'projects': {},
        }
        
        import yaml
        with open(config_yaml, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        success(f"Created {config_yaml}")


def print_summary():
    """Print setup summary."""
    header("Setup Summary")
    print("=" * 50)
    
    checks = [
        ("Google credentials", CREDENTIALS_FILE.exists()),
        ("Gmail token", GMAIL_TOKEN_FILE.exists()),
        ("Calendar token", CALENDAR_TOKEN_FILE.exists()),
    ]
    
    all_good = True
    for name, status in checks:
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}: {'OK' if status else 'Missing'}")
        if not status:
            all_good = False
    
    print("=" * 50)
    
    if all_good:
        success("\nGoogle APIs are fully configured!")
        print("\nYou can now use:")
        print("  - /link-calendar  - Link meetings to calendar events")
        print("  - /send-followups - Send follow-up emails")
        print("  - /run-pipeline   - Full automated workflow")
    else:
        warning("\nSetup incomplete. Some features may not work.")
        print("\nRun this script again to complete setup:")
        print(f"  python {__file__}")


def test_only():
    """Run tests without setup."""
    header("Testing Google API Integrations")
    
    print("\n🔄 Running integration tests...\n")
    
    # Check credentials
    if CREDENTIALS_FILE.exists():
        valid, msg = validate_credentials_file(CREDENTIALS_FILE)
        if valid:
            success(f"Credentials file: {msg}")
        else:
            error(f"Credentials file: {msg}")
    else:
        error(f"Credentials file not found: {CREDENTIALS_FILE}")
    
    # Test Gmail
    print()
    if test_gmail_connection():
        success("Gmail: Connected")
    else:
        error("Gmail: Not connected")
    
    # Test Calendar
    print()
    if test_calendar_connection():
        success("Calendar: Connected")
    else:
        error("Calendar: Not connected")
    
    print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Set up Google APIs for Hyperflow')
    parser.add_argument('--credentials', '-c', type=Path, 
                        help='Path to OAuth credentials JSON')
    parser.add_argument('--test', '-t', action='store_true',
                        help='Test connections only')
    parser.add_argument('--skip-browser', action='store_true',
                        help='Skip opening browser for OAuth')
    args = parser.parse_args()
    
    print(f"""
{Colors.BOLD}╔═══════════════════════════════════════════════════╗
║       Hyperflow Google API Setup Wizard           ║
╚═══════════════════════════════════════════════════╝{Colors.END}
""")
    
    # Test only mode
    if args.test:
        if not check_dependencies():
            error("Google API packages not installed.")
            print("Run: pip install google-auth google-auth-oauthlib google-api-python-client")
            sys.exit(1)
        test_only()
        sys.exit(0)
    
    # Check/install dependencies
    if not check_dependencies():
        try:
            install_dependencies()
        except Exception as e:
            error(f"Failed to install dependencies: {e}")
            sys.exit(1)
    
    # Setup credentials
    if not setup_credentials(args.credentials):
        warning("Credentials setup incomplete")
    elif CREDENTIALS_FILE.exists():
        # Authenticate Gmail
        if not authenticate_gmail():
            warning("Gmail authentication skipped")
        
        # Authenticate Calendar  
        if not authenticate_calendar():
            warning("Calendar authentication skipped")
    
    # Update config files
    try:
        update_config()
    except Exception as e:
        warning(f"Config update failed: {e}")
    
    # Print summary
    print_summary()


if __name__ == '__main__':
    main()

