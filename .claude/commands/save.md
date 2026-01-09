# Save Command

Save and version control the knowledge vault with a detailed commit.

## Arguments
- `$ARGUMENTS` - Optional commit message or description of changes

## Instructions

When the user runs `/save`, create a git commit that captures all changes to the knowledge vault with a detailed, informative commit message.

### Steps:

1. **Check git status** to see what files have changed:
   ```bash
   git status --porcelain
   ```

2. **Analyze changes** by category:
   - New meetings added (in `_inbox/meetings/` or `meetings/` or project `meetings/` folders)
   - New people profiles created (in `people/`)
   - New or updated project files (in `projects/`)
   - New concepts added (in `concepts/`)
   - New articles/papers ingested (in `_inbox/papers/`, `_inbox/articles/`)
   - Configuration changes
   - Template updates

3. **Generate a detailed commit message** following this format:
   ```
   [Category]: Brief summary

   Changes:
   - Added/Updated: specific files
   - New entities: people, concepts, etc.

   Stats:
   - X new meetings
   - Y people profiles updated
   - Z new concepts
   ```

4. **Stage all changes**:
   ```bash
   git add -A
   ```

5. **Create the commit** using a heredoc for proper formatting:
   ```bash
   git commit -m "$(cat <<'EOF'
   Your detailed commit message here
   EOF
   )"
   ```

6. **Report summary** to the user showing what was committed.

### Commit Message Categories:

Use these prefixes based on the primary change type:
- `[Knowledge]` - New content added (meetings, notes, articles)
- `[People]` - Person profile changes
- `[Projects]` - Project-related updates
- `[Config]` - Configuration or template changes
- `[Ingest]` - New content ingested from external sources
- `[Tasks]` - Task-related updates
- `[Mixed]` - Multiple significant change types

### Example Output:

If the user made changes including 2 new meetings and 1 new person profile:

```
[Knowledge]: Add OpenCivics meetings and new contact

Changes:
- meetings/2024-01-07-opencivics-planning.md (new)
- meetings/2024-01-08-trustgraph-review.md (new)
- people/Jane Smith.md (new)

Stats:
- 2 new meeting notes
- 1 new person profile

Committed 3 files
```

### User Message Handling:

If the user provides `$ARGUMENTS`, incorporate that context into the commit message. For example:

- `/save after weekly planning sessions` → Use "after weekly planning sessions" as additional context
- `/save WIP on project docs` → Create a WIP commit with that description

### No Changes:

If there are no changes to commit, inform the user:
"No changes to commit. Your knowledge vault is up to date."
