# JUST404IT Static Site

This is the new static site for `just404it.com`, generated from the public safety backup of `justdeleteit.com`.

## What Is Here

- `index.html` - the hub plus searchable, sortable, faceted archive.
- `assets/site.css` and `assets/site.js` - the editable front-end.
- `data/portfolio.json` and `data/portfolio.js` - 91 public project pages representing 100 games.
- `games/` - locally generated detail pages for every public project entry.
- `assets/portfolio/` - 22 copied portfolio images from the backup.
- `archive/index.html` - crawlable text index of all public project pages.
- `sitemap.xml` and `robots.txt` - generated discovery files for search engines.
- `DESIGN_SYSTEM.md` - the color, label, filtering, and sorting rules.

## What Is Not Here

The complete public-site backup is intentionally kept outside this public repository as a checksummed private archive.

The private James Archive is a research map, not publication content. See `PUBLICATION_BOUNDARY.md` before adding archive-derived material.

## Hosting State

GitHub is the source repo and GitHub Pages is the current free construction preview.

The generator defaults canonical URLs and the sitemap to the preview URL. At domain cutover, set `JUST404IT_SITE_URL` to the approved production origin before rebuilding.

No DNS, registrar, hosting, or WordPress changes have been made by this generator.

## Regenerate From Backup

```powershell
$env:JUSTDELETEIT_BACKUP_ROOT = 'C:\path\to\the\extracted-backup'
$env:JUST404IT_SITE_URL = 'https://just404it.github.io/just404it-site'
py -3.12 tools\build_static_site.py
```

## Validate Before Publishing

```powershell
py -3.12 tools\validate_site.py
```
