# JUST404IT Design System

This file explains the visible rules behind the site. The interface should never change color or label behavior arbitrarily.

## Information Shape

- `JUST404IT` is the public identity and front door.
- `Selected work` is a deliberately small starting set, not a ranking.
- `100 Games in 5 Years` is the complete legacy series.
- The archive contains 91 project pages representing all 100 games. One page contains games 33-41 and another contains games 56-57.
- Each project links to a local detail page. The old WordPress page is a legacy source link, not the main destination.

## Color Jobs

Color communicates a stable kind of information. Text labels remain present, so color is never the only signal.

| Color | Token | Job |
|---|---|---|
| Coral `#ff5d3d` | `--coral` | Primary commands and the unqualified `All` state |
| Mint `#72e2b7` | `--mint` | Playable status, outbound play links, and focus |
| Blue `#78c9ff` | `--blue` | Digital format |
| Pink `#ec91c8` | `--pink` | Analog format and the legacy wordmark accent |
| Violet `#b7a7ff` | `--violet` | Intermedia format |
| Gold `#f3c662` | `--gold` | Recognition and small archival metadata |
| Neutral gray | `--muted`, `--quiet` | Context, platform, year, and supporting copy |

Project cards use a colored top rule for their primary format. Hover and focus may strengthen contrast, but they do not reassign category colors.

Semantic filters keep their assigned color when selected: playable fills mint, recognized fills gold, and format filters fill blue, pink, or violet. Neutral context and platform filters use coral only while selected.

## Brand Mark

The navigation wordmark and square browser-face icon preserve the exact geometry of the 2019 `Just 404-03` vector. The update removes the old purple gradient and assigns the existing site colors deliberately:

- `JUST` and `IT` use the warm white text color.
- The first `4` uses command coral.
- The browser-face `0` uses digital blue.
- The second `4` uses analog pink.
- The tongue repeats coral as the only small character accent.

The large homepage title remains live text for clarity and responsiveness. The full vector wordmark is reserved for navigation, footers, favicons, and social previews, where the browser-face icon adds recognition without competing with the work.

## Label Taxonomy

The old site placed unrelated labels in one category list. The rebuild separates them:

- **Status:** all, playable, or recognized.
- **Format:** digital, analog, or intermedia.
- **Context:** jam, personal, serious, silly, interactive fiction, or music videogame.
- **Platform:** web, PC, or Mac.
- **Recognition:** award-winning or exhibited.
- **Do something:** play online, download, watch, or get rules/print material.
- **Build time:** one day or less, days, weeks, or months and longer.
- **Year:** 2012 through 2017.

Status is exclusive. Choosing another status replaces the current status.

All groups except status are multi-select. Multiple labels inside one group broaden the result with OR logic. Different groups narrow the result with AND logic. Search and year also combine with the active filters using AND logic.

Example: `Playable` + (`Analog` OR `Intermedia`) + `Exhibited` finds playable off-screen or hybrid work that was publicly exhibited.

Facet counts respond to the filters in other groups. A zero-result option is disabled unless it is already selected. Active filters appear as individually removable chips, and the full state remains in the URL.

## Quick Routes And Chance

Quick routes are named combinations of ordinary filters, not a second hidden classification system:

- **Play something now:** playable and available online.
- **Give me nonsense:** silly context.
- **Get serious:** serious context.
- **Go off-screen:** analog or intermedia format.
- **Made in a day:** development time of one day or less.
- **The decorated ones:** award-winning recognition.

`Surprise me` chooses one project from the current visible result set. It respects every active filter, search term, and year. It does not add a random URL parameter or create an indexable duplicate page.

## Sorting

- **Series: 100 to 1** is the default and follows the authored project sequence backward from completion.
- **Series: 1 to 100** follows the project from its beginning.
- **Year: newest first** and **Year: oldest first** use the recovered publication year, then series order.
- **Title: A to Z** is alphabetical and ignores series position.
- **Build time: fastest first** and **Build time: longest first** use normalized public development-time labels; projects without a parseable time remain at the end.

Filtering never silently changes the selected sort. Search and filter state are stored in the URL so a result can be shared.

## Search Discovery

- Every project remains a static HTML page with a unique title, description, canonical URL, and JSON-LD creative-work record.
- `archive/index.html` is a crawlable text index with direct HTML links to all project pages; the richer visual archive remains the human-first interface.
- `sitemap.xml` lists the homepage, text index, and every project page. `robots.txt` points to it.
- Filter combinations canonicalize to the main homepage and are not linked as separate crawl targets, preventing the faceted interface from multiplying duplicate indexable URLs.
- The canonical origin comes from `JUST404IT_SITE_URL`; it must be changed from the construction preview to `https://just404it.com` only when that domain is ready for cutover.

## Project Pages

Each project page contains only information already present on the public portfolio:

- series position, year, development time, and availability;
- public description and article text;
- public play/download links;
- public credits and recognition;
- recovered image or public video still when available;
- adjacent navigation through the 100-game sequence;
- an archive-provenance note without linking visitors back to the old WordPress surface.

The private James Archive remains a research map. Any future press, reception, or timeline additions must pass the allowlist in `PUBLICATION_BOUNDARY.md` before publication.
