# Quick Clip

Instantly capture content to the knowledge base.

## Usage

```
/clip [title]
```

Without arguments, reads from the last user message or clipboard context.

## Behavior

1. **Detect content type** from input:
   - URL → Run web ingester
   - Structured text (code, lists) → Create formatted note
   - Plain text → Create quick clipping

2. **Generate metadata**:
   - Auto-generate title if not provided
   - Set status to `pending_review`
   - Add `clipping` tag
   - Record source and timestamp

3. **Save to** `_inbox/clippings/YYYY-MM-DD_title.md`

4. **Suggest enhancements**:
   - Entity extraction
   - Related notes
   - Appropriate tags

## Examples

### Clip a URL
User provides: `https://interesting-article.com/post`
```
/clip
```
→ Fetches and converts to markdown, saves to `_inbox/articles/`

### Clip with custom title
User provides some text, then:
```
/clip My Research Notes
```
→ Creates `_inbox/clippings/2026-01-09_my-research-notes.md`

### Clip code snippet
User provides code block, then:
```
/clip Python helper function
```
→ Creates note with proper code formatting

## Output Format

```markdown
---
title: "[Title]"
date: 2026-01-09T20:30:00
source: clipboard
status: pending_review
content_type: clipping
tags:
  - clipping
  - unprocessed
---

# [Title]

[Captured content]

---

*Clipped on 2026-01-09 at 20:30*
*Source: [source description]*
```

## Content Type Detection

| Content Pattern | Type | Handling |
|-----------------|------|----------|
| Starts with `http://` or `https://` | URL | Run `/ingest [url]` |
| Contains ``` or indented code | Code snippet | Preserve formatting |
| Has markdown headers | Structured note | Preserve structure |
| Plain paragraphs | Text note | Wrap in note template |
| JSON or YAML | Data | Format appropriately |

## Workflow Integration

After clipping, the command will:
1. Confirm save location
2. Show first few lines of captured content
3. Suggest running entity extraction
4. Offer to add to a specific project
5. Ask if you want to tag or categorize further

## Related Commands

- `/ingest` - Full ingestion with routing
- `/ingest-meetings` - Process meeting transcripts
- `/extract-actions` - Extract tasks from content
