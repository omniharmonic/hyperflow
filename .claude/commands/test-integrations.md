# Test Hyperflow Integrations

Validate all configured integrations and provide diagnostic information.

## Purpose
Run comprehensive tests on all Hyperflow integrations (Notion, Gmail, Calendar, Meetily) to verify configuration and connectivity.

## Workflow

### Step 1: Check Configuration Files

Look for configuration in order of priority:
1. `.hyperflow/config.yaml` in vault root
2. `.hyperflow.env` in vault root
3. Environment variables

Report which configuration sources are found and loaded.

### Step 2: Test Meetily Database

```bash
python scripts/sync_meetily.py --list --limit 3
```

Expected output:
- ✅ Database found and accessible
- Recent meetings listed
- ❌ If failed, check MEETILY_DB_PATH

### Step 3: Test Notion Integration

```bash
python scripts/integrations.py --test-notion
```

Verify:
- [ ] NOTION_TOKEN is set
- [ ] Token is valid (can reach API)
- [ ] Can list databases
- [ ] Project databases are accessible

If failed, provide specific fix:
```
❌ Notion: Token not configured
   Fix: Add NOTION_TOKEN to .hyperflow.env or .hyperflow/config.yaml
   Get token from: https://www.notion.so/my-integrations
```

### Step 4: Test Gmail Integration

```bash
python scripts/integrations.py --test-gmail
```

Verify:
- [ ] Credentials file exists (~/.hyperflow/google-oauth.json)
- [ ] Token file exists (or can be created)
- [ ] Can authenticate with Gmail API
- [ ] Can access user's email address

If failed, provide specific fix:
```
❌ Gmail: OAuth credentials not found
   Fix: Run `python scripts/setup_google.py` for guided setup
```

### Step 5: Test Calendar Integration

```bash
python scripts/integrations.py --test-calendar
```

Verify:
- [ ] Credentials file exists
- [ ] Token file exists (or can be created)  
- [ ] Can authenticate with Calendar API
- [ ] Can list calendars

### Step 6: Test Project Configurations

For each project in `projects/*/PROJECT.md`:
- [ ] Check if PROJECT.md exists and is valid YAML frontmatter
- [ ] If notion_tasks_database is set, verify database is accessible
- [ ] Check team member emails are valid format

### Step 7: Generate Report

Output a comprehensive status report:

```
╔═══════════════════════════════════════════════════╗
║         Hyperflow Integration Status              ║
╚═══════════════════════════════════════════════════╝

Configuration:
  ✅ .hyperflow.env found
  ✅ .hyperflow/config.yaml found
  ⚠️  Some values from environment variables

Core Integrations:
  ✅ Meetily Database: Connected (15 meetings)
  ✅ Notion API: Connected (token valid)
  ✅ Gmail API: Connected (user@example.com)
  ⚠️  Calendar API: Not configured

Project Status:
  ✅ opencivics: Notion database accessible
  ⚠️  another-project: No Notion database configured

Ready for:
  ✅ /sync-meetily - Sync meeting recordings
  ✅ /ingest-meetings - Process and enrich meetings
  ✅ /sync-tasks - Sync tasks to people profiles
  ✅ /sync-notion - Push tasks to Notion
  ⚠️  /link-calendar - Needs Calendar API setup
  ⚠️  /send-followups - Needs Gmail API setup

To complete setup:
  1. Run: python scripts/setup_google.py
  2. This will configure Gmail and Calendar APIs
```

## Quick Fix Commands

Provide copy-paste commands for common issues:

### Missing Notion Token
```bash
# Add to .hyperflow.env:
echo 'NOTION_TOKEN="your-token-here"' >> .hyperflow.env
```

### Missing Google Setup
```bash
python scripts/setup_google.py
```

### Meetily Database Not Found
```bash
# Manually specify path:
echo 'MEETILY_DB_PATH="~/Library/Application Support/com.meetily.ai/meeting_minutes.sqlite"' >> .hyperflow.env
```

## Response Format

Always provide:
1. **Status Summary** - Quick pass/fail for each integration
2. **Detailed Diagnostics** - Specific error messages and file locations
3. **Actionable Fixes** - Exact commands to resolve issues
4. **Next Steps** - What the user can do once fixed

## Example Outputs

### All Working:
```
🎉 All integrations healthy!

You're ready to run the full pipeline:
  /run-pipeline

Or individual commands:
  /sync-meetily → /ingest-meetings → /sync-notion
```

### Partial Setup:
```
⚠️ Some integrations need attention

Working:
  ✅ Meetily, Notion

Needs Setup:
  ❌ Gmail - Run: python scripts/setup_google.py
  ❌ Calendar - Run: python scripts/setup_google.py

You can still use:
  /sync-meetily, /ingest-meetings, /sync-notion, /sync-tasks
```

