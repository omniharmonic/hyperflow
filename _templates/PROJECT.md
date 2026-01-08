---
name: "{{project_name}}"
aliases: []
status: active
tags:
  - project
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

## Recent Meetings

```dataview
TABLE date, themes
FROM "projects/{{project_slug}}/meetings"
SORT date DESC
LIMIT 10
```

