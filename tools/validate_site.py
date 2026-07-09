from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup


SITE_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKERS = (
    "C:\\Users\\just4",
    "Dropbox\\James_Archive",
    "just404it@gmail.com",
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
    extensions = {".html", ".css", ".js", ".json", ".md", ".py"}
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


def main() -> None:
    entries, games = check_public_data()
    pages, references = check_local_references()
    check_private_markers()
    print(f"Validated {entries} project pages representing {games} games; {pages} HTML files and {references} local references.")


if __name__ == "__main__":
    main()
