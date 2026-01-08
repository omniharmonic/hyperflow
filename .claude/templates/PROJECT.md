---
project: "Project Name"
aliases:
  - project-short-name
  - alternative-name
notion_workspace: https://notion.so/workspace/...
notion_tasks_database: abc123-def456-7890
status: active
team:
  - name: Benjamin
    email: benjamin@example.org
    role: Lead
  - name: Collaborator Name
    email: collab@example.org
    role: Contributor
keywords:
  - keyword-one
  - keyword-two
  - topic-area
related_projects:
  - "[[projects/related-project/index]]"
---

# Project Name

## Overview

Brief description of what this project is about. This section helps Claude Code understand context when routing meeting notes.

## Goals

- Primary objective
- Secondary objective
- Key milestone targets

## Links

| Resource | URL |
|----------|-----|
| Notion Workspace | [Link](https://notion.so/...) |
| GitHub Repository | [Link](https://github.com/...) |
| Shared Drive Folder | [Link](https://drive.google.com/...) |
| Documentation | [Link](...) |

## Team

### Core Team
- **Benjamin** (Lead) - Primary contact, overall direction
- **[Name]** (Role) - Responsibilities

### Extended Collaborators
- [Name] - Occasional contributor

## Meeting Cadence

- Weekly sync: Tuesdays 2pm
- Monthly review: First Thursday

## Keywords for Auto-Matching

These keywords help Claude Code identify when a meeting relates to this project:

- [Primary keyword 1]
- [Primary keyword 2]  
- [Technical term]
- [Domain concept]

## Shared Folder

The `shared/` subdirectory in this project folder is synced via Google Drive.

**Sharing setup:**
1. This folder is at: `projects/[project-name]/shared/`
2. Synced to Google Drive folder: [Drive folder name]
3. Shared with: [collaborator emails]

Collaborators can mount this Drive folder into their own Obsidian vault.

## Notes

Additional context that helps with meeting routing and understanding.
