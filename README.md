# JUST404IT Static Site

This is the new static starter site for `just404it.com`, generated from the public safety backup of `justdeleteit.com`.

## What Is Here

- `index.html` - the new hub plus searchable archive.
- `assets/site.css` and `assets/site.js` - the editable front-end.
- `data/portfolio.json` and `data/portfolio.js` - 91 recovered portfolio entries.
- `assets/portfolio/` - 22 copied portfolio images from the backup.
- `archive/index.html` - compatibility entry point for archive links.

## What Is Not Here

The complete public-site backup is intentionally kept outside this public repository as a checksummed private archive.

## Recommended Free Hosting Path

Use Cloudflare Pages as the production host and GitHub as the source repo.

1. Create a GitHub repo for this folder.
2. Connect that repo to Cloudflare Pages.
3. Set `just404it.com` as the primary custom domain.
4. Add `www.just404it.com`, `justdeleteit.com`, and `www.justdeleteit.com` only after the preview is approved.
5. Decide whether `justdeleteit.com` redirects to `just404it.com/#archive` or remains a preserved archive domain.

No DNS, registrar, hosting, or WordPress changes have been made by this generator.

## Regenerate From Backup

```powershell
$env:JUSTDELETEIT_BACKUP_ROOT = 'C:\path\to\the\extracted-backup'
py -3.12 tools\build_static_site.py
```
