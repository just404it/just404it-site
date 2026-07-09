# Public Website Boundary

The James Archive is a private research map for this website. It is not website content and must never be copied wholesale into this repository or a deployment.

## Allowed

- Website source code and generated static files.
- Information James has approved for public presentation.
- Material already published on James's public sites, including ordinary work credits.
- Curated links, press references, awards, and excerpts that pass a public-export review.
- Selected public-facing images and downloadable press materials.

## Never Publish From The Private Archive

- `james_archive.db`, database dumps, or private ledgers.
- `known_people`, audience, correspondence, contact, or relationship records.
- Private analytics, sales, revenue, dashboard, or account data.
- Source inventories, extraction paths, local filesystem paths, or backup locations.
- Unpublished drafts, private notes, email, chat exports, or internal rulings.
- Full reception, representation, timeline, voice-corpus, or research datasets.
- Safety backups or raw captures.

## Export Rule

Future archive-to-site tooling must use an explicit allowlist of public fields and produce a small reviewable export. Treat every field as private unless the allowlist says otherwise. Run a private-path and secret scan before every public push.
