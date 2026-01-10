---
title: Task Dashboard
type: index
tags:
  - tasks
  - dashboard
---

# Task Dashboard

Central hub for all tasks across the knowledge vault.

## All Open Tasks

```dataview
TASK
FROM ""
WHERE !completed
SORT file.mtime DESC
LIMIT 50
```

## Tasks by Project

### Filter by Project

> Replace `PROJECT_NAME` with your project folder name (e.g., `opencivics`, `trustgraph`)

```dataview
TASK
FROM "projects/PROJECT_NAME"
WHERE !completed
SORT file.mtime DESC
```

### Project Task Counts

```dataview
TABLE WITHOUT ID
  file.folder as "Project",
  length(filter(file.tasks, (t) => !t.completed)) as "Open Tasks",
  length(filter(file.tasks, (t) => t.completed)) as "Completed"
FROM "projects"
WHERE file.tasks
GROUP BY file.folder
SORT rows.length DESC
```

## Tasks by Person

### Filter Tasks Assigned to Person

> Replace `Person Name` with the person's name

```dataview
TASK
FROM ""
WHERE contains(text, "Person Name") OR contains(text, "@person")
WHERE !completed
SORT file.mtime DESC
```

### People with Open Tasks

```dataview
TABLE WITHOUT ID
  file.link as "Person",
  length(filter(file.tasks, (t) => !t.completed)) as "Open Tasks"
FROM "people"
WHERE file.tasks
SORT length(filter(file.tasks, (t) => !t.completed)) DESC
```

## Tasks from Recent Meetings

```dataview
TASK
FROM "meetings" OR "projects"
WHERE !completed
WHERE file.cday >= date(today) - dur(14 days)
SORT file.mtime DESC
```

## Overdue Tasks

```dataview
TASK
FROM ""
WHERE !completed
WHERE contains(text, "due:") OR contains(text, "by ")
SORT file.mtime DESC
```

## Tasks by Tag

### Action Items

```dataview
TASK
FROM #action-item
WHERE !completed
SORT file.mtime DESC
```

### Follow-ups

```dataview
TASK
FROM ""
WHERE contains(text, "follow up") OR contains(text, "follow-up")
WHERE !completed
SORT file.mtime DESC
```

## Recently Completed

```dataview
TASK
FROM ""
WHERE completed
WHERE file.mtime >= date(today) - dur(7 days)
SORT file.mtime DESC
LIMIT 20
```

---

## Quick Filters

Create custom views by copying and modifying these queries:

### Tasks Mentioning a Topic

```dataview
TASK
FROM ""
WHERE contains(text, "YOUR_TOPIC")
WHERE !completed
```

### Tasks from a Specific Date Range

```dataview
TASK
FROM ""
WHERE file.cday >= date("2024-01-01") AND file.cday <= date("2024-01-31")
WHERE !completed
```

### Tasks in Inbox (Unprocessed)

```dataview
TASK
FROM "_inbox"
WHERE !completed
SORT file.mtime DESC
```

---

## Task Statistics

```dataview
TABLE WITHOUT ID
  "Total Open" as Metric,
  length(filter(rows, (r) => !r.completed)) as Count
FROM ""
FLATTEN file.tasks as task
WHERE task
GROUP BY true
```

## Notes

- Tasks are automatically extracted from meeting notes using the `/extract-actions` command
- Use `- [ ]` syntax to create tasks in any note
- Tag tasks with `#action-item` for important follow-ups
- Mention people with `@name` or `[[people/Name]]` for assignment tracking
