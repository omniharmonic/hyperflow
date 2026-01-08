---
name: "{Organization Name}"
type: organization
website: 
sector: 
first_seen: {{date}}
tags:
  - organization
---

# {Organization Name}

First encountered in: [[{meeting path}]]

## About

<!-- Description based on meeting context -->

## Key People

<!-- People associated with this organization -->

## Projects

<!-- Projects involving this organization -->

## Mentions

```dataview
LIST
FROM "meetings" OR "projects"
WHERE contains(file.outlinks, this.file.link)
SORT date DESC
```

