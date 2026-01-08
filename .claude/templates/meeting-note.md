---
title: "{{title}}"
date: {{date}}
duration: {{duration}}
status: processed
project: "[[projects/{{project}}/index]]"
participants:
{{#each participants}}
  - "[[people/{{this}}]]"
{{/each}}
themes:
{{#each themes}}
  - {{this}}
{{/each}}
tags:
  - meeting
  - {{project-slug}}
{{#each themes}}
  - {{this}}
{{/each}}
meetily_id: {{meetily_id}}
processed_at: {{processed_at}}
---

# {{title}}

**Date:** {{date}}  
**Duration:** {{duration}} minutes  
**Project:** [[projects/{{project}}/index]]

## Participants

{{#each participants}}
- [[people/{{this}}]]
{{/each}}

## Summary

{{summary}}

## Key Discussion Points

{{#each key_points}}
### {{this.title}}

{{this.content}}

{{/each}}

## Decisions Made

{{#if decisions}}
{{#each decisions}}
- {{this}}
{{/each}}
{{else}}
_No formal decisions recorded._
{{/if}}

## Action Items

{{#if action_items}}
| Owner | Task | Deadline | Status |
|-------|------|----------|--------|
{{#each action_items}}
| [[people/{{this.owner}}]] | {{this.task}} | {{this.deadline}} | {{this.status}} |
{{/each}}
{{else}}
_No action items identified._
{{/if}}

## Full Transcript

<details>
<summary>Click to expand transcript</summary>

{{transcript}}

</details>

---

## Notes

_Additional notes or follow-up items can be added here._

---

*Processed by Claude Code on {{processed_at}}*
