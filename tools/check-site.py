#!/usr/bin/env python3
"""Check generated routes, fragments, migrated content and private reference assets."""
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE = re.search(r"^url:\s*(\S+)", (ROOT / "_config.yml").read_text(), re.M)[1]


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicate_ids = set()
        self.references = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                self.duplicate_ids.add(attrs["id"])
            self.ids.add(attrs["id"])
        for name in ("href", "src"):
            if attrs.get(name):
                self.references.append(attrs[name])


def target_file(path):
    target = PUBLIC / unquote(path).lstrip("/")
    if target.is_dir():
        target = target / "index.html"
    return target


def main():
    if not (PUBLIC / "index.html").exists():
        raise SystemExit("Build the site first: npm run build")
    pages = {path: Page(path.read_text()) for path in PUBLIC.rglob("*.html")}
    errors = []
    checked = 0
    for path, page in pages.items():
        relative = path.relative_to(PUBLIC).as_posix()
        for identifier in page.duplicate_ids:
            errors.append(f"{relative}: duplicate id {identifier}")
        base = SITE.rstrip("/") + "/" + relative
        for reference in page.references:
            url = urlsplit(urljoin(base, reference))
            if url.scheme not in ("http", "https") or url.netloc != urlsplit(SITE).netloc:
                continue
            checked += 1
            target = target_file(url.path)
            if not target.is_file():
                errors.append(f"{relative}: missing {reference}")
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f"{relative}: missing fragment {reference}")

    search = json.loads((PUBLIC / "search.json").read_text())
    search_paths = {urlsplit(post["url"]).path.rstrip("/") for post in search}
    report = json.loads((ROOT / "migration/report.json").read_text())
    migrated = list((ROOT / "source/_posts").glob("cnblogs-*.md"))
    for post in migrated:
        if f"/posts/{post.stem}" not in search_paths:
            errors.append(f"Missing migrated post in search: {post.stem}")
    for post in search:
        if not target_file(urlsplit(post["url"]).path).is_file():
            errors.append(f"Search has missing post: {post['url']}")
    if not report.get("rendered_validation", {}).get("status") == "passed":
        errors.append("Migration rendering validation is not marked passed")

    namespace = {"a": "http://www.w3.org/2005/Atom"}
    feed = ElementTree.parse(PUBLIC / "atom.xml")
    entries = feed.findall("a:entry", namespace)
    for entry in entries:
        content = entry.find("a:content", namespace)
        if content is None or content.get("type") != "html":
            errors.append("Atom entry must explicitly declare HTML content")
    ElementTree.parse(PUBLIC / "sitemap.xml")

    reference_hashes = {hashlib.sha256(path.read_bytes()).digest() for path in ROOT.glob("*.png")}
    for asset in PUBLIC.rglob("*"):
        if asset.is_file() and asset.suffix.lower() == ".png":
            if hashlib.sha256(asset.read_bytes()).digest() in reference_hashes:
                errors.append(f"Reference PNG published: {asset.relative_to(PUBLIC)}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: {len(pages)} pages, {checked} local references, {len(search)} searchable posts, "
          f"{len(migrated)} migrated posts, {len(entries)} Atom entries; no reference PNG published.")


if __name__ == "__main__":
    main()
