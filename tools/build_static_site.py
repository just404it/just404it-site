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
SITE_URL = os.environ.get(
    "JUST404IT_SITE_URL", "https://just404it.github.io/just404it-site"
).rstrip("/")
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

FORMAT_CATEGORIES = {"Digital": "digital", "Analog": "analog", "Intermedia Games": "intermedia"}
PLATFORM_CATEGORIES = {"Online": "web", "PC": "pc", "Mac": "mac"}
CONTEXT_CATEGORIES = {
    "Jam Games": "jam",
    "Personal Games": "personal",
    "Serious Games": "serious",
    "Silly Games": "silly",
    "Interactive Fiction": "interactive-fiction",
    "Music Videogames": "music",
}
RECOGNITION_CATEGORIES = {"Award Winning": "award-winning", "Exhibited": "exhibited"}
ACCESS_LABELS = {
    "online": "Play online",
    "download": "Download",
    "watch": "Watch",
    "rules": "Rules / print",
}
PACE_LABELS = {
    "day-or-less": "One day or less",
    "days": "Days",
    "weeks": "Weeks",
    "months-plus": "Months+",
}
ALLOWED_ARTICLE_TAGS = {"p", "em", "strong", "blockquote", "ul", "ol", "li", "br", "a", "h2", "h3"}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


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


def local_article_href(href: str) -> str:
    parsed = urlparse(href)
    if parsed.netloc.lower() in {"www.justdeleteit.com", "justdeleteit.com"}:
        match = re.fullmatch(r"/portfolio/([^/]+)/?", parsed.path)
        if match:
            return f"../../games/{match.group(1)}/"
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return ""
    return href


def extract_article_html(soup: BeautifulSoup) -> str:
    article = soup.find("article")
    if not article:
        return ""
    clone = BeautifulSoup(str(article), "html.parser")
    root = clone.find("article")
    if not root:
        return ""
    for tag in list(root.find_all(True)):
        if tag.name not in ALLOWED_ARTICLE_TAGS:
            tag.unwrap()
            continue
        if tag.name == "a":
            href = local_article_href(tag.get("href", "").strip())
            if not href:
                tag.unwrap()
                continue
            tag.attrs = {"href": href}
            if href.startswith(("http://", "https://")):
                tag.attrs["rel"] = "noopener"
        else:
            tag.attrs = {}
    return "".join(str(child) for child in root.contents).strip()


def extract_game_numbers(details: list[str]) -> list[int]:
    for detail in details:
        match = re.search(r"Games?\s+(.+?)\s+of\s+100", detail, re.I)
        if not match:
            continue
        numbers = [int(value) for value in re.findall(r"\d+", match.group(1))]
        return sorted({value for value in numbers if 1 <= value <= 100})
    return []


def series_label(numbers: list[int]) -> str:
    if not numbers:
        return "Archive project"
    if len(numbers) == 1:
        return f"Game {numbers[0]}/100"
    if numbers == list(range(numbers[0], numbers[-1] + 1)):
        return f"Games {numbers[0]}-{numbers[-1]}/100"
    return "Games " + ", ".join(str(value) for value in numbers) + "/100"


def development_scale(value: str) -> tuple[float | None, str]:
    normalized = compact(value).lower()
    match = re.search(r"(\d+|one|two|three|four|five|six)\s*(hour|day|week|month|year)s?", normalized)
    if not match:
        return None, ""
    amount = int(match.group(1)) if match.group(1).isdigit() else NUMBER_WORDS[match.group(1)]
    unit = match.group(2)
    days = amount / 24 if unit == "hour" else amount
    if unit == "week":
        days *= 7
    elif unit == "month":
        days *= 30
    elif unit == "year":
        days *= 365
    if unit == "hour" or (unit == "day" and amount <= 1):
        pace = "day-or-less"
    elif unit == "day":
        pace = "days"
    elif unit == "week":
        pace = "weeks"
    else:
        pace = "months-plus"
    return round(days, 3), pace


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

    game_numbers = extract_game_numbers(details)
    game_number = str(max(game_numbers)) if game_numbers else ""
    development_time = ""
    for detail in details:
        dev_match = re.search(r"Development time:\s*(.+)", detail, re.I)
        if dev_match:
            development_time = compact(dev_match.group(1))

    accolade_details = [detail for detail in details if AWARD_WORDS.search(detail)]
    credits = [
        detail
        for detail in details
        if re.match(r"^(made by|assembled by|canceled game by|james earl cox iii$|see description for team info)", detail, re.I)
    ]
    playable = bool(any(PLAY_WORDS.search(link["label"]) for link in links))
    page_text = path.read_text(encoding="utf-8", errors="ignore")
    video_match = re.search(r"videoId:\s*['\"]([^'\"]+)", page_text)
    formats = [FORMAT_CATEGORIES[cat] for cat in categories if cat in FORMAT_CATEGORIES]
    platforms = [PLATFORM_CATEGORIES[cat] for cat in categories if cat in PLATFORM_CATEGORIES]
    contexts = [CONTEXT_CATEGORIES[cat] for cat in categories if cat in CONTEXT_CATEGORIES]
    recognition = [RECOGNITION_CATEGORIES[cat] for cat in categories if cat in RECOGNITION_CATEGORIES]
    development_days, development_pace = development_scale(development_time)
    access = []
    if "web" in platforms:
        access.append("online")
    if any(re.search(r"\bdownload\b", link["label"], re.I) for link in links):
        access.append("download")
    if video_match:
        access.append("watch")
    if any(re.search(r"\b(rules?|print)\b", link["label"], re.I) for link in links):
        access.append("rules")

    return {
        "slug": slug,
        "title": title,
        "year": year,
        "categories": categories,
        "description": extract_description(soup),
        "image": local_image,
        "sourceUrl": source_url,
        "gameNumber": game_number,
        "gameNumbers": game_numbers,
        "seriesLabel": series_label(game_numbers),
        "developmentTime": development_time,
        "developmentDays": development_days,
        "developmentPace": development_pace,
        "details": details,
        "links": links[:12],
        "credits": credits,
        "accolades": accolade_details,
        "formats": formats,
        "platforms": platforms,
        "contexts": contexts,
        "recognition": recognition,
        "access": access,
        "bodyHtml": extract_article_html(soup),
        "videoId": video_match.group(1) if video_match else "",
        "detailPath": f"games/{slug}/",
        "hasAccolade": bool(accolade_details or recognition),
        "playable": playable,
    }


def sort_key(entry: dict) -> tuple:
    year = int(entry["year"]) if entry.get("year", "").isdigit() else 0
    game = max(entry.get("gameNumbers") or [0])
    return (-year, -game, entry["title"].lower())


