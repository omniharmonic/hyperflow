---
name: "{Concept Name}"
type: concept
aliases: []
category: 
first_seen: {{date}}
tags:
  - concept
---

# {Concept Name}

First encountered in: [[{meeting path}]]

## Definition

<!-- Definition based on meeting context -->

## Related Concepts

<!-- Wiki-links to related concepts -->

## Resources

<!-- Links to external resources -->

## Mentions

```dataview
LIST
FROM "meetings" OR "projects"
WHERE contains(file.outlinks, this.file.link)
SORT date DESC
```

