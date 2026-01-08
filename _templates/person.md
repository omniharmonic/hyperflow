---
name: "{{name}}"
type: person
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

## Open Tasks

<!-- Tasks assigned to this person from meetings -->
<!-- Format: - [ ] Task description ([[source meeting]]) - Due: date -->

## Completed Tasks

<!-- Move completed tasks here -->

## Projects

<!-- Projects this person is involved in -->

## Notes

<!-- Add notes about this person -->

## Meetings

```dataview
TABLE date, title
FROM "projects" OR "meetings"
WHERE contains(participants, this.file.link)
SORT date DESC
LIMIT 10
```
