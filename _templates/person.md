---
name: "{{name}}"
email: 
organization: 
role: 
first_seen: {{date}}
tags:
  - person
---

# {{name}}

## Contact

- **Email:** 
- **Organization:** 
- **Role:** 

## Notes

<!-- Add notes about this person -->

## Meetings

```dataview
LIST
FROM "projects" OR "meetings"
WHERE contains(participants, this.file.link)
SORT date DESC
```

