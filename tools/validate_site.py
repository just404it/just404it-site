from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup


SITE_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKERS = (
    "C:\\Users\\just4",
    "Dropbox\\James_Archive",
    "just404it@gmail.com",
)
BRAND_FILES = (
    "assets/brand/just404it-wordmark.svg",
    "assets/brand/just404it-icon.svg",
    "assets/brand/just404it-icon-512.png",
    "assets/brand/just404it-social-card.png",
    "assets/favicon.png",
)


def check_public_data() -> tuple[int, int]:
    entries = json.loads((SITE_ROOT / "data" / "portfolio.json").read_text(encoding="utf-8"))
    represented = {number for entry in entries for number in entry.get("gameNumbers", [])}
    if represented != set(range(1, 101)):
        missing = sorted(set(range(1, 101)) - represented)
        raise SystemExit(f"Archive does not represent games 1-100. Missing: {missing}")
    for entry in entries:
        detail = SITE_ROOT / entry["detailPath"] / "index.html"
        if not detail.is_file():
            raise SystemExit(f"Missing detail page: {detail}")
        image = entry.get("image")
        if image and not (SITE_ROOT / image).is_file():
            raise SystemExit(f"Missing portfolio image: {image}")
        if not set(entry.get("access", [])).issubset({"online", "download", "watch", "rules"}):
            raise SystemExit(f"Unknown access label: {entry['slug']}")
        if entry.get("developmentPace") not in {"", "day-or-less", "days", "weeks", "months-plus"}:
            raise SystemExit(f"Unknown development pace: {entry['slug']}")
    return len(entries), len(represented)


def check_local_references() -> tuple[int, int]:
    pages = [path for path in SITE_ROOT.rglob("*.html") if ".git" not in path.parts and "qa" not in path.parts]
    checked = 0
    for page in pages:
        soup = BeautifulSoup(page.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        for tag_name, attribute in (("a", "href"), ("img", "src"), ("script", "src"), ("link", "href")):
            for node in soup.find_all(tag_name):
                value = (node.get(attribute) or "").strip()
                if not value or value.startswith(("#", "mailto:", "tel:", "data:")):
                    continue
                parsed = urlparse(value)
                if parsed.scheme or parsed.netloc:
                    continue
                checked += 1
                target = (page.parent / unquote(parsed.path)).resolve()
                if parsed.path.endswith("/") or (not target.suffix and not target.exists()):
                    target /= "index.html"
                if SITE_ROOT != target and SITE_ROOT not in target.parents:
                    raise SystemExit(f"Reference escapes site root: {page} -> {value}")
                if not target.exists():
                    raise SystemExit(f"Missing local reference: {page} -> {value}")
    return len(pages), checked


def check_private_markers() -> None:
    extensions = {".html", ".css", ".js", ".json", ".md", ".py", ".xml", ".txt"}
    for path in SITE_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if ".git" in path.parts or "qa" in path.parts or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in PRIVATE_MARKERS:
            if marker.lower() in text.lower():
                raise SystemExit(f"Private marker in public file: {path} ({marker})")


def check_brand_assets() -> None:
    for relative in BRAND_FILES:
        path = SITE_ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"Missing brand asset: {relative}")
        if path.suffix == ".svg":
            ElementTree.fromstring(path.read_text(encoding="utf-8"))


def check_search_artifacts(entries: int) -> tuple[int, int]:
    sitemap = SITE_ROOT / "sitemap.xml"
    robots = SITE_ROOT / "robots.txt"
    if not sitemap.is_file() or not robots.is_file():
        raise SystemExit("Missing sitemap.xml or robots.txt")
    root = ElementTree.fromstring(sitemap.read_text(encoding="utf-8"))
    locations = [node.text for node in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    expected = entries + 2
    if len(locations) != expected or len(set(locations)) != expected:
        raise SystemExit(f"Sitemap expected {expected} unique URLs, found {len(set(locations))}")
    if not all(value and value.startswith("https://") for value in locations):
        raise SystemExit("Sitemap contains a non-absolute URL")
    if locations[0].rstrip("/") not in robots.read_text(encoding="utf-8"):
        raise SystemExit("robots.txt sitemap host does not match the generated site host")

    indexable = [SITE_ROOT / "index.html", SITE_ROOT / "archive" / "index.html"]
    indexable.extend(SITE_ROOT.glob("games/*/index.html"))
    structured = 0
    canonical_urls: set[str] = set()
    descriptions: set[str] = set()
    for page in indexable:
        soup = BeautifulSoup(page.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        canonicals = soup.select('link[rel="canonical"]')
        if len(canonicals) != 1 or not canonicals[0].get("href", "").startswith("https://"):
            raise SystemExit(f"Missing absolute canonical URL: {page}")
        canonical = canonicals[0]["href"]
        if canonical in canonical_urls:
            raise SystemExit(f"Duplicate canonical URL: {canonical}")
        canonical_urls.add(canonical)
        description = soup.select_one('meta[name="description"]')
        description_value = (description.get("content") if description else "").strip()
        if not description_value or description_value in descriptions:
            raise SystemExit(f"Missing or duplicate meta description: {page}")
        if "games" in page.parts and not 50 <= len(description_value) <= 160:
            raise SystemExit(f"Project meta description outside 50-160 characters: {page}")
        descriptions.add(description_value)
        scripts = soup.select('script[type="application/ld+json"]')
        if not scripts:
            raise SystemExit(f"Missing structured data: {page}")
        for script in scripts:
            json.loads(script.string or script.get_text())
            structured += 1
    return len(locations), structured


def main() -> None:
    entries, games = check_public_data()
    pages, references = check_local_references()
    check_private_markers()
    check_brand_assets()
    sitemap_urls, structured = check_search_artifacts(entries)
    print(
        f"Validated {entries} project pages representing {games} games; {pages} HTML files, "
        f"{references} local references, {sitemap_urls} sitemap URLs, and {structured} structured-data blocks."
    )


if __name__ == "__main__":
    main()
