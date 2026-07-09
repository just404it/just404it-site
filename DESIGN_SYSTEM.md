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

## Label Taxonomy

The old site placed unrelated labels in one category list. The rebuild separates them:

- **Status:** all, playable, or recognized.
- **Format:** digital, analog, or intermedia.
- **Context:** jam, personal, serious, silly, interactive fiction, or music videogame.
- **Platform:** web, PC, or Mac.
- **Year:** 2012 through 2017.

Status is exclusive. Choosing another status replaces the current status.

Format, context, and platform are multi-select groups. Multiple labels inside one group broaden the result with OR logic. Different groups narrow the result with AND logic. Search and year also combine with the active filters using AND logic.

Example: `Playable` + (`Analog` OR `Intermedia`) + `Exhibited` is not currently possible because `Exhibited` is represented by the broader recognized status. A future public-data pass may split awards and exhibitions if the source data is normalized enough to support that distinction consistently.

## Sorting

- **Series: 100 to 1** is the default and follows the authored project sequence backward from completion.
- **Series: 1 to 100** follows the project from its beginning.
- **Year: newest first** and **Year: oldest first** use the recovered publication year, then series order.
- **Title: A to Z** is alphabetical and ignores series position.

Filtering never silently changes the selected sort. Search and filter state are stored in the URL so a result can be shared.

## Project Pages

Each project page contains only information already present on the public portfolio:

- series position, year, development time, and availability;
- public description and article text;
- public play/download links;
- public credits and recognition;
- recovered image or public video still when available;
- adjacent navigation through the 100-game sequence;
- a clearly secondary link to the legacy WordPress page.

The private James Archive remains a research map. Any future press, reception, or timeline additions must pass the allowlist in `PUBLICATION_BOUNDARY.md` before publication.