def trim_meta(value: str, limit: int = 155) -> str:
    value = compact(value)
    if len(value) <= limit:
        return value
    shortened = value[: limit + 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return shortened + "."


def project_meta_description(entry: dict, public_description: str) -> str:
    if len(compact(public_description)) >= 50:
        return trim_meta(public_description)
    year = f" ({entry['year']})" if entry.get("year") else ""
    descriptors = []
    descriptors.extend(entry.get("formats", [])[:1])
    descriptors.extend(entry.get("contexts", [])[:2])
    descriptor_text = ", ".join(value.replace("-", " ") for value in descriptors)
    suffix = f" {descriptor_text.capitalize()} game." if descriptor_text else ""
    return trim_meta(
        f"{entry['title']}, {entry['seriesLabel']} by James Earl Cox III, "
        f"from the 100 Games in 5 Years archive{year}.{suffix}"
    )


def build_portfolio_data() -> list[dict]:
    paths = sorted(PORTFOLIO_ROOT.glob("*/index.html"))
    entries = [extract_portfolio_entry(path) for path in paths]
    return sorted(entries, key=sort_key)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = "\n".join(line.rstrip() for line in value.splitlines())
    if value.endswith(("\n", "\r")):
        normalized += "\n"
    path.write_text(normalized, encoding="utf-8", newline="\n")


def write_portfolio_data(entries: list[dict]) -> None:
    data = json.dumps(entries, ensure_ascii=False, indent=2)
    write_text(SITE_ROOT / "data" / "portfolio.json", data + "\n")
    write_text(SITE_ROOT / "data" / "portfolio.js", "window.JUST404IT_PORTFOLIO = " + data + ";\n")


def build_index_html(entries: list[dict]) -> str:
    featured_slugs = [
        "bundle-kitt",
        "you-must-be-18-or-older-to-enter",
        "moloch-zero",
        "temporality",
        "bottle-rockets",
        "an-occurrence-at-owl-creek-bridge",
    ]
    entries_by_slug = {entry["slug"]: entry for entry in entries}
    featured = [entries_by_slug[slug] for slug in featured_slugs if slug in entries_by_slug]

    def initials(title: str) -> str:
        return "".join(part[0] for part in title.split()[:2]).upper()

    def feature_media(entry: dict) -> str:
        if entry["image"]:
            return f'<img src="{escape(entry["image"])}" alt="">'
        return (
            f'<span class="feature-series">{escape(entry["seriesLabel"])}</span>'
            f'<b aria-hidden="true">{escape(initials(entry["title"]))}</b>'
        )

    cards = "\n".join(
        f"""
        <a class="feature-card" href="{escape(entry['detailPath'])}">
          <span class="feature-media">{feature_media(entry)}</span>
          <span class="feature-copy">
            <span class="feature-kicker">{escape(entry['year'] or 'Archive')} · {escape(entry['seriesLabel'])}</span>
            <strong>{escape(entry['title'])}</strong>
            <span>{escape(entry['description'] or ', '.join(entry['categories'][:3]) or '100 Games in 5 Years archive entry')}</span>
          </span>
        </a>"""
        for entry in featured
    )

    def facet_count(field: str, value: str) -> int:
        return sum(
            value in current if isinstance(current := entry.get(field), list) else current == value
            for entry in entries
        )

    def facet_button(group: str, value: str, label: str, count: int) -> str:
        return (
            f'<button class="facet" type="button" data-group="{group}" data-value="{value}" '
            f'aria-pressed="false">{label}<span>{count}</span></button>'
        )

    format_buttons = "".join(
        facet_button("formats", value, label.replace(" Games", ""), facet_count("formats", value))
        for label, value in FORMAT_CATEGORIES.items()
    )
    context_buttons = "".join(
        facet_button("contexts", value, label.replace(" Games", ""), facet_count("contexts", value))
        for label, value in CONTEXT_CATEGORIES.items()
    )
    platform_buttons = "".join(
        facet_button("platforms", value, label, facet_count("platforms", value))
        for label, value in PLATFORM_CATEGORIES.items()
    )
    recognition_buttons = "".join(
        facet_button("recognition", value, label, facet_count("recognition", value))
        for label, value in RECOGNITION_CATEGORIES.items()
    )
    access_buttons = "".join(
        facet_button("access", value, label, facet_count("access", value))
        for value, label in ACCESS_LABELS.items()
    )
    pace_buttons = "".join(
        facet_button("pace", value, label, facet_count("developmentPace", value))
        for value, label in PACE_LABELS.items()
    )
    years = sorted({entry["year"] for entry in entries if entry["year"]}, reverse=True)
    year_options = "".join(f'<option value="{year}">{year}</option>' for year in years)
    represented_games = len({number for entry in entries for number in entry["gameNumbers"]})
    playable_count = sum(entry["playable"] for entry in entries)
    recognized_count = sum(entry["hasAccolade"] for entry in entries)
    home_description = (
        "Games, films, writing, and experiments by James Earl Cox III, "
        "including the complete 100 Games in 5 Years archive."
    )
    home_schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebSite",
                    "@id": f"{SITE_URL}/#website",
                    "url": f"{SITE_URL}/",
                    "name": "JUST404IT",
                    "description": home_description,
                    "creator": {"@id": f"{SITE_URL}/#james-earl-cox-iii"},
                },
                {
                    "@type": "Person",
                    "@id": f"{SITE_URL}/#james-earl-cox-iii",
                    "name": "James Earl Cox III",
                    "url": f"{SITE_URL}/",
                },
            ],
        },
        ensure_ascii=False,
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JUST404IT - James Earl Cox III</title>
  <meta name="description" content="{escape(home_description, quote=True)}">
  <meta name="theme-color" content="#0e0f0f">
  <link rel="canonical" href="{SITE_URL}/">
  <meta property="og:type" content="website">
  <meta property="og:title" content="JUST404IT - James Earl Cox III">
  <meta property="og:description" content="{escape(home_description, quote=True)}">
  <meta property="og:url" content="{SITE_URL}/">
  <meta name="twitter:card" content="summary">
  <script type="application/ld+json">{home_schema}</script>
  <link rel="icon" type="image/png" href="assets/favicon.png">
  <link rel="apple-touch-icon" href="assets/favicon.png">
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <header class="site-head">
    <nav class="nav" aria-label="Primary">
      <a class="mark" href="./"><span>JUST</span>404<span>IT</span></a>
      <div class="nav-links">
        <a href="#selected">Selected work</a>
        <a href="#archive">100 Games</a>
        <a href="#elsewhere">Elsewhere</a>
      </div>
    </nav>
    <section class="hero" aria-labelledby="hero-title">
      <p class="eyebrow">James Earl Cox III</p>
      <h1 id="hero-title">JUST404IT</h1>
      <p class="lede">Games, films, writing, and experiments. Start with the work. The archive has the rest.</p>
      <div class="hero-actions">
        <a class="button primary" href="#selected">Selected work</a>
        <a class="button" href="#archive">Browse all 100</a>
      </div>
      <dl class="hero-stats" aria-label="Archive summary">
        <div><dt>{represented_games}</dt><dd>games</dd></div>
        <div><dt>{len(entries)}</dt><dd>project pages</dd></div>
        <div><dt>2012–2017</dt><dd>five-year run</dd></div>
      </dl>
    </section>
  </header>

  <main>
    <section class="band featured" id="selected" aria-labelledby="featured-title">
      <div class="section-heading">
        <p class="eyebrow">Selected work</p>
        <h2 id="featured-title">Six useful places to start.</h2>
      </div>
      <div class="feature-grid">
        {cards}
      </div>
    </section>

    <section class="band archive-band" id="archive" aria-labelledby="archive-title">
      <div class="section-heading archive-heading">
        <div>
          <p class="eyebrow">Complete series</p>
          <h2 id="archive-title">100 Games in 5 Years</h2>
          <p class="section-note">Every game is represented. Two project pages contain multi-game sets.</p>
        </div>
        <div class="archive-heading-side">
          <p class="count" id="result-summary" role="status" aria-live="polite" aria-atomic="true"><span id="visible-count">0</span> project pages</p>
          <a class="text-index-link" href="archive/">Complete text index</a>
        </div>
      </div>
      <div class="archive-tools">
        <div class="quick-routes" aria-label="Quick routes">
          <span>Pick a door</span>
          <button type="button" data-preset="play-now">Play something now</button>
          <button type="button" data-preset="nonsense">Give me nonsense</button>
          <button type="button" data-preset="serious">Get serious</button>
          <button type="button" data-preset="off-screen">Go off-screen</button>
          <button type="button" data-preset="made-fast">Made in a day</button>
          <button type="button" data-preset="decorated">The decorated ones</button>
        </div>
        <div class="archive-utility" role="search">
          <label class="control search-control" for="search"><span>Search</span><input id="search" type="search" placeholder="Title, credit, category, award"></label>
          <label class="control" for="sort"><span>Sort</span><select id="sort">
            <option value="series-desc">Series: 100 to 1</option>
            <option value="series-asc">Series: 1 to 100</option>
            <option value="newest">Year: newest first</option>
            <option value="oldest">Year: oldest first</option>
            <option value="title">Title: A to Z</option>
            <option value="fastest">Build time: fastest first</option>
            <option value="longest">Build time: longest first</option>
          </select></label>
          <label class="control" for="year"><span>Year</span><select id="year"><option value="all">All years</option>{year_options}</select></label>
          <button class="surprise-button" id="surprise-me" type="button">Surprise me</button>
          <button class="reset-button" id="reset-filters" type="button">Reset</button>
        </div>
        <div class="facet-groups" aria-label="Archive filters">
          <fieldset class="facet-group"><legend>Status</legend><div>
            <button class="facet is-active" type="button" data-group="status" data-value="all" aria-pressed="true">All<span>{len(entries)}</span></button>
            <button class="facet facet-playable" type="button" data-group="status" data-value="playable" aria-pressed="false">Playable<span>{playable_count}</span></button>
            <button class="facet facet-recognition" type="button" data-group="status" data-value="recognized" aria-pressed="false">Recognized<span>{recognized_count}</span></button>
          </div></fieldset>
          <fieldset class="facet-group facet-format"><legend>Format</legend><div>{format_buttons}</div></fieldset>
          <fieldset class="facet-group"><legend>Context</legend><div>{context_buttons}</div></fieldset>
          <fieldset class="facet-group"><legend>Platform</legend><div>{platform_buttons}</div></fieldset>
        </div>
        <details class="more-filters">
          <summary>More ways in</summary>
          <div class="facet-groups facet-groups-more">
            <fieldset class="facet-group"><legend>Recognition</legend><div>{recognition_buttons}</div></fieldset>
            <fieldset class="facet-group"><legend>Do something</legend><div>{access_buttons}</div></fieldset>
            <fieldset class="facet-group"><legend>Build time</legend><div>{pace_buttons}</div></fieldset>
          </div>
        </details>
        <div class="active-filters" id="active-filters" hidden>
          <span>Active</span>
          <div id="active-filter-list"></div>
        </div>
      </div>
      <div class="portfolio-grid" id="portfolio-grid"></div>
      <noscript><p class="noscript-index">JavaScript is off. The <a href="archive/">complete text index</a> still has every project.</p></noscript>
    </section>

    <section class="band elsewhere" id="elsewhere" aria-labelledby="elsewhere-title">
      <div class="section-heading">
        <p class="eyebrow">Elsewhere</p>
        <h2 id="elsewhere-title">The work refuses to stay on one website.</h2>
      </div>
      <div class="elsewhere-grid">
        <a href="https://www.seempoint.com/"><span>Studio</span><strong>Seemingly Pointless</strong><small>Games and collaborative work</small></a>
        <a href="https://just404it.itch.io/"><span>Play</span><strong>itch.io</strong><small>Downloads and browser games</small></a>
        <a href="https://www.llamageddonfilm.com/"><span>Film</span><strong>Llamageddon</strong><small>A killer space llama remains involved</small></a>
      </div>
    </section>
  </main>

  <footer class="footer">
    <a class="mark" href="./"><span>JUST</span>404<span>IT</span></a>
    <p>James Earl Cox III · Games and other evidence</p>
  </footer>
  <script src="data/portfolio.js"></script>
  <script src="assets/site.js"></script>
