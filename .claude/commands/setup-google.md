# Setup Google APIs

Automated setup for Gmail and Calendar integration.

## Purpose
Guide the user through Google Cloud Console OAuth setup with minimal friction.

## Prerequisites
- Google account
- Python 3.8+ installed
- Internet connection

## Workflow

### Step 1: Check Current Status

First, check what's already configured:

```bash
python scripts/setup_google.py --test
```

If everything passes, inform user setup is already complete.

### Step 2: Run Setup Wizard

If setup needed:

```bash
python scripts/setup_google.py
```

The script will:
1. Install required Python packages (if missing)
2. Look for existing credentials in common locations
3. Guide through Google Cloud Console if needed
4. Authenticate with Gmail and Calendar
5. Update configuration files

### Step 3: Assist with Google Cloud Console

If user needs to create new credentials, guide them:

#### Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Select a project" → "New Project"
3. Name it "Hyperflow" (or anything you like)
4. Click "Create"

#### Enable APIs
1. Go to "APIs & Services" → "Library"
2. Search for "Gmail API" → Click → Enable
3. Search for "Google Calendar API" → Click → Enable

#### Create OAuth Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "+ CREATE CREDENTIALS" → "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - User Type: External (or Internal for Workspace)
   - App name: "Hyperflow"
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Skip for now
   - Test users: Add your email
   - Save and continue
4. Back to Credentials → "+ CREATE CREDENTIALS" → "OAuth client ID"
5. Application type: **Desktop app**
6. Name: "Hyperflow Desktop"
7. Click "Create"
8. Click "Download JSON"
9. Save to Downloads folder

### Step 4: Complete Authentication

After user has credentials JSON:

```bash
python scripts/setup_google.py --credentials ~/Downloads/client_secret*.json
```

This will:
1. Copy credentials to `~/.hyperflow/google-oauth.json`
2. Open browser for Gmail OAuth consent
3. Open browser for Calendar OAuth consent
4. Save tokens for future use

### Step 5: Verify Setup

```bash
python scripts/setup_google.py --test
```

Expected output:
```
✅ Credentials file: Valid OAuth credentials
✅ Gmail: Connected (user@example.com)
✅ Calendar: Connected (3 calendars found)
```

## Troubleshooting

### "Access blocked" error
- OAuth consent screen not configured
- Fix: Go to "OAuth consent screen" in Google Cloud Console
- Add your email as a test user

### "Credentials file not found"
- JSON wasn't downloaded or saved correctly
- Fix: Re-download from Google Cloud Console → Credentials

### "Invalid client" error
- Wrong credential type (web instead of desktop)
- Fix: Create new OAuth client ID with "Desktop app" type

### "Token expired"
- Refresh token is invalid
- Fix: Delete `~/.hyperflow/gmail_token.pickle` and re-authenticate

### Browser doesn't open
- Running in headless environment
- Fix: Copy the auth URL and open manually in browser

## Post-Setup

After successful setup, you can use:

1. **Link meetings to calendar**:
   ```
   /link-calendar
   ```

2. **Send follow-up emails**:
   ```
   /send-followups
   ```

3. **Run full pipeline**:
   ```
   /run-pipeline
   ```

## Security Notes

- OAuth tokens are stored locally in `~/.hyperflow/`
- Tokens provide limited access (send email, manage calendar)
- Tokens can be revoked at [Google Security Settings](https://myaccount.google.com/permissions)
- Credentials JSON contains your client secret - keep it private

## Quick Reference

| File | Location | Purpose |
|------|----------|---------|
| google-oauth.json | ~/.hyperflow/ | OAuth client credentials |
| gmail_token.pickle | ~/.hyperflow/ | Gmail access token |
| calendar_token.pickle | ~/.hyperflow/ | Calendar access token |

