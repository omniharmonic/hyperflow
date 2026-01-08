---
description: Create a new project with guided setup questions
allowed-tools: Read, Write, Bash
argument-hint: [optional: project name to skip first question]
---

# Add New Project

Interactively create a new project folder with all necessary files.

## Workflow

### Step 1: Get Project Name

If not provided as argument, ask:
> **What's the project name?** (e.g., "OpenCivics", "Client Website Redesign")

Generate a slug from the name (lowercase, hyphens, no special chars).
Example: "OpenCivics" → `opencivics`

### Step 2: Get Aliases

Ask:
> **What are some aliases or short names people use for this project?**
> (comma-separated, e.g., "oc, civic project, the civics thing")

These help match meetings where people don't use the full name.

### Step 3: Get Team Members

Ask:
> **Who are the core team members?**
> List each person with their email and role. Format:
> - Name, email@example.com, Role
> 
> Example:
> - Benjamin Life, ben@opencivics.co, Lead
> - Jane Doe, jane@example.com, Advisor

### Step 4: Get Keywords

Ask:
> **What keywords or terms are unique to this project?**
> (comma-separated, e.g., "TrustGraph, attestation, governance")
> 
> These help auto-route meetings to this project.

### Step 5: Get Links (Optional)

Ask:
> **Any links to add?** (optional, press Enter to skip)
> - Repository URL:
> - Documentation URL:
> - Shared Drive URL:

### Step 6: Create Project Structure

Create the following files:

**`projects/{slug}/PROJECT.md`:**
```markdown
---
name: "{Project Name}"
aliases:
  - "{alias1}"
  - "{alias2}"
status: active
tags:
  - project
---

# {Project Name}

## Overview

<!-- Add project description -->

## Team

| Name | Email | Role |
|------|-------|------|
| {Name1} | {email1} | {role1} |
| {Name2} | {email2} | {role2} |

## Keywords

Keywords for auto-matching meetings to this project:

- {keyword1}
- {keyword2}
- {keyword3}

## Links

- **Repository:** {repo_url or empty}
- **Docs:** {docs_url or empty}
- **Shared Drive:** {drive_url or empty}

## Recent Meetings

\```dataview
TABLE date, themes
FROM "projects/{slug}/meetings"
SORT date DESC
LIMIT 10
\```
```

**`projects/{slug}/index.md`:**
```markdown
# {Project Name}

> Link to this project: `[[projects/{slug}/index]]`

## Quick Links

- [[projects/{slug}/PROJECT|Project Context & Team]]

## Overview

<!-- Add project overview here -->

## Key Decisions

<!-- Track major decisions -->

## Resources

<!-- Add links to resources -->
```

**Create directories:**
- `projects/{slug}/meetings/`
- `projects/{slug}/shared/` (optional, for Google Drive sync)

### Step 7: Confirm Creation

Show summary:
```
✅ Created project: {Project Name}

📁 projects/{slug}/
   ├── PROJECT.md      ← Team, keywords, aliases
   ├── index.md        ← Project overview
   ├── meetings/       ← Meeting notes will go here
   └── shared/         ← For collaboration (optional)

Team: {count} members
Keywords: {keyword list}
Aliases: {alias list}

Meetings mentioning these keywords/people will auto-route here.
```

## Example Session

```
User: /add-project

Claude: What's the project name?

User: Localism Fund

Claude: What are some aliases or short names? (comma-separated)

User: localism, the fund, LF

Claude: Who are the core team members?
Format: Name, email, Role (one per line)

User: 
- Sarah Chen, sarah@localismfund.org, Director
- Marcus Johnson, marcus@localismfund.org, Program Lead

Claude: What keywords are unique to this project? (comma-separated)

User: community investment, local economy, regenerative finance, bioregion

Claude: Any links to add? (Enter to skip each)
Repository URL: 
User: https://github.com/localism-fund/platform

Documentation URL:
User: [Enter]

Shared Drive URL:
User: https://drive.google.com/drive/folders/xxx

Claude: ✅ Created project: Localism Fund

📁 projects/localism-fund/
   ├── PROJECT.md
   ├── index.md  
   ├── meetings/
   └── shared/

Team: 2 members (Sarah Chen, Marcus Johnson)
Keywords: community investment, local economy, regenerative finance, bioregion
Aliases: localism, the fund, LF

Meetings mentioning these will auto-route to this project!
```

## Notes

- Slug is auto-generated from project name
- All fields can be edited later in PROJECT.md
- The dataview query in PROJECT.md requires the Dataview plugin
- Empty links can be filled in later

