# Publish Knowledge Base

Build and deploy your knowledge base as a static website.

## Usage

```
/publish [options]
```

## Supported Frameworks

| Framework | Best For | Graph | Deploy Targets |
|-----------|----------|-------|----------------|
| **Quartz** | Obsidian users | ✅ | GitHub Pages |
| **Jekyll** | Simplicity | ✅ | Netlify, GitHub Pages |
| **Eleventy** | Speed | ❌ | Netlify, Vercel |
| **Gatsby** | Interactivity | ✅ | GitHub Pages, Vercel |

## Workflow

1. **Check prerequisites** (Node.js, site template)
2. **Scan vault** for publishable content
3. **Copy eligible files** to site content directory
4. **Process for publishing**:
   - Strip private sections (`<!-- private -->...<!-- /private -->`)
   - Convert wiki links for target platform
   - Normalize frontmatter
5. **Build static site**
6. **Deploy** (if `--deploy` flag)

## Privacy Filtering

By default, only files marked as public are published:

### Marking Files as Public

**Option 1: Frontmatter flag**
```yaml
---
title: My Public Note
public: true
---
```

**Option 2: Tag**
```yaml
---
title: My Public Note
tags: [public, topic]
---
```

### Private Sections

Use HTML comments to mark private content within public files:
```markdown
This is public content.

<!-- private -->
This section will be stripped before publishing.
<!-- /private -->

This is also public.
```

### Auto-Excluded

These patterns are always excluded:
- `_*/**` (inbox, templates, drafts)
- `.*/**` (config directories)
- `**/PROJECT.md` (project configs)
- `**/*private*`, `**/*personal*`

## Examples

### Preview locally
```
/publish --preview
```
→ Runs `python scripts/publish_site.py preview --framework quartz --port 8080`

### Build only (no deploy)
```
/publish --build
```
→ Runs `python scripts/publish_site.py build --framework quartz`

### Build and deploy to GitHub Pages
```
/publish --deploy
```
→ Runs `python scripts/publish_site.py build && python scripts/publish_site.py deploy`

### Use Jekyll for Netlify
```
/publish --framework jekyll --target netlify
```

### Include all files (ignore public flag)
```
/publish --all
```
→ Runs with `--all-files` flag

### Specify folders to include
```
/publish --include "concepts/**" "projects/*/index.md"
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--preview` | Build and serve locally | - |
| `--build` | Build only (no deploy) | - |
| `--deploy` | Build and deploy | - |
| `--framework` | quartz, jekyll, eleventy, gatsby | quartz |
| `--target` | github-pages, netlify, vercel | auto |
| `--port` | Preview server port | 8080 |
| `--include` | Glob patterns to include | See defaults |
| `--all` | Include all files (not just public) | false |

## Configuration

Configure publishing in `.hyperflow/config.yaml`:

```yaml
publishing:
  framework: quartz
  site_path: ~/projects/my-knowledge-site
  deploy_target: github-pages

  default_public_folders:
    - concepts/
    - projects/*/index.md

  exclude_patterns:
    - "**/meetings/**"
    - "**/personal/**"

  site_title: "My Knowledge Base"
  site_url: "https://username.github.io/knowledge"
```

## First-Time Setup

If you haven't set up a site yet:

### Quartz (Recommended)
```bash
npx quartz create
cd quartz
npx quartz build --serve
```

### Jekyll Garden
```bash
git clone https://github.com/maximevaillancourt/digital-garden-jekyll-template my-garden
cd my-garden
bundle install
bundle exec jekyll serve
```

### Eleventy
```bash
git clone https://github.com/juanfrank77/foam-eleventy-template my-site
cd my-site
npm install
npx @11ty/eleventy --serve
```

### Gatsby KB
```bash
git clone https://github.com/hikerpig/foam-template-gatsby-kb my-kb
cd my-kb
npm install
npm run develop
```

## Troubleshooting

**No files published?**
- Ensure files have `public: true` or `#public` tag
- Or use `--all` flag to include all files

**Build fails?**
- Check that site template is properly installed
- Run `npm install` or `bundle install` in site directory

**Deploy fails?**
- Ensure you're authenticated (gh auth, netlify login, vercel login)
- Check remote repository permissions