</body>
</html>
"""


def build_archive_html(entries: list[dict]) -> str:
    items = "\n".join(
        f'<li><a href="../{escape(entry["detailPath"])}"><span>{escape(entry["seriesLabel"])}</span>'
        f'<strong>{escape(entry["title"])}</strong><small>{escape(entry["year"] or "Archive")}</small></a></li>'
        for entry in sorted(entries, key=lambda item: max(item.get("gameNumbers") or [0]), reverse=True)
    )
    represented_games = len({number for entry in entries for number in entry["gameNumbers"]})
    archive_description = "A crawlable text index of James Earl Cox III's complete 100 Games in 5 Years archive."
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": "100 Games in 5 Years - Complete Index",
            "url": f"{SITE_URL}/archive/",
            "description": archive_description,
            "mainEntity": {
                "@type": "ItemList",
                "numberOfItems": len(entries),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "name": entry["title"],
                        "url": f'{SITE_URL}/{entry["detailPath"]}',
                    }
                    for index, entry in enumerate(entries, start=1)
                ],
            },
        },
        ensure_ascii=False,
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>100 Games in 5 Years - Complete Index · JUST404IT</title>
  <meta name="description" content="{escape(archive_description, quote=True)}">
  <meta name="theme-color" content="#0e0f0f">
  <link rel="canonical" href="{SITE_URL}/archive/">
  <meta property="og:type" content="website">
  <meta property="og:title" content="100 Games in 5 Years - Complete Index">
  <meta property="og:description" content="{escape(archive_description, quote=True)}">
  <meta property="og:url" content="{SITE_URL}/archive/">
  <script type="application/ld+json">{schema}</script>
  <link rel="icon" type="image/png" href="../assets/favicon.png">
  <link rel="apple-touch-icon" href="../assets/favicon.png">
  <link rel="stylesheet" href="../assets/site.css">
</head>
<body>
  <nav class="nav project-nav" aria-label="Primary">
    <a class="mark" href="../"><span>JUST</span>404<span>IT</span></a>
    <div class="nav-links"><a href="../#selected">Selected work</a><a href="../#archive">Visual archive</a></div>
  </nav>
  <main class="archive-index-page">
    <a class="back-link" href="../#archive">← Filter the archive</a>
    <header>
      <p class="eyebrow">Complete text index</p>
      <h1>100 Games in 5 Years</h1>
      <p>{len(entries)} project pages representing all {represented_games} games.</p>
    </header>
    <ol class="archive-index-list">{items}</ol>
  </main>
  <footer class="footer"><a class="mark" href="../"><span>JUST</span>404<span>IT</span></a><p>James Earl Cox III · Complete index</p></footer>
</body>
</html>
"""


def build_sitemap(entries: list[dict]) -> str:
    urls = [f"{SITE_URL}/", f"{SITE_URL}/archive/"] + [
        f'{SITE_URL}/{entry["detailPath"]}' for entry in entries
    ]
    body = "\n".join(f"  <url><loc>{escape(url)}</loc></url>" for url in urls)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
