---
name: "{{project_name}}"
aliases: []
status: active
tags:
  - project
# Notion Integration (optional)
notion_workspace: ""
notion_tasks_database: ""
notion_page_id: ""
---

# {{project_name}}

## Overview

<!-- Brief project description -->

## Team

| Name | Email | Role |
|------|-------|------|
| | | Lead |
| | | |

## Keywords

Keywords for auto-matching meetings to this project:

- 
- 
- 

## Links

- **Repository:** 
- **Docs:** 
- **Shared Drive:** 
- **Notion:** <!-- Add Notion workspace link if using -->

## Integrations

### Notion Tasks (Optional)

To enable Notion task sync, add to frontmatter:
```yaml
notion_workspace: "Your Workspace Name"
notion_tasks_database: "database-id-from-url"
```

Find your database ID in the Notion URL after opening the database.

## Recent Meetings

```dataview
TABLE date, themes
FROM "projects/{{project_slug}}/meetings"
SORT date DESC
LIMIT 10
```
