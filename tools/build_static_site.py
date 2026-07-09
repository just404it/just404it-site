from __future__ import annotations

import json
import os
import re
import shutil
from html import escape
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup


SITE_ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = Path(
    os.environ.get("JUSTDELETEIT_BACKUP_ROOT", SITE_ROOT / ".source-backup")
).expanduser()
MIRROR_ROOT = BACKUP_ROOT / "mirror" / "www.justdeleteit.com"
PORTFOLIO_ROOT = MIRROR_ROOT / "portfolio"
PORTFOLIO_ASSETS = SITE_ROOT / "assets" / "portfolio"


AWARD_WORDS = re.compile(
    r"\b(award|winner|wins|won|official select|selected|festival|showcase|featured|honorable mention|finalist|nominee|displayed)\b",
    re.I,
)
PLAY_WORDS = re.compile(r"\b(play|download|itch|game jolt|newgrounds|source code|rules)\b", re.I)


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def text_of(node) -> str:
    if not node:
        return ""
    return compact(node.get_text(" ", strip=True))


def absolute_backup_path_for_url(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc.lower() not in {"www.justdeleteit.com", "justdeleteit.com"}:
        return None
    path = unquote(parsed.path if parsed.netloc else url)
    if not path.startswith("/"):
        path = "/" + path
    candidate = MIRROR_ROOT / path.lstrip("/")
    if candidate.is_file():
        return candidate
    if candidate.parent.is_dir():
        stem = candidate.stem
        suffix = candidate.suffix
        matches = list(candidate.parent.glob(f"{stem}-*{suffix}"))
        if matches:
            return max(matches, key=lambda item: item.stat().st_size)
    return None


def copy_portfolio_image(slug: str, image_url: str) -> str:
    source = absolute_backup_path_for_url(image_url)
    if not source:
        return ""
    suffix = source.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        suffix = ".jpg"
    destination = PORTFOLIO_ASSETS / f"{slug}{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return f"assets/portfolio/{destination.name}"


def extract_description(soup: BeautifulSoup) -> str:
    content = soup.select_one(".entry-content") or soup.select_one("article")
    if not content:
        return ""
    clone = BeautifulSoup(str(content), "html.parser")
    for selector in [
        ".preview_meta",
        ".post_social_share",
        ".blogpost_share",
        ".prev_next_links",
        ".block_cats",
        "script",
        "style",
        "nav",
    ]:
        for node in clone.select(selector):
            node.decompose()
    paragraphs: list[str] = []
    for node in clone.find_all(["p", "li"]):
        value = text_of(node)
        if len(value) < 24:
            continue
        if value.lower().startswith(("share this", "previous", "next")):
            continue
        paragraphs.append(value)
    if not paragraphs:
        value = text_of(clone)
        return value[:360]
    return " ".join(paragraphs[:2])[:420]


def extract_portfolio_entry(path: Path) -> dict:
    slug = path.parent.name
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    title = text_of(soup.select_one("h1.entry-title") or soup.find("h1")) or slug.replace("-", " ").title()
    canonical = soup.select_one('link[rel="canonical"]')
    source_url = canonical.get("href") if canonical and canonical.get("href") else f"https://www.justdeleteit.com/portfolio/{slug}/"
    categories = [text_of(node) for node in soup.select(".block_cats a") if text_of(node)]
    year = next((cat for cat in categories if re.fullmatch(r"20\d{2}", cat)), "")

    image_url = ""
    image = soup.select_one("img.pf_img")
    if image and image.get("src"):
        image_url = image["src"]
    local_image = copy_portfolio_image(slug, image_url) if image_url else ""

    details: list[str] = []
    links: list[dict] = []
    for node in soup.select(".preview_skills"):
        label = text_of(node)
        if not label:
            continue
        details.append(label)
        link = node.find("a")
        if link and link.get("href"):
            links.append({"label": text_of(link), "url": link["href"]})

    game_number = ""
    development_time = ""
    for detail in details:
        game_match = re.search(r"Game\s+(\d+)\s+of\s+100", detail, re.I)
        if game_match:
            game_number = game_match.group(1)
        dev_match = re.search(r"Development time:\s*(.+)", detail, re.I)
        if dev_match:
            development_time = compact(dev_match.group(1))

    accolade_details = [detail for detail in details if AWARD_WORDS.search(detail)]
    playable = bool(any(PLAY_WORDS.search(link["label"]) for link in links))

    return {
        "slug": slug,
        "title": title,
        "year": year,
        "categories": categories,
        "description": extract_description(soup),
        "image": local_image,
        "sourceUrl": source_url,
        "gameNumber": game_number,
        "developmentTime": development_time,
        "details": details[:8],
        "links": links[:5],
        "hasAccolade": bool(accolade_details),
        "playable": playable,
    }


def sort_key(entry: dict) -> tuple:
    year = int(entry["year"]) if entry.get("year", "").isdigit() else 0
    game = int(entry["gameNumber"]) if entry.get("gameNumber", "").isdigit() else 0
    return (-year, -game, entry["title"].lower())


def build_portfolio_data() -> list[dict]:
    paths = sorted(PORTFOLIO_ROOT.glob("*/index.html"))
    entries = [extract_portfolio_entry(path) for path in paths]
    return sorted(entries, key=sort_key)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def write_portfolio_data(entries: list[dict]) -> None:
    data = json.dumps(entries, ensure_ascii=False, indent=2)
    write_text(SITE_ROOT / "data" / "portfolio.json", data + "\n")
    write_text(SITE_ROOT / "data" / "portfolio.js", "window.JUST404IT_PORTFOLIO = " + data + ";\n")


def build_index_html(entries: list[dict]) -> str:
    featured = [entry for entry in entries if entry["hasAccolade"] or entry["playable"]][:6]
    cards = "\n".join(
        f"""
        <a class="feature-card" href="{escape(entry['sourceUrl'])}">
          <span class="feature-kicker">{escape(entry['year'] or 'Archive')}</span>
          <strong>{escape(entry['title'])}</strong>
          <span>{escape(entry['description'] or ', '.join(entry['categories'][:3]) or '100 Games in 5 Years archive entry')}</span>
        </a>"""
        for entry in featured
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JUST404IT - James Earl Cox III</title>
  <meta name="description" content="The central hub and playable archive for James Earl Cox III: games, film, writing, music, and experiments.">
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <header class="site-head">
    <nav class="nav" aria-label="Primary">
      <a class="mark" href="./"><span>JUST</span>404<span>IT</span></a>
      <div class="nav-links">
        <a href="#flavors">Flavors</a>
        <a href="#archive">Archive</a>
        <a href="https://www.justdeleteit.com/">Old Site</a>
      </div>
    </nav>
    <section class="hero" aria-labelledby="hero-title">
      <p class="eyebrow">James Earl Cox III</p>
      <h1 id="hero-title">JUST404IT</h1>
      <p class="lede">One strange little hub for the games, films, words, sounds, and survival documents. JUSTDELETEIT stays preserved as the sealed 100 Games in 5 Years archive while the new site gets cleaner, faster, and easier for AI to keep improving.</p>
      <div class="hero-actions">
        <a class="button primary" href="#archive">Browse Archive</a>
        <a class="button" href="#transfer">Migration Plan</a>
      </div>
    </section>
  </header>

  <main>
    <section class="band" id="flavors" aria-labelledby="flavors-title">
      <div class="section-heading">
        <p class="eyebrow">The Map</p>
        <h2 id="flavors-title">A cleaner home for the James Cinematic Sidequest Universe.</h2>
      </div>
      <div class="flavor-grid">
        <a class="flavor" href="https://www.seempoint.com/">
          <span>Studio</span>
          <strong>Seemingly Pointless</strong>
          <p>Collaborative games and studio work.</p>
        </a>
        <a class="flavor" href="#archive">
          <span>Archive</span>
          <strong>100 Games in 5 Years</strong>
          <p>The JUSTDELETEIT legacy collection, preserved from WordPress.</p>
        </a>
        <a class="flavor" href="https://www.llamageddonfilm.com/">
          <span>Film</span>
          <strong>Llamageddon</strong>
          <p>The killer space llama orbit remains intact.</p>
        </a>
        <a class="flavor" href="#archive">
          <span>Solo</span>
          <strong>Fool's Ghost</strong>
          <p>Future solo games, experiments, and haunted snacks.</p>
        </a>
      </div>
    </section>

    <section class="band featured" aria-labelledby="featured-title">
      <div class="section-heading">
        <p class="eyebrow">Recovered Highlights</p>
        <h2 id="featured-title">Pulled from the live WordPress backup.</h2>
      </div>
      <div class="feature-grid">
        {cards}
      </div>
    </section>

    <section class="band archive-band" id="archive" aria-labelledby="archive-title">
      <div class="section-heading archive-heading">
        <div>
          <p class="eyebrow">Playable Archive</p>
          <h2 id="archive-title">100 Games in 5 Years</h2>
        </div>
        <p class="count"><span id="visible-count">0</span> of {len(entries)} entries</p>
      </div>
      <div class="toolbar" role="search">
        <label class="search-label" for="search">Search</label>
        <input id="search" type="search" placeholder="title, year, category, accolade">
        <div class="filters" aria-label="Archive filters">
          <button class="filter is-active" type="button" data-filter="all">All</button>
          <button class="filter" type="button" data-filter="playable">Playable</button>
          <button class="filter" type="button" data-filter="accolade">Accolades</button>
          <button class="filter" type="button" data-filter="analog">Analog</button>
          <button class="filter" type="button" data-filter="digital">Digital</button>
        </div>
      </div>
      <div class="portfolio-grid" id="portfolio-grid" aria-live="polite"></div>
    </section>

    <section class="band transfer" id="transfer" aria-labelledby="transfer-title">
      <div class="section-heading">
        <p class="eyebrow">Transfer Shape</p>
        <h2 id="transfer-title">Cloudflare Pages first, WordPress nowhere near the steering wheel.</h2>
      </div>
      <div class="transfer-grid">
        <div>
          <strong>1. Keep the backup sealed.</strong>
          <p>The full public mirror and checksummed ZIP are stored separately. This repo only carries the new site and selected portfolio media.</p>
        </div>
        <div>
          <strong>2. Put this repo on GitHub.</strong>
          <p>AI tools can edit files directly, propose redesigns, and keep the source history readable.</p>
        </div>
        <div>
          <strong>3. Deploy on Cloudflare Pages.</strong>
          <p>Attach just404it.com as the main domain, then decide whether justdeleteit.com redirects or remains an archive domain.</p>
        </div>
      </div>
    </section>
  </main>

  <footer class="footer">
    <a class="mark" href="./"><span>JUST</span>404<span>IT</span></a>
    <p>Built from the 2026-07-09 safety backup of justdeleteit.com. No DNS changes have been made.</p>
  </footer>
  <script src="data/portfolio.js"></script>
  <script src="assets/site.js"></script>
</body>
</html>
"""


def build_archive_html(total: int) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JUST404IT Archive</title>
  <meta http-equiv="refresh" content="0; url=../#archive">
  <link rel="canonical" href="../#archive">
</head>
<body>
  <p>{total} archive entries moved to <a href="../#archive">the JUST404IT archive</a>.</p>
</body>
</html>
"""


def build_css() -> str:
    return """:root {
  color-scheme: dark;
  --ink: #f6f1e7;
  --muted: #b8afa1;
  --quiet: #7d756d;
  --paper: #11100e;
  --panel: #191713;
  --panel-2: #221f1a;
  --line: #383127;
  --hot: #ff5a36;
  --mint: #7cf4c8;
  --gold: #f2bd59;
  --pink: #f06aa2;
  --shadow: rgba(0, 0, 0, 0.34);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  background:
    linear-gradient(90deg, rgba(255, 90, 54, 0.07) 1px, transparent 1px),
    linear-gradient(180deg, rgba(124, 244, 200, 0.05) 1px, transparent 1px),
    var(--paper);
  background-size: 72px 72px;
  color: var(--ink);
  line-height: 1.5;
}

a {
  color: inherit;
  text-decoration: none;
}

.site-head {
  min-height: 68svh;
  border-bottom: 1px solid var(--line);
}

.nav {
  align-items: center;
  display: flex;
  gap: 24px;
  justify-content: space-between;
  margin: 0 auto;
  max-width: 1180px;
  padding: 24px;
}

.mark {
  font-family: "Courier New", ui-monospace, monospace;
  font-size: clamp(1.35rem, 2.5vw, 2rem);
  font-weight: 800;
  letter-spacing: 0;
  white-space: nowrap;
}

.mark span {
  color: var(--hot);
}

.nav-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.nav-links a,
.button,
.filter {
  border: 1px solid var(--line);
  min-height: 40px;
  padding: 9px 14px;
}

.nav-links a:hover,
.button:hover,
.filter:hover {
  border-color: var(--mint);
  color: var(--mint);
}

.hero {
  margin: 0 auto;
  max-width: 1180px;
  padding: clamp(56px, 8vw, 104px) 24px 56px;
}

.eyebrow {
  color: var(--gold);
  font-family: "Courier New", ui-monospace, monospace;
  font-size: 0.83rem;
  font-weight: 700;
  letter-spacing: 0;
  margin: 0 0 12px;
  text-transform: uppercase;
}

h1,
h2 {
  letter-spacing: 0;
  line-height: 0.98;
  margin: 0;
}

h1 {
  font-size: clamp(4.5rem, 13vw, 11rem);
  max-width: 8ch;
}

h2 {
  font-size: clamp(2rem, 4.6vw, 4.8rem);
  max-width: 14ch;
}

.lede {
  color: var(--muted);
  font-size: clamp(1.05rem, 2vw, 1.35rem);
  max-width: 720px;
}

.hero-actions,
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.button,
.filter {
  background: transparent;
  color: var(--ink);
  cursor: pointer;
  display: inline-flex;
  font: inherit;
  font-weight: 700;
  justify-content: center;
}

.button.primary,
.filter.is-active {
  background: var(--hot);
  border-color: var(--hot);
  color: #160b07;
}

.band {
  border-bottom: 1px solid var(--line);
  margin: 0 auto;
  max-width: 1180px;
  padding: clamp(52px, 8vw, 92px) 24px;
}

.section-heading {
  align-items: end;
  display: flex;
  gap: 24px;
  justify-content: space-between;
  margin-bottom: 28px;
}

.flavor-grid,
.feature-grid,
.transfer-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
}

.flavor,
.feature-card,
.transfer-grid > div,
.portfolio-card {
  background: color-mix(in srgb, var(--panel) 94%, black);
  border: 1px solid var(--line);
  box-shadow: 0 18px 40px var(--shadow);
}

.flavor,
.feature-card,
.transfer-grid > div {
  min-height: 178px;
  padding: 22px;
}

.flavor:hover,
.feature-card:hover,
.portfolio-card:hover {
  border-color: var(--mint);
}

.flavor span,
.feature-kicker,
.meta {
  color: var(--gold);
  display: block;
  font-family: "Courier New", ui-monospace, monospace;
  font-size: 0.78rem;
  margin-bottom: 10px;
  text-transform: uppercase;
}

.flavor strong,
.feature-card strong,
.transfer-grid strong,
.portfolio-card h3 {
  display: block;
  font-size: 1.25rem;
  line-height: 1.08;
}

.flavor p,
.feature-card span:last-child,
.transfer-grid p,
.portfolio-card p {
  color: var(--muted);
}

.toolbar {
  align-items: center;
  display: grid;
  gap: 12px;
  grid-template-columns: auto minmax(220px, 1fr) auto;
  margin-bottom: 20px;
}

.search-label {
  color: var(--quiet);
  font-family: "Courier New", ui-monospace, monospace;
  font-weight: 700;
  text-transform: uppercase;
}

input[type="search"] {
  background: var(--panel);
  border: 1px solid var(--line);
  color: var(--ink);
  font: inherit;
  min-height: 44px;
  padding: 10px 12px;
  width: 100%;
}

input[type="search"]:focus {
  border-color: var(--mint);
  outline: none;
}

.count {
  color: var(--quiet);
  font-family: "Courier New", ui-monospace, monospace;
}

.portfolio-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
}

.portfolio-card {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  overflow: hidden;
}

.thumb {
  aspect-ratio: 16 / 10;
  background: var(--panel-2);
  border-bottom: 1px solid var(--line);
  display: grid;
  overflow: hidden;
  place-items: center;
}

.thumb img {
  height: 100%;
  object-fit: cover;
  width: 100%;
}

.fallback-thumb {
  color: var(--pink);
  font-family: "Courier New", ui-monospace, monospace;
  font-size: 2rem;
  font-weight: 800;
}

.portfolio-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  border: 1px solid var(--line);
  color: var(--muted);
  font-family: "Courier New", ui-monospace, monospace;
  font-size: 0.75rem;
  padding: 4px 7px;
}

.card-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: auto;
}

.card-links a {
  border-bottom: 1px solid var(--hot);
  color: var(--hot);
  font-weight: 700;
}

.empty {
  border: 1px dashed var(--line);
  color: var(--muted);
  grid-column: 1 / -1;
  padding: 28px;
}

.footer {
  align-items: center;
  color: var(--quiet);
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: space-between;
  margin: 0 auto;
  max-width: 1180px;
  padding: 34px 24px;
}

@media (max-width: 760px) {
  .nav,
  .section-heading,
  .footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar {
    grid-template-columns: 1fr;
  }

  .nav-links {
    justify-content: flex-start;
  }

  .site-head {
    min-height: 68svh;
  }

  .site-head h1 {
    font-size: clamp(3.4rem, 16vw, 4rem);
    max-width: 100%;
  }
}
"""


def build_js() -> str:
    return r"""const entries = Array.isArray(window.JUST404IT_PORTFOLIO) ? window.JUST404IT_PORTFOLIO : [];
const grid = document.querySelector("#portfolio-grid");
const search = document.querySelector("#search");
const count = document.querySelector("#visible-count");
const filters = [...document.querySelectorAll(".filter")];
let activeFilter = "all";

function clean(value) {
  return String(value || "");
}

function html(value) {
  return clean(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function matchesFilter(entry) {
  if (activeFilter === "all") return true;
  if (activeFilter === "playable") return Boolean(entry.playable);
  if (activeFilter === "accolade") return Boolean(entry.hasAccolade);
  const haystack = [...(entry.categories || []), ...(entry.details || [])].join(" ").toLowerCase();
  return haystack.includes(activeFilter);
}

function matchesSearch(entry) {
  const query = clean(search.value).trim().toLowerCase();
  if (!query) return true;
  const haystack = [
    entry.title,
    entry.year,
    entry.description,
    ...(entry.categories || []),
    ...(entry.details || []),
  ].join(" ").toLowerCase();
  return haystack.includes(query);
}

function initials(title) {
  return clean(title)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function renderCard(entry) {
  const categories = (entry.categories || []).slice(0, 4);
  const links = (entry.links || []).slice(0, 2);
  const meta = [entry.year, entry.gameNumber ? `Game ${entry.gameNumber}/100` : "", entry.developmentTime]
    .filter(Boolean)
    .join(" · ");
  const thumb = entry.image
    ? `<img src="${html(entry.image)}" alt="">`
    : `<span class="fallback-thumb">${html(initials(entry.title))}</span>`;
  const linkMarkup = links.map((link) => `<a href="${html(link.url)}">${html(link.label)}</a>`).join("");
  const archiveLink = `<a href="${html(entry.sourceUrl)}">Original</a>`;
  return `<article class="portfolio-card">
    <div class="thumb">${thumb}</div>
    <div class="portfolio-body">
      <span class="meta">${html(meta || "Archive Entry")}</span>
      <h3>${html(entry.title)}</h3>
      <p>${html(entry.description || "Recovered from the JUSTDELETEIT WordPress archive.")}</p>
      <div class="tags">${categories.map((category) => `<span class="tag">${html(category)}</span>`).join("")}</div>
      <div class="card-links">${linkMarkup}${archiveLink}</div>
    </div>
  </article>`;
}

function render() {
  const visible = entries.filter((entry) => matchesFilter(entry) && matchesSearch(entry));
  count.textContent = visible.length;
  grid.innerHTML = visible.length
    ? visible.map(renderCard).join("")
    : `<p class="empty">No archive entries match that search.</p>`;
}

filters.forEach((filter) => {
  filter.addEventListener("click", () => {
    activeFilter = filter.dataset.filter;
    filters.forEach((item) => item.classList.toggle("is-active", item === filter));
    render();
  });
});

search.addEventListener("input", render);
render();
"""


def build_readme(entries: list[dict]) -> str:
    with_images = sum(1 for entry in entries if entry["image"])
    return f"""# JUST404IT Static Site

This is the new static starter site for `just404it.com`, generated from the public safety backup of `justdeleteit.com`.

## What Is Here

- `index.html` - the new hub plus searchable archive.
- `assets/site.css` and `assets/site.js` - the editable front-end.
- `data/portfolio.json` and `data/portfolio.js` - {len(entries)} recovered portfolio entries.
- `assets/portfolio/` - {with_images} copied portfolio images from the backup.
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
$env:JUSTDELETEIT_BACKUP_ROOT = 'C:\\path\\to\\the\\extracted-backup'
py -3.12 tools\\build_static_site.py
```
"""


def build_404_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>404 - JUST404IT</title>
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <main class="hero">
    <p class="eyebrow">404, naturally</p>
    <h1>This page wandered off.</h1>
    <p class="lede">The archive is still intact. Head back to the hub and try the search.</p>
    <div class="hero-actions"><a class="button primary" href="./">Back to JUST404IT</a></div>
  </main>
</body>
</html>
"""


def main() -> None:
    if not PORTFOLIO_ROOT.exists():
        raise SystemExit(f"Missing portfolio backup: {PORTFOLIO_ROOT}")
    PORTFOLIO_ASSETS.mkdir(parents=True, exist_ok=True)
    entries = build_portfolio_data()
    write_portfolio_data(entries)
    write_text(SITE_ROOT / "index.html", build_index_html(entries))
    write_text(SITE_ROOT / "archive" / "index.html", build_archive_html(len(entries)))
    write_text(SITE_ROOT / "404.html", build_404_html())
    write_text(SITE_ROOT / "assets" / "site.css", build_css())
    write_text(SITE_ROOT / "assets" / "site.js", build_js())
    write_text(SITE_ROOT / "README.md", build_readme(entries))
    print(f"Generated {len(entries)} portfolio entries in {SITE_ROOT}")


if __name__ == "__main__":
    main()