'''


def build_robots() -> str:
    return f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""


def category_tag(category: str) -> str:
    if re.fullmatch(r"20\d{2}", category):
        kind = "year"
    elif category in FORMAT_CATEGORIES:
        kind = f"format format-{FORMAT_CATEGORIES[category]}"
    elif category in PLATFORM_CATEGORIES:
        kind = "platform"
    elif category in CONTEXT_CATEGORIES:
        kind = "context"
    elif category in RECOGNITION_CATEGORIES:
        kind = "recognition"
    else:
        kind = "neutral"
    return f'<span class="tag tag-{kind}">{escape(category)}</span>'


def build_game_html(entry: dict, newer: dict | None, earlier: dict | None) -> str:
    description = entry["description"] or "A project from the 100 Games in 5 Years archive."
    meta_description = project_meta_description(entry, description)
    categories = "".join(
        category_tag(category) for category in entry["categories"] if not re.fullmatch(r"20\d{2}", category)
    )
    links = "".join(
        f'<a class="project-link" href="{escape(link["url"], quote=True)}">{escape(link["label"])}</a>'
        for link in entry["links"]
    )
    credits = "".join(f"<li>{escape(item)}</li>" for item in entry["credits"])
    accolades = "".join(f"<li>{escape(item)}</li>" for item in entry["accolades"])
    body = entry["bodyHtml"] or f"<p>{escape(description)}</p>"

    if entry["image"]:
        media = f'<img src="../../{escape(entry["image"])}" alt="">'
    elif entry["videoId"]:
        video_id = escape(entry["videoId"], quote=True)
        initials = "".join(part[0] for part in entry["title"].split()[:2]).upper()
        media = f"""<a class="project-video" href="https://www.youtube.com/watch?v={video_id}">
          <img src="https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" alt="Video still for {escape(entry['title'], quote=True)}" referrerpolicy="no-referrer">
          <b class="project-video-initials" aria-hidden="true">{escape(initials)}</b>
          <span>Watch video</span>
        </a>"""
    else:
        initials = "".join(part[0] for part in entry["title"].split()[:2]).upper()
        media = f'<span class="project-poster-index">{escape(entry["seriesLabel"])}</span><b>{escape(initials)}</b>'

    newer_link = (
        f'<a href="../../{escape(newer["detailPath"])}"><span>Newer in series</span><strong>{escape(newer["title"])}</strong></a>'
        if newer
        else "<span></span>"
    )
    earlier_link = (
        f'<a href="../../{escape(earlier["detailPath"])}"><span>Earlier in series</span><strong>{escape(earlier["title"])}</strong></a>'
        if earlier
        else "<span></span>"
    )
    canonical_url = f'{SITE_URL}/{entry["detailPath"]}'
    image_url = ""
    if entry["image"]:
        image_url = f'{SITE_URL}/{entry["image"]}'
    elif entry["videoId"]:
        image_url = f'https://i.ytimg.com/vi/{entry["videoId"]}/hqdefault.jpg'
    schema_type = "VideoGame" if "digital" in entry["formats"] else "Game"
    schema_data = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": entry["title"],
        "url": canonical_url,
        "description": meta_description,
        "creator": {
            "@type": "Person",
            "name": "James Earl Cox III",
            "url": f"{SITE_URL}/",
        },
    }
    if entry["year"]:
        schema_data["datePublished"] = entry["year"]
    if entry["categories"]:
        schema_data["genre"] = [
            category for category in entry["categories"] if not re.fullmatch(r"20\d{2}", category)
        ]
    if image_url:
        schema_data["image"] = image_url
    schema = json.dumps(schema_data, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(entry['title'])} · JUST404IT</title>
  <meta name="description" content="{escape(meta_description, quote=True)}">
  <meta name="theme-color" content="#0e0f0f">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{escape(entry['title'], quote=True)}">
  <meta property="og:description" content="{escape(meta_description, quote=True)}">
  <meta property="og:url" content="{canonical_url}">
  {f'<meta property="og:image" content="{escape(image_url, quote=True)}">' if image_url else ''}
  <meta name="twitter:card" content="{'summary_large_image' if image_url else 'summary'}">
  <script type="application/ld+json">{schema}</script>
  <link rel="icon" type="image/png" href="../../assets/favicon.png">
  <link rel="apple-touch-icon" href="../../assets/favicon.png">
  <link rel="stylesheet" href="../../assets/site.css">
</head>
<body>
  <nav class="nav project-nav" aria-label="Primary">
    <a class="mark" href="../../"><span>JUST</span>404<span>IT</span></a>
    <div class="nav-links"><a href="../../#selected">Selected work</a><a href="../../#archive">100 Games</a></div>
  </nav>
  <main class="project-page">
    <a class="back-link" href="../../#archive">← All 100 games</a>
    <section class="project-hero" aria-labelledby="project-title">
      <div class="project-media">{media}</div>
      <div class="project-heading">
        <p class="eyebrow">{escape(entry['seriesLabel'])}</p>
        <h1 id="project-title"{' class="project-title-long"' if len(entry['title']) > 58 else ''}>{escape(entry['title'])}</h1>
        <p class="project-deck">{escape(description)}</p>
        <div class="project-facts">
          {f'<span><b>Year</b>{escape(entry["year"])}</span>' if entry['year'] else ''}
          {f'<span><b>Development</b>{escape(entry["developmentTime"])}</span>' if entry['developmentTime'] else ''}
          <span><b>Availability</b>{'Playable' if entry['playable'] else 'Documented'}</span>
        </div>
        <div class="tags project-tags">{categories}</div>
      </div>
    </section>

    <section class="project-content">
      <article class="project-body">{body}</article>
      <aside class="project-aside">
        {f'<section><h2>Play and explore</h2><div class="project-links">{links}</div></section>' if links else ''}
        {f'<section><h2>Credits</h2><ul>{credits}</ul></section>' if credits else ''}
        {f'<section><h2>Recognition</h2><ul>{accolades}</ul></section>' if accolades else ''}
        <section><h2>Archive record</h2><p>Recovered from the public 100 Games in 5 Years site backup.</p></section>
      </aside>
    </section>

    <nav class="project-sequence" aria-label="100 Games sequence">{newer_link}{earlier_link}</nav>
  </main>
  <footer class="footer"><a class="mark" href="../../"><span>JUST</span>404<span>IT</span></a><p>James Earl Cox III · {escape(entry['seriesLabel'])}</p></footer>
</body>
</html>
"""


def _build_css_legacy() -> str:
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


def _build_js_legacy() -> str:
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


def build_css() -> str:
    return """:root {
  color-scheme: dark;
  --bg: #0e0f0f;
  --surface: #161816;
  --surface-2: #1d201e;
  --ink: #f5f1e8;
  --muted: #b8b5ad;
  --quiet: #817f78;
  --line: #373b37;
  --line-strong: #5d625d;
  --coral: #ff5d3d;
  --mint: #72e2b7;
  --blue: #78c9ff;
  --pink: #ec91c8;
  --violet: #b7a7ff;
  --gold: #f3c662;
  --max: 1240px;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { background: var(--bg); color: var(--ink); margin: 0; }
button, input, select { font: inherit; }
a { color: inherit; text-decoration: none; }
img { display: block; max-width: 100%; }

:focus-visible {
  outline: 3px solid var(--mint);
  outline-offset: 3px;
}

.site-head { border-bottom: 1px solid var(--line); min-height: 78svh; }
.nav {
  align-items: center;
  background: rgba(14, 15, 15, 0.94);
  border-bottom: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  margin: 0 auto;
  max-width: var(--max);
  min-height: 68px;
  padding: 14px 28px;
  position: sticky;
  top: 0;
  z-index: 20;
}

.mark {
  font-family: "Courier New", ui-monospace, monospace;
  font-size: 1.5rem;
  font-weight: 900;
  white-space: nowrap;
}
.mark span:first-child { color: var(--coral); }
.mark span:last-child { color: var(--pink); }
.nav-links { display: flex; flex-wrap: wrap; gap: 8px; }
.nav-links a, .button, .reset-button, .project-link {
  border: 1px solid var(--line);
  min-height: 42px;
  padding: 10px 14px;
}
.nav-links a:hover, .button:hover, .reset-button:hover, .project-link:hover {
  border-color: var(--mint);
  color: var(--mint);
}

.hero {
  display: flex;
  flex-direction: column;
  justify-content: center;
  margin: 0 auto;
  max-width: var(--max);
  min-height: 620px;
  padding: 86px 28px 78px;
}
.eyebrow, .feature-kicker, .meta, .control > span, .facet-group legend, .project-poster-index, .feature-series {
  color: var(--gold);
  font-family: "Courier New", ui-monospace, monospace;
  font-size: 0.77rem;
  font-weight: 700;
  text-transform: uppercase;
}
h1, h2, h3 { letter-spacing: 0; margin: 0; overflow-wrap: anywhere; }
h1 { font-size: 8rem; line-height: 0.88; max-width: 9ch; }
h2 { font-size: 3.5rem; line-height: 0.98; max-width: 18ch; }
h3 { font-size: 1.25rem; line-height: 1.1; }
.lede { color: var(--muted); font-size: 1.45rem; line-height: 1.48; margin: 28px 0; max-width: 730px; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 10px; }
.button { cursor: pointer; font-weight: 800; }
.button.primary { background: var(--coral); border-color: var(--coral); color: #160b07; }
.button.primary:hover { background: var(--ink); border-color: var(--ink); color: var(--bg); }
.hero-stats { display: flex; gap: 0; margin: 58px 0 0; }
.hero-stats div { border-left: 1px solid var(--line); min-width: 150px; padding: 0 20px; }
.hero-stats div:first-child { padding-left: 0; border-left: 0; }
.hero-stats dt { font-family: "Courier New", ui-monospace, monospace; font-size: 1.45rem; font-weight: 800; }
.hero-stats dd { color: var(--quiet); margin: 4px 0 0; }

.band { border-bottom: 1px solid var(--line); padding: 100px 28px; }
.band > * { margin-left: auto; margin-right: auto; max-width: var(--max); }
.section-heading { align-items: end; display: flex; justify-content: space-between; margin-bottom: 38px; gap: 28px; }
.section-heading .eyebrow { margin: 0 0 12px; }
.section-note { color: var(--muted); line-height: 1.55; margin: 16px 0 0; max-width: 600px; }

.feature-grid { display: grid; gap: 16px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.feature-card { background: var(--surface); border: 1px solid var(--line); display: flex; flex-direction: column; min-height: 100%; }
.feature-card:hover { border-color: var(--mint); transform: translateY(-2px); }
.feature-media { align-items: center; aspect-ratio: 16 / 10; background: var(--surface-2); border-bottom: 1px solid var(--line); display: flex; justify-content: center; overflow: hidden; padding: 18px; position: relative; }
.feature-media img { height: 100%; object-fit: cover; width: 100%; }
.feature-media b { color: var(--pink); font-family: "Courier New", ui-monospace, monospace; font-size: 3rem; }
.feature-series { left: 16px; position: absolute; top: 14px; }
.feature-copy { display: flex; flex: 1; flex-direction: column; gap: 12px; padding: 20px; }
.feature-copy strong { font-size: 1.35rem; line-height: 1.08; }
.feature-copy > span:last-child { color: var(--muted); display: -webkit-box; line-height: 1.5; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }

.archive-band { background: #111312; }
.archive-heading { align-items: flex-end; }
.archive-heading-side { align-items: flex-end; display: grid; gap: 9px; justify-items: end; }
.count { color: var(--muted); font-family: "Courier New", ui-monospace, monospace; margin: 0; }
.count span { color: var(--ink); font-size: 1.4rem; font-weight: 800; }
.text-index-link { border-bottom: 1px solid var(--line-strong); color: var(--mint); font-size: 0.82rem; padding-bottom: 3px; }
.archive-tools { background: var(--surface); border: 1px solid var(--line); margin-bottom: 28px; }
.quick-routes { align-items: center; border-bottom: 1px solid var(--line); display: flex; flex-wrap: wrap; gap: 8px; padding: 14px 18px; }
.quick-routes > span, .active-filters > span {
  color: var(--gold);
  font-family: "Courier New", ui-monospace, monospace;
  font-size: 0.72rem;
  font-weight: 700;
  margin-right: 4px;
  text-transform: uppercase;
}
.quick-routes button {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--muted);
  cursor: pointer;
  min-height: 34px;
  padding: 6px 9px;
}
.quick-routes button:hover { border-color: var(--pink); color: var(--pink); }
.archive-utility { align-items: end; border-bottom: 1px solid var(--line); display: grid; gap: 12px; grid-template-columns: minmax(250px, 1fr) 210px 140px auto auto; padding: 18px; }
.control { display: grid; gap: 7px; }
.control input, .control select {
  background: var(--bg);
  border: 1px solid var(--line-strong);
  border-radius: 0;
  color: var(--ink);
  min-height: 46px;
  padding: 10px 12px;
  width: 100%;
}
.control input:focus, .control select:focus { border-color: var(--mint); }
.reset-button, .surprise-button { background: transparent; color: var(--muted); cursor: pointer; }
.surprise-button {
  background: var(--coral);
  border: 1px solid var(--coral);
  color: #170b07;
  font-weight: 800;
  min-height: 42px;
  padding: 10px 14px;
}
.surprise-button:hover { background: var(--ink); border-color: var(--ink); color: var(--bg); }
.surprise-button:disabled { background: transparent; border-color: var(--line); color: var(--quiet); cursor: not-allowed; }
.facet-groups { display: grid; grid-template-columns: 1fr 1fr 2fr 1fr; }
.facet-group { border: 0; border-right: 1px solid var(--line); margin: 0; min-width: 0; padding: 18px; }
.facet-group:last-child { border-right: 0; }
.facet-group legend { padding: 0; }
.facet-group > div { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 10px; }
.facet {
  align-items: center;
  background: transparent;
  border: 1px solid var(--line);
  color: var(--muted);
  cursor: pointer;
  display: inline-flex;
  gap: 7px;
  min-height: 36px;
  padding: 7px 9px;
}
.facet span { color: var(--quiet); font-family: "Courier New", ui-monospace, monospace; font-size: 0.72rem; }
.facet:hover { border-color: var(--line-strong); color: var(--ink); }
.facet:disabled { cursor: not-allowed; opacity: 0.34; }
.facet:disabled:hover { border-color: var(--line); color: var(--muted); }
.facet.is-active { background: var(--coral); border-color: var(--coral); color: #170b07; }
.facet.is-active span { color: #522015; }
.facet-playable:not(.is-active) { border-color: color-mix(in srgb, var(--mint) 55%, var(--line)); color: var(--mint); }
.facet-recognition:not(.is-active) { border-color: color-mix(in srgb, var(--gold) 55%, var(--line)); color: var(--gold); }
.facet-playable.is-active { background: var(--mint); border-color: var(--mint); color: #08251c; }
.facet-recognition.is-active { background: var(--gold); border-color: var(--gold); color: #2b1d05; }
.facet-playable.is-active span, .facet-recognition.is-active span { color: currentColor; }
.facet[data-group="formats"][data-value="digital"]:not(.is-active) { border-color: color-mix(in srgb, var(--blue) 55%, var(--line)); color: var(--blue); }
.facet[data-group="formats"][data-value="analog"]:not(.is-active) { border-color: color-mix(in srgb, var(--pink) 55%, var(--line)); color: var(--pink); }
.facet[data-group="formats"][data-value="intermedia"]:not(.is-active) { border-color: color-mix(in srgb, var(--violet) 55%, var(--line)); color: var(--violet); }
.facet[data-group="formats"][data-value="digital"].is-active { background: var(--blue); border-color: var(--blue); color: #082033; }
.facet[data-group="formats"][data-value="analog"].is-active { background: var(--pink); border-color: var(--pink); color: #351326; }
.facet[data-group="formats"][data-value="intermedia"].is-active { background: var(--violet); border-color: var(--violet); color: #1e163d; }
.facet[data-group="formats"].is-active span { color: currentColor; }
.more-filters { border-top: 1px solid var(--line); }
.more-filters summary {
  color: var(--mint);
  cursor: pointer;
  font-family: "Courier New", ui-monospace, monospace;
  font-size: 0.78rem;
  font-weight: 700;
  list-style-position: inside;
  padding: 14px 18px;
  text-transform: uppercase;
}
.more-filters[open] summary { border-bottom: 1px solid var(--line); }
.facet-groups-more { grid-template-columns: 1fr 1.4fr 1.3fr; }
.facet-groups-more .facet-group:last-child { border-right: 0; }
.active-filters { align-items: center; border-top: 1px solid var(--line); display: flex; flex-wrap: wrap; gap: 9px; padding: 12px 18px; }
.active-filters[hidden] { display: none; }
.active-filters > div { display: flex; flex-wrap: wrap; gap: 7px; }
.active-filter {
  background: var(--bg);
  border: 1px solid var(--line-strong);
  color: var(--ink);
  cursor: pointer;
  min-height: 32px;
  padding: 5px 8px;
}
.active-filter:hover { border-color: var(--mint); color: var(--mint); }

.portfolio-grid { display: grid; gap: 16px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.portfolio-card { background: var(--surface); border: 1px solid var(--line); display: flex; flex-direction: column; min-height: 100%; }
.portfolio-card:hover { border-color: var(--line-strong); }
.portfolio-card[data-format="digital"] { border-top: 3px solid var(--blue); }
.portfolio-card[data-format="analog"] { border-top: 3px solid var(--pink); }
.portfolio-card[data-format="intermedia"] { border-top: 3px solid var(--violet); }
.thumb { align-items: center; aspect-ratio: 16 / 10; background: var(--surface-2); border-bottom: 1px solid var(--line); display: flex; justify-content: center; overflow: hidden; }
.thumb img { height: 100%; object-fit: cover; width: 100%; }
.fallback-thumb { color: var(--pink); font-family: "Courier New", ui-monospace, monospace; font-size: 2.3rem; font-weight: 900; }
.portfolio-body { display: flex; flex: 1; flex-direction: column; gap: 12px; padding: 19px; }
.portfolio-body h3 a:hover { color: var(--mint); }
.portfolio-body p { color: var(--muted); display: -webkit-box; line-height: 1.5; margin: 0; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 4; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag { border: 1px solid var(--line); color: var(--muted); font-family: "Courier New", ui-monospace, monospace; font-size: 0.68rem; padding: 5px 7px; text-transform: uppercase; }
.tag-format-digital { border-color: color-mix(in srgb, var(--blue) 60%, var(--line)); color: var(--blue); }
.tag-format-analog { border-color: color-mix(in srgb, var(--pink) 60%, var(--line)); color: var(--pink); }
.tag-format-intermedia { border-color: color-mix(in srgb, var(--violet) 60%, var(--line)); color: var(--violet); }
.tag-recognition { border-color: color-mix(in srgb, var(--gold) 60%, var(--line)); color: var(--gold); }
.tag-playable { border-color: color-mix(in srgb, var(--mint) 60%, var(--line)); color: var(--mint); }
.tag-year { color: var(--quiet); }
.card-links { display: flex; flex-wrap: wrap; gap: 8px; margin-top: auto; padding-top: 4px; }
.card-links a { border-bottom: 1px solid var(--line-strong); color: var(--mint); font-size: 0.82rem; padding-bottom: 3px; }
.card-links a.details-link { color: var(--ink); font-weight: 800; }
.empty { border: 1px solid var(--line); color: var(--muted); grid-column: 1 / -1; padding: 40px; }
.noscript-index { border: 1px solid var(--line); color: var(--muted); padding: 24px; }
.noscript-index a { color: var(--mint); text-decoration: underline; }

.elsewhere-grid { display: grid; gap: 0; grid-template-columns: repeat(3, 1fr); }
.elsewhere-grid a { border: 1px solid var(--line); display: grid; gap: 10px; min-height: 170px; padding: 24px; }
.elsewhere-grid a + a { border-left: 0; }
.elsewhere-grid a:hover { background: var(--surface); }
.elsewhere-grid span { color: var(--gold); font-family: "Courier New", ui-monospace, monospace; font-size: 0.75rem; text-transform: uppercase; }
.elsewhere-grid strong { font-size: 1.4rem; }
.elsewhere-grid small { color: var(--muted); font-size: 0.95rem; }

.footer { align-items: center; display: flex; justify-content: space-between; margin: 0 auto; max-width: var(--max); padding: 34px 28px; }
.footer p { color: var(--quiet); margin: 0; }

.project-nav { max-width: var(--max); }
.project-page { margin: 0 auto; max-width: var(--max); padding: 54px 28px 90px; }
.back-link, .text-link { color: var(--mint); }
.project-hero { align-items: stretch; display: grid; gap: 42px; grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr); margin-top: 38px; }
.project-media { align-items: center; aspect-ratio: 16 / 11; background: var(--surface); border: 1px solid var(--line); display: flex; justify-content: center; overflow: hidden; position: relative; }
.project-media > img, .project-video, .project-video img { height: 100%; object-fit: cover; width: 100%; }
.project-media > b { color: var(--pink); font-family: "Courier New", ui-monospace, monospace; font-size: 5rem; }
.project-poster-index { left: 18px; position: absolute; top: 16px; }
.project-video { display: block; position: relative; }
.project-video span { background: var(--coral); bottom: 18px; color: #160b07; font-weight: 800; left: 18px; padding: 10px 13px; position: absolute; }
.project-video-initials { color: rgba(245, 241, 232, 0.72); font-family: "Courier New", ui-monospace, monospace; font-size: 5rem; left: 50%; position: absolute; top: 50%; transform: translate(-50%, -50%); }
.project-heading { align-self: center; }
.project-heading h1 { font-size: 5.3rem; line-height: 0.92; max-width: 12ch; }
.project-heading h1.project-title-long { font-size: 3.4rem; max-width: 18ch; }
.project-deck { color: var(--muted); font-size: 1.18rem; line-height: 1.6; margin: 24px 0; }
.project-facts { border-bottom: 1px solid var(--line); border-top: 1px solid var(--line); display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 24px 0; }
.project-facts span { color: var(--muted); min-width: 0; padding: 14px 10px 14px 0; }
.project-facts b { color: var(--quiet); display: block; font-family: "Courier New", ui-monospace, monospace; font-size: 0.68rem; margin-bottom: 5px; text-transform: uppercase; }
.project-content { display: grid; gap: 64px; grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.6fr); margin-top: 80px; }
.project-body { font-size: 1.08rem; line-height: 1.75; max-width: 760px; }
.project-body p:first-child { font-size: 1.3rem; }
.project-body a { color: var(--mint); text-decoration: underline; text-underline-offset: 3px; }
.project-body blockquote { border-left: 3px solid var(--gold); color: var(--muted); margin: 32px 0; padding-left: 20px; }
.project-aside { display: grid; gap: 24px; align-content: start; }
.project-aside section { border-top: 1px solid var(--line); padding-top: 18px; }
.project-aside h2 { font-size: 1rem; margin-bottom: 14px; }
.project-aside ul { color: var(--muted); line-height: 1.5; margin: 0; padding-left: 20px; }
.project-aside p { color: var(--muted); line-height: 1.5; margin: 0; }
.project-links { display: grid; gap: 8px; }
.project-link { color: var(--mint); }
.project-sequence { border-top: 1px solid var(--line); display: grid; gap: 28px; grid-template-columns: 1fr 1fr; margin-top: 80px; padding-top: 28px; }
.project-sequence > a:last-child { text-align: right; }
.project-sequence span { color: var(--quiet); display: block; font-family: "Courier New", ui-monospace, monospace; font-size: 0.72rem; margin-bottom: 7px; text-transform: uppercase; }
.project-sequence strong { color: var(--mint); }

.archive-index-page { margin: 0 auto; max-width: var(--max); padding: 58px 28px 90px; }
.archive-index-page header { margin: 54px 0 42px; }
.archive-index-page header h1 { font-size: 5.6rem; max-width: 12ch; }
.archive-index-page header > p:last-child { color: var(--muted); font-size: 1.1rem; }
.archive-index-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); list-style: none; margin: 0; padding: 0; }
.archive-index-list li { border-top: 1px solid var(--line); }
.archive-index-list li:nth-child(odd) { border-right: 1px solid var(--line); }
.archive-index-list a { align-items: baseline; display: grid; gap: 12px; grid-template-columns: 130px minmax(0, 1fr) auto; min-height: 70px; padding: 16px 18px; }
.archive-index-list a:hover { background: var(--surface); }
.archive-index-list span, .archive-index-list small { color: var(--quiet); font-family: "Courier New", ui-monospace, monospace; font-size: 0.72rem; }
.archive-index-list strong { line-height: 1.2; }

@media (max-width: 1000px) {
  h1 { font-size: 6.5rem; }
  .feature-grid, .portfolio-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .archive-utility { grid-template-columns: 1fr 1fr; }
  .facet-groups { grid-template-columns: 1fr 1fr; }
  .facet-groups-more { grid-template-columns: 1fr 1fr; }
  .facet-group:nth-child(2) { border-right: 0; }
  .facet-group:nth-child(-n + 2) { border-bottom: 1px solid var(--line); }
  .facet-groups-more .facet-group:nth-child(2) { border-right: 0; }
  .facet-groups-more .facet-group:last-child { border-right: 1px solid var(--line); }
  .project-heading h1 { font-size: 4.2rem; }
}

@media (max-width: 700px) {
  .nav { align-items: flex-start; flex-direction: column; gap: 13px; padding: 16px 20px; position: relative; }
  .nav-links { width: 100%; }
  .nav-links a { flex: 1; text-align: center; }
  .hero { min-height: 560px; padding: 70px 20px 56px; }
  h1 { font-size: 4rem; }
  h2 { font-size: 2.35rem; }
  .lede { font-size: 1.12rem; }
  .hero-stats { display: grid; gap: 14px; grid-template-columns: repeat(3, 1fr); width: 100%; }
  .hero-stats div { min-width: 0; padding: 0 10px; }
  .hero-stats dt { font-size: 1rem; }
  .hero-stats dd { font-size: 0.78rem; }
  .band { padding: 72px 20px; }
  .section-heading, .archive-heading, .footer { align-items: flex-start; flex-direction: column; }
  .archive-heading-side { justify-items: start; }
  .feature-grid, .portfolio-grid, .elsewhere-grid, .project-hero, .project-content { grid-template-columns: 1fr; }
  .feature-media, .thumb { aspect-ratio: 16 / 9; }
  .archive-utility, .facet-groups { grid-template-columns: 1fr; }
  .facet-group, .facet-group:nth-child(2) { border-bottom: 1px solid var(--line); border-right: 0; }
  .facet-group:last-child { border-bottom: 0; }
  .facet-groups-more .facet-group:last-child { border-right: 0; }
  .quick-routes { align-items: stretch; }
  .quick-routes > span { width: 100%; }
  .quick-routes button { flex: 1 1 calc(50% - 8px); }
  .elsewhere-grid a + a { border-left: 1px solid var(--line); border-top: 0; }
  .project-page { padding: 40px 20px 70px; }
  .project-hero { gap: 28px; }
  .project-heading h1 { font-size: 3.25rem; }
  .project-heading h1.project-title-long { font-size: 2.45rem; max-width: 100%; }
  .project-facts { grid-template-columns: 1fr; }
  .project-facts span + span { border-top: 1px solid var(--line); }
  .project-content { gap: 46px; margin-top: 58px; }
  .project-sequence { grid-template-columns: 1fr; }
  .project-sequence > a:last-child { text-align: left; }
  .archive-index-page { padding: 40px 20px 70px; }
  .archive-index-page header h1 { font-size: 3.3rem; }
  .archive-index-list { grid-template-columns: 1fr; }
  .archive-index-list li:nth-child(odd) { border-right: 0; }
  .archive-index-list a { grid-template-columns: 96px minmax(0, 1fr); }
  .archive-index-list small { grid-column: 2; }
}

@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .feature-card { transition: none; }
}
"""


def build_js() -> str:
    return r"""const entries = Array.isArray(window.JUST404IT_PORTFOLIO) ? window.JUST404IT_PORTFOLIO : [];
const grid = document.querySelector("#portfolio-grid");
const search = document.querySelector("#search");
const summary = document.querySelector("#result-summary");
const sort = document.querySelector("#sort");
const year = document.querySelector("#year");
const reset = document.querySelector("#reset-filters");
const surprise = document.querySelector("#surprise-me");
const activeFilters = document.querySelector("#active-filters");
const activeFilterList = document.querySelector("#active-filter-list");
const facets = [...document.querySelectorAll(".facet")];
const routes = [...document.querySelectorAll("[data-preset]")];
const moreFilters = document.querySelector(".more-filters");
const multiGroups = ["formats", "contexts", "platforms", "recognition", "access", "pace"];
let visibleEntries = [];

const state = {
  status: "all",
  formats: new Set(),
  contexts: new Set(),
  platforms: new Set(),
  recognition: new Set(),
  access: new Set(),
  pace: new Set(),
};

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

function initials(title) {
  return clean(title).split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function intersects(values, selected) {
  return selected.size === 0 || (values || []).some((value) => selected.has(value));
}

function matches(entry, ignoreGroup = "") {
  if (ignoreGroup !== "status" && state.status === "playable" && !entry.playable) return false;
  if (ignoreGroup !== "status" && state.status === "recognized" && !entry.hasAccolade) return false;
  if (ignoreGroup !== "formats" && !intersects(entry.formats, state.formats)) return false;
  if (ignoreGroup !== "contexts" && !intersects(entry.contexts, state.contexts)) return false;
  if (ignoreGroup !== "platforms" && !intersects(entry.platforms, state.platforms)) return false;
  if (ignoreGroup !== "recognition" && !intersects(entry.recognition, state.recognition)) return false;
  if (ignoreGroup !== "access" && !intersects(entry.access, state.access)) return false;
  if (ignoreGroup !== "pace" && state.pace.size && !state.pace.has(entry.developmentPace)) return false;
  if (year.value !== "all" && entry.year !== year.value) return false;

  const query = clean(search.value).trim().toLowerCase();
  if (!query) return true;
  const haystack = [
    entry.title,
    entry.year,
    entry.description,
    ...(entry.categories || []),
    ...(entry.details || []),
    ...(entry.credits || []),
    ...(entry.accolades || []),
    entry.developmentTime,
  ].join(" ").toLowerCase();
  return haystack.includes(query);
}

function seriesValue(entry, fallback) {
  const numbers = entry.gameNumbers || [];
  return numbers.length ? Math.max(...numbers) : fallback;
}

function sortEntries(list) {
  const sorted = [...list];
  const mode = sort.value;
  sorted.sort((a, b) => {
    if (mode === "series-asc") return seriesValue(a, 999) - seriesValue(b, 999) || a.title.localeCompare(b.title);
    if (mode === "newest") return clean(b.year).localeCompare(clean(a.year)) || seriesValue(b, 0) - seriesValue(a, 0);
    if (mode === "oldest") return clean(a.year).localeCompare(clean(b.year)) || seriesValue(a, 999) - seriesValue(b, 999);
    if (mode === "title") return a.title.localeCompare(b.title);
    if (mode === "fastest" || mode === "longest") {
      const aKnown = Number.isFinite(a.developmentDays);
      const bKnown = Number.isFinite(b.developmentDays);
      if (aKnown !== bKnown) return aKnown ? -1 : 1;
      if (aKnown && a.developmentDays !== b.developmentDays) {
        return mode === "fastest" ? a.developmentDays - b.developmentDays : b.developmentDays - a.developmentDays;
      }
      return seriesValue(b, 0) - seriesValue(a, 0);
    }
    return seriesValue(b, 0) - seriesValue(a, 0) || a.title.localeCompare(b.title);
  });
  return sorted;
}

function tag(label, className = "") {
  return `<span class="tag ${className}">${html(label)}</span>`;
}

function categoryTags(entry) {
  const tags = [];
  (entry.categories || []).forEach((category) => {
    if (/^20\d{2}$/.test(category)) return;
    if (category === "Digital") tags.push(tag(category, "tag-format-digital"));
    else if (category === "Analog") tags.push(tag(category, "tag-format-analog"));
    else if (category === "Intermedia Games") tags.push(tag("Intermedia", "tag-format-intermedia"));
    else if (category === "Award Winning" || category === "Exhibited") tags.push(tag(category, "tag-recognition"));
    else if (tags.length < 5) tags.push(tag(category));
  });
  if (entry.playable) tags.push(tag("Playable", "tag-playable"));
  return tags.slice(0, 6).join("");
}

function renderCard(entry) {
  const format = (entry.formats || ["other"])[0] || "other";
  const thumb = entry.image
    ? `<img src="${html(entry.image)}" alt="">`
    : `<span class="fallback-thumb" aria-hidden="true">${html(initials(entry.title))}</span>`;
  const links = (entry.links || []).filter((link) => /play|download|itch|game jolt|newgrounds|rules/i.test(link.label)).slice(0, 2);
  const linkMarkup = links.map((link) => `<a href="${html(link.url)}">${html(link.label)}</a>`).join("");
  return `<article class="portfolio-card" data-format="${html(format)}">
    <div class="thumb">${thumb}</div>
    <div class="portfolio-body">
      <span class="meta">${html(entry.year || "Archive")} · ${html(entry.seriesLabel)}</span>
      <h3><a href="${html(entry.detailPath)}">${html(entry.title)}</a></h3>
      <p>${html(entry.description || "A project from the 100 Games in 5 Years archive.")}</p>
      <div class="tags">${categoryTags(entry)}</div>
      <div class="card-links"><a class="details-link" href="${html(entry.detailPath)}">Project page</a>${linkMarkup}</div>
    </div>
  </article>`;
}

function updateFacetState() {
  facets.forEach((facet) => {
    const group = facet.dataset.group;
    const value = facet.dataset.value;
    const active = group === "status" ? state.status === value : state[group].has(value);
    facet.classList.toggle("is-active", active);
    facet.setAttribute("aria-pressed", String(active));
    const count = entries.filter((entry) => {
      if (!matches(entry, group)) return false;
      if (group === "status") {
        if (value === "all") return true;
        if (value === "playable") return entry.playable;
        return entry.hasAccolade;
      }
      if (group === "pace") return entry.developmentPace === value;
      return (entry[group] || []).includes(value);
    }).length;
    const countNode = facet.querySelector("span");
    if (countNode) countNode.textContent = count;
    facet.disabled = count === 0 && !active;
  });
}

function facetLabel(facet) {
  return [...facet.childNodes].find((node) => node.nodeType === Node.TEXT_NODE)?.textContent.trim() || facet.dataset.value;
}

function activeChip(label, group, value = "") {
  return `<button class="active-filter" type="button" data-remove-group="${html(group)}" data-remove-value="${html(value)}" aria-label="Remove ${html(label)} filter">${html(label)} ×</button>`;
}

function updateActiveFilters() {
  const chips = [];
  if (state.status !== "all") {
    const facet = facets.find((item) => item.dataset.group === "status" && item.dataset.value === state.status);
    chips.push(activeChip(facetLabel(facet), "status", state.status));
  }
  multiGroups.forEach((group) => {
    state[group].forEach((value) => {
      const facet = facets.find((item) => item.dataset.group === group && item.dataset.value === value);
      chips.push(activeChip(facetLabel(facet), group, value));
    });
  });
  if (year.value !== "all") chips.push(activeChip(year.value, "year", year.value));
  const query = clean(search.value).trim();
  if (query) chips.push(activeChip(`Search: ${query}`, "search"));
  activeFilterList.innerHTML = chips.join("");
  activeFilters.hidden = chips.length === 0;
}

function syncUrl() {
  const params = new URLSearchParams();
  const query = clean(search.value).trim();
  if (query) params.set("q", query);
  if (state.status !== "all") params.set("status", state.status);
  multiGroups.forEach((group) => {
    if (state[group].size) params.set(group, [...state[group]].join(","));
  });
  if (year.value !== "all") params.set("year", year.value);
  if (sort.value !== "series-desc") params.set("sort", sort.value);
  const queryString = params.toString();
  history.replaceState(null, "", `${location.pathname}${queryString ? `?${queryString}` : ""}${location.hash}`);
}

function render() {
  visibleEntries = sortEntries(entries.filter((entry) => matches(entry)));
  const representedGames = new Set(visibleEntries.flatMap((entry) => entry.gameNumbers || [])).size;
  const projectWord = visibleEntries.length === 1 ? "project page" : "project pages";
  const gameWord = representedGames === 1 ? "game" : "games";
  summary.innerHTML = `<span>${visibleEntries.length}</span> ${projectWord} · ${representedGames} ${gameWord} represented`;
  grid.innerHTML = visibleEntries.length ? visibleEntries.map(renderCard).join("") : `<p class="empty">Nothing lives at this exact intersection. Yet.</p>`;
  surprise.disabled = visibleEntries.length === 0;
  updateFacetState();
  updateActiveFilters();
  syncUrl();
}

function loadUrlState() {
  const params = new URLSearchParams(location.search);
  search.value = params.get("q") || "";
  state.status = ["all", "playable", "recognized"].includes(params.get("status")) ? params.get("status") : "all";
  multiGroups.forEach((group) => {
    const allowed = new Set(facets.filter((item) => item.dataset.group === group).map((item) => item.dataset.value));
    clean(params.get(group)).split(",").filter((value) => allowed.has(value)).forEach((value) => state[group].add(value));
  });
  if ([...year.options].some((option) => option.value === params.get("year"))) year.value = params.get("year");
  if ([...sort.options].some((option) => option.value === params.get("sort"))) sort.value = params.get("sort");
  if (moreFilters && ["recognition", "access", "pace"].some((group) => state[group].size)) moreFilters.open = true;
}

function clearFilters(resetSort = true) {
  search.value = "";
  if (resetSort) sort.value = "series-desc";
  year.value = "all";
  state.status = "all";
  multiGroups.forEach((group) => state[group].clear());
}

facets.forEach((facet) => {
  facet.addEventListener("click", () => {
    const group = facet.dataset.group;
    const value = facet.dataset.value;
    if (group === "status") state.status = value;
    else if (state[group].has(value)) state[group].delete(value);
    else state[group].add(value);
    render();
  });
});

search.addEventListener("input", render);
sort.addEventListener("change", render);
year.addEventListener("change", render);
reset.addEventListener("click", () => {
  clearFilters();
  render();
});

routes.forEach((route) => {
  route.addEventListener("click", () => {
    clearFilters();
    const preset = route.dataset.preset;
    if (preset === "play-now") {
      state.status = "playable";
      state.access.add("online");
    } else if (preset === "nonsense") state.contexts.add("silly");
    else if (preset === "serious") state.contexts.add("serious");
    else if (preset === "off-screen") {
      state.formats.add("analog");
      state.formats.add("intermedia");
    } else if (preset === "made-fast") state.pace.add("day-or-less");
    else if (preset === "decorated") state.recognition.add("award-winning");
    if (moreFilters && ["made-fast", "decorated"].includes(preset)) moreFilters.open = true;
    render();
  });
});

activeFilterList.addEventListener("click", (event) => {
  const chip = event.target.closest("[data-remove-group]");
  if (!chip) return;
  const group = chip.dataset.removeGroup;
  const value = chip.dataset.removeValue;
  if (group === "status") state.status = "all";
  else if (group === "year") year.value = "all";
  else if (group === "search") search.value = "";
  else if (state[group]) state[group].delete(value);
  render();
});

surprise.addEventListener("click", () => {
  if (!visibleEntries.length) return;
  const random = new Uint32Array(1);
  crypto.getRandomValues(random);
  const entry = visibleEntries[random[0] % visibleEntries.length];
  location.href = entry.detailPath;
});

loadUrlState();
render();
"""


def build_readme(entries: list[dict]) -> str:
    with_images = sum(1 for entry in entries if entry["image"])
    represented_games = len({number for entry in entries for number in entry["gameNumbers"]})
    return f"""# JUST404IT Static Site

This is the new static site for `just404it.com`, generated from the public safety backup of `justdeleteit.com`.

## What Is Here

- `index.html` - the hub plus searchable, sortable, faceted archive.
- `assets/site.css` and `assets/site.js` - the editable front-end.
- `data/portfolio.json` and `data/portfolio.js` - {len(entries)} public project pages representing {represented_games} games.
- `games/` - locally generated detail pages for every public project entry.
- `assets/portfolio/` - {with_images} copied portfolio images from the backup.
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
$env:JUSTDELETEIT_BACKUP_ROOT = 'C:\\path\\to\\the\\extracted-backup'
$env:JUST404IT_SITE_URL = 'https://just404it.github.io/just404it-site'
py -3.12 tools\\build_static_site.py
```

## Validate Before Publishing

```powershell
py -3.12 tools\\validate_site.py
```
"""


def build_404_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>404 - JUST404IT</title>
  <link rel="icon" type="image/png" href="assets/favicon.png">
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
    write_text(SITE_ROOT / "archive" / "index.html", build_archive_html(entries))
    for index, entry in enumerate(entries):
        newer = entries[index - 1] if index > 0 else None
        earlier = entries[index + 1] if index + 1 < len(entries) else None
        write_text(SITE_ROOT / entry["detailPath"] / "index.html", build_game_html(entry, newer, earlier))
    write_text(SITE_ROOT / "404.html", build_404_html())
    write_text(SITE_ROOT / "sitemap.xml", build_sitemap(entries))
    write_text(SITE_ROOT / "robots.txt", build_robots())
    write_text(SITE_ROOT / "assets" / "site.css", build_css())
    write_text(SITE_ROOT / "assets" / "site.js", build_js())
    favicon_source = MIRROR_ROOT / "wp-content" / "uploads" / "2016" / "03" / "114.png"
    if favicon_source.is_file():
        shutil.copy2(favicon_source, SITE_ROOT / "assets" / "favicon.png")
    write_text(SITE_ROOT / "README.md", build_readme(entries))
    print(f"Generated {len(entries)} portfolio entries in {SITE_ROOT}")


if __name__ == "__main__":
    main()
