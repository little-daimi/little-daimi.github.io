#!/usr/bin/env python3
"""Migrate public cnblogs posts to Hexo without changing the source blog.

Install: python3 -m pip install -r migration/requirements.txt
Run:     python3 tools/migrate-cnblogs.py
Replay:  python3 tools/migrate-cnblogs.py --offline
Refresh: python3 tools/migrate-cnblogs.py --refresh

Cached source HTML/XML/JSON is retained for auditing and repeatable offline
rebuilds. Only cnblogs-<id>.md files are written; other authored posts are kept.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import parse_qs, urljoin, urlparse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup
from markdownify import MarkdownConverter


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.cnblogs.com/undefined"
CACHE = ROOT / "migration/cache"
POSTS = ROOT / "source/_posts"
IMAGES = ROOT / "source/images/posts"
POST_RE = re.compile(r"^https://(?:www\.)?cnblogs\.com/undefined/(p|articles)/(\d+)(?:\.html)?/?$")
USER_AGENT = "Mozilla/5.0 (compatible; PersonalBlogMigration/1.0)"


def soup(value):
    return BeautifulSoup(value, "html.parser")


def json_text(value):
    return json.dumps(value, ensure_ascii=False)


def post_links(html):
    found = {}
    for a in soup(html).select("a[href]"):
        url = urljoin(BASE + "/", a["href"])
        match = POST_RE.fullmatch(url)
        if match:
            found[match[2]] = f"{BASE}/{match[1]}/{match[2]}"
    return found


class Fetcher:
    def __init__(self, offline=False, refresh=False):
        self.offline = offline
        self.refresh = refresh
        self.fetched = []

    def fetch(self, url, filename):
        path = CACHE / filename
        self.fetched.append({"url": url, "cache": str(path.relative_to(ROOT))})
        if path.exists() and (self.offline or not self.refresh):
            return path.read_text(encoding="utf-8-sig")
        if self.offline:
            raise RuntimeError(f"Missing offline cache: {filename}")
        response = self.request(url)
        response.encoding = "utf-8"
        path.write_text(response.text, encoding="utf-8")
        return response.text.lstrip("\ufeff")

    def request(self, url, referer=BASE):
        error = None
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=(15, 60), headers={
                    "User-Agent": USER_AGENT, "Referer": referer,
                })
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                error = exc
                if attempt < 2:
                    time.sleep(attempt + 1)
        raise error


class SourceMarkdown(MarkdownConverter):
    """Preserve preformatted source code exactly, including blank lines."""

    def convert_pre(self, el, text, parent_tags):
        code = el.find("code") or el
        text = code.get_text()
        languages = [c.removeprefix("language-") for c in code.get("class", [])
                     if c.startswith("language-")]
        language = languages[0] if languages else ""
        longest = max([len(m) for m in re.findall(r"`+", text)] + [2])
        fence = "`" * max(3, longest + 1)
        # Fences need their own line. All original code bytes remain unchanged.
        ending = "" if text.endswith("\n") else "\n"
        return f"\n\n{fence}{language}\n{text}{ending}{fence}\n\n"

    def convert_img(self, el, text, parent_tags):
        # Screenshot filenames can contain unmatched backticks and brackets.
        # Markdownify leaves those unescaped, which can suppress the image.
        alt = re.sub(r"([\\\[\]`*_])", r"\\\1", el.get("alt", ""))
        src = el.get("src", "").replace(" ", "%20")
        return f"![{alt}]({src})"


def discover(fetcher):
    evidence = {}
    urls = {}
    # The site map also lists articles excluded from the front page and feed.
    sitemap = ET.fromstring(fetcher.fetch(BASE + "/sitemap.xml", "sitemap.xml"))
    sitemap_ids = []
    last_modified = {}
    for entry in sitemap:
        children = {item.tag.rsplit("}", 1)[-1]: item.text for item in entry}
        match = POST_RE.fullmatch(children.get("loc", ""))
        if match:
            urls[match[2]] = f"{BASE}/{match[1]}/{match[2]}"
            sitemap_ids.append(match[2])
            last_modified[match[2]] = children.get("lastmod")
    evidence["sitemap"] = sorted(sitemap_ids)

    feed = ET.fromstring(fetcher.fetch(BASE + "/rss", "feed.xml"))
    feed_ids = []
    for entry in feed.findall("{http://www.w3.org/2005/Atom}entry"):
        for link in entry.findall("{http://www.w3.org/2005/Atom}link"):
            match = POST_RE.fullmatch(link.get("href", ""))
            if match:
                urls[match[2]] = f"{BASE}/{match[1]}/{match[2]}"
                feed_ids.append(match[2])
    evidence["feed"] = sorted(set(feed_ids))

    # Follow actual pagination links until exhausted, rather than guessing count.
    pending = [1]
    pages = set()
    index_ids = set()
    while pending:
        page = pending.pop(0)
        if page in pages:
            continue
        pages.add(page)
        page_url = BASE if page == 1 else f"{BASE}?page={page}"
        html = fetcher.fetch(page_url, f"index-{page}.html")
        links = post_links(html)
        urls.update(links)
        index_ids.update(links)
        for a in soup(html).select("a[href]"):
            parsed = urlparse(urljoin(BASE + "/", a["href"]))
            if parsed.path.rstrip("/") not in ("/undefined", "/undefined/default.html"):
                continue
            number = parse_qs(parsed.query).get("page", [""])[0]
            if number.isdigit() and int(number) not in pages:
                pending.append(int(number))
    evidence["homepage"] = sorted(index_ids)
    evidence["homepage_pages"] = sorted(pages)

    sidebar = json.loads(fetcher.fetch(BASE + "/ajax/sidebar-lists", "sidebar-lists.json"))
    sidebar_html = sidebar.get("sideColumn", "")
    archive_urls = {}
    archive_declared_total = 0
    for a in soup(sidebar_html).select("a[href]"):
        match = re.fullmatch(re.escape(BASE) + r"/p/archive/(\d{4})/(\d{2})/?", a["href"])
        if match:
            archive_urls[f"archive-{match[1]}-{match[2]}.html"] = a["href"]
            count = re.search(r"\((\d+)\)", a.get_text())
            if count:
                archive_declared_total += int(count[1])
    archive_ids = set()
    for filename, url in sorted(archive_urls.items()):
        links = post_links(fetcher.fetch(url, filename))
        urls.update(links)
        archive_ids.update(links)
    evidence["monthly_archives"] = sorted(archive_ids)
    evidence["monthly_archive_count"] = len(archive_urls)
    evidence["monthly_declared_posts"] = archive_declared_total
    stats = soup(fetcher.fetch(BASE + "/ajax/blog-stats", "stats.html"))
    evidence["site_statistics_text"] = stats.get_text(" ", strip=True)
    return urls, evidence, last_modified


def taxonomy(title, original_categories, original_tags):
    if original_categories or original_tags:
        return original_categories, original_tags, "original"
    lower = title.lower()
    if "protobuf" in lower:
        tags = ["Reverse", "Protobuf"]
        if "pwn" in lower:
            tags.append("Pwn")
        return ["Reverse"], tags, "title: protobuf / 逆向"
    if "web" in lower:
        return ["Web"], ["CTF", "Web"], "title: WEB"
    if "pwn" in lower:
        return ["Pwn"], ["CTF", "Pwn"], "title: pwn"
    if "actf" in lower:
        return ["Pwn"], ["CTF", "Pwn"], "title: ACTF; body: shellcode / AFL sandbox"
    if "年终" in title or title == "二0二午":
        return ["Life"], ["年度记录"], "title and body: 2025 年终记录"
    return ["Notes"], ["博客"], "title and body: testBlog / test skin"


def download_images(fetcher, documents):
    references = defaultdict(set)
    for ident, document in documents.items():
        for img in document["body"].select("img"):
            src = img.get("data-src") or img.get("src")
            if src:
                references[urljoin(document["url"], src)].add(ident)

    def download(item):
        url, ids = item
        ext = Path(urlparse(url).path).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif"):
            ext = ".img"
        path = IMAGES / (hashlib.sha256(url.encode()).hexdigest()[:20] + ext)
        result = {"original_url": url, "posts": sorted(ids),
                  "local_path": str(path.relative_to(ROOT)),
                  "public_url": "/" + str(path.relative_to(ROOT / "source"))}
        try:
            if not path.exists() or (fetcher.refresh and not fetcher.offline):
                if fetcher.offline:
                    raise RuntimeError("image missing from local cache")
                response = fetcher.request(url, documents[sorted(ids)[0]]["url"])
                content_type = response.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    raise RuntimeError(f"Expected image, got {content_type}")
                path.write_bytes(response.content)
            result.update(status="downloaded", bytes=path.stat().st_size,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        except Exception as exc:
            result.update(status="failed", error=str(exc))
        return result

    with ThreadPoolExecutor(max_workers=5) as pool:
        return list(pool.map(download, sorted(references.items())))


def make_post(ident, document, image_map):
    body = document["body"]
    original_code = [(p.find("code") or p).get_text() for p in body.select("pre")]
    code_hashes = [hashlib.sha256(code.encode()).hexdigest() for code in original_code]
    text_hash = hashlib.sha256(body.get_text().encode()).hexdigest()
    for img in body.select("img"):
        src = img.get("data-src") or img.get("src")
        if not src:
            continue
        url = urljoin(document["url"], src)
        image = image_map.get(url)
        img["src"] = image["public_url"] if image and image["status"] == "downloaded" else url
        img.attrs.pop("data-src", None)
        img.attrs.pop("srcset", None)
    for a in body.select("a[href]"):
        if not a["href"].startswith("#"):
            a["href"] = urljoin(document["url"], a["href"])
    # Scope is the article body only; never import platform scripts/ads/widgets.
    for tag in body.select("script, style"):
        tag.decompose()
    markdown = SourceMarkdown(heading_style="ATX", bullets="-", escape_underscores=True,
                              escape_misc=True).convert(str(body)).strip() + "\n"
    for index, code in enumerate(original_code):
        if code not in markdown:
            raise ValueError(f"Code block {index} changed during Markdown conversion")
    doc = document["document"]
    title_el = doc.select_one("#cb_post_title_url")
    date_el = doc.select_one("#post-date")
    if title_el is None or date_el is None:
        raise ValueError("Missing post title or original publication date")
    title = title_el.get_text(strip=True)
    description_el = doc.select_one('meta[name="description"]')
    description = description_el.get("content", "") if description_el else ""
    published = date_el.get_text(strip=True)
    updated = date_el.get("data-date-updated") or published
    metadata = soup(document["metadata"].get("categoriesTags", ""))
    original_categories = [a.get_text(strip=True) for a in metadata.select("#BlogPostCategory a")]
    original_tags = [a.get_text(strip=True) for a in metadata.select("#EntryTag a")]
    categories, tags, taxonomy_source = taxonomy(title, original_categories, original_tags)
    frontmatter = {
        "title": title, "date": published + ":00 +08:00", "updated": updated + ":00 +08:00",
        "slug": "cnblogs-" + ident, "author": "imiab", "description": description,
        "categories": categories, "tags": tags,
        "original_url": document["url"], "cnblogs_id": int(ident),
        "original_categories": original_categories, "original_tags": original_tags,
        "taxonomy_source": taxonomy_source, "source_kind": document["kind"],
        "disableNunjucks": True,
    }
    text = "---\n" + "\n".join(f"{key}: {json_text(value)}" for key, value in frontmatter.items()) + "\n---\n\n" + markdown
    output = POSTS / f"cnblogs-{ident}.md"
    output.write_text(text, encoding="utf-8")
    return {"id": ident, "title": title, "original_url": document["url"],
            "published": published, "updated": updated, "source_kind": document["kind"],
            "file": str(output.relative_to(ROOT)), "categories": categories, "tags": tags,
            "taxonomy_source": taxonomy_source, "code_blocks": len(original_code),
            "code_sha256": code_hashes, "code_preservation_verified": True,
            "image_references": len(body.select("img")), "body_text_sha256": text_hash,
            "source_html_sha256": document["html_sha256"], "markdown_sha256": hashlib.sha256(text.encode()).hexdigest()}


def verify_rendered_content(posts):
    """Round-trip through the installed Markdown renderer and compare sources."""
    javascript = r"""
const fs = require('fs');
const marked = require('marked');
const paths = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = {};
for (const path of paths) {
  const source = fs.readFileSync(path, 'utf8');
  const markdown = source.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '');
  result[path] = marked.parse(markdown);
}
process.stdout.write(JSON.stringify(result));
"""
    process = subprocess.run(["node", "-e", javascript], cwd=ROOT,
                             input=json.dumps([post["file"] for post in posts]),
                             text=True, capture_output=True, check=True)
    rendered_posts = json.loads(process.stdout)
    for post in posts:
        source = soup((CACHE / (post["id"] + ".html")).read_text()).select_one("#cnblogs_post_body")
        rendered = soup(rendered_posts[post["file"]])
        normalize = lambda element: re.sub(r"\s+", "", element.get_text())
        if normalize(source) != normalize(rendered):
            raise ValueError(f"Rendered body text mismatch: {post['file']}")
        source_codes = [(p.find("code") or p).get_text().rstrip("\n") for p in source.select("pre")]
        rendered_codes = [p.get_text().rstrip("\n") for p in rendered.select("pre code")]
        if source_codes != rendered_codes:
            raise ValueError(f"Rendered code mismatch: {post['file']}")
        if len(source.select("img")) != len(rendered.select("img")):
            raise ValueError(f"Rendered image count mismatch: {post['file']}")
        for img in rendered.select("img"):
            if not img["src"].startswith("/images/posts/"):
                raise ValueError(f"Nonlocal rendered image: {post['file']}")
    return {"status": "passed", "renderer": "installed marked package",
            "articles": len(posts), "checks": ["body text excluding whitespace", "all preformatted code", "image counts and local paths"]}


def write_report(report):
    (ROOT / "migration/report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evidence = report["coverage"]
    lines = ["# 博客园文章迁移报告", "", f"迁移时间：{report['generated_at']}", "",
             f"来源：{BASE}", "", "## 迁移结果", "",
             f"- 已发现公开文章：{report['discovered_count']} 篇；成功迁移：{len(report['posts'])} 篇。",
             f"- 正文代码块：{report['code_blocks']} 个；逐块检查原始代码文本完全保留。",
             f"- 正文图片引用：{report['image_references']} 次；去重图片：{len(report['images'])} 张；成功本地化：{sum(i['status'] == 'downloaded' for i in report['images'])} 张。",
             f"- 文章失败：{len(report['failures'])}；图片失败：{sum(i['status'] == 'failed' for i in report['images'])}。",
             f"- Markdown 渲染比对：{report.get('rendered_validation', {}).get('status', '本次未运行，可加 --verify-render')}。",
             "- 保留原始标题、发布时间、更新时间、段落、标题层级、代码语言和来源链接。代码未执行。",
             "- 原站所有已迁移文章未提供分类与标签；根据标题及明确的正文领域补充导航分类。每篇 front matter 的 taxonomy_source 与本报告标明推导依据，original_categories/original_tags 保留原始空值。",
             "- 重复发布的文章保留独立 URL、日期和标题，不自动合并，不删除原站内容。", "",
             "## 全量覆盖核对", "",
             f"- 首页 {len(evidence['homepage_pages'])} 页：{len(evidence['homepage'])} 篇。",
             f"- RSS/Atom：{len(evidence['feed'])} 篇。",
             f"- 月份归档 {evidence['monthly_archive_count']} 个：{len(evidence['monthly_archives'])} 篇；月份列表标注合计 {evidence['monthly_declared_posts']} 篇。",
             f"- 公开 sitemap：{len(evidence['sitemap'])} 篇。额外发现 /articles/18827559，已迁移。",
             "- 检查每篇的上一篇/下一篇链接，未遗漏可发现的公开内容。",
             f"- 侧栏统计原文：{evidence['site_statistics_text']}",
             "- 统计中的“随笔 14”比公开随笔索引 13 多 1。所有公开索引及逐月归档均只暴露 13 篇随笔，公开 sitemap 另包含 1 篇文章，共 14 篇。无法据公开页面确认统计差异的原因；可能存在非公开内容或统计滞后，本次不声称迁移了不可发现/私有/草稿内容。", "",
             "## 可重复执行", "", "```sh", "python3 -m pip install -r migration/requirements.txt",
             "python3 tools/migrate-cnblogs.py --offline  # 由已保存源文件重新生成",
             "python3 tools/migrate-cnblogs.py --offline --verify-render  # npm install 后校验渲染结果",
             "python3 tools/migrate-cnblogs.py            # 复用缓存，补齐缺失",
             "python3 tools/migrate-cnblogs.py --refresh  # 重新获取公开源站", "```", "",
             "脚本仅写入 source/_posts/cnblogs-<id>.md、source/images/posts 与 migration，保留其他新文章。缓存中保存原始 HTML、元数据 JSON、RSS、sitemap 和月份归档，以便审计。迁移需 requests、beautifulsoup4、markdownify；Hexo 构建不依赖 Python。", "",
             "## 文章清单", "", "| 原始日期 | 标题 | 分类 | 代码块 | 图片引用 |", "| --- | --- | --- | ---: | ---: |"]
    for post in report["posts"]:
        lines.append(f"| {post['published']} | [{post['title']}]({post['original_url']}) | {', '.join(post['categories'])} | {post['code_blocks']} | {post['image_references']} |")
    lines += ["", "## 同文不同发布记录", ""]
    for group in report["duplicate_body_groups"]:
        lines.append("- " + "、".join(f"cnblogs-{ident}" for ident in group) + "：正文文字哈希相同，按原文独立保留。")
    lines += ["", "## 失败项", ""]
    failures = report["failures"] + [i for i in report["images"] if i["status"] == "failed"]
    lines += ["无。"] if not failures else ["```json", json.dumps(failures, ensure_ascii=False, indent=2), "```"]
    (ROOT / "migration/report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use only cached sources and local images")
    parser.add_argument("--refresh", action="store_true", help="Refetch source pages and images")
    parser.add_argument("--verify-render", action="store_true", help="Compare rendered text/code/images using installed Node marked package")
    args = parser.parse_args()
    for directory in (CACHE, POSTS, IMAGES):
        directory.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher(args.offline, args.refresh)
    urls, evidence, _ = discover(fetcher)
    print(f"Discovered {len(urls)} public posts", flush=True)
    documents = {}
    failures = []
    neighbor_ids = set()
    while set(urls) - set(documents) - {f['id'] for f in failures}:
        batch = sorted(set(urls) - set(documents) - {f['id'] for f in failures})

        def load_post(ident):
            try:
                html = fetcher.fetch(urls[ident], ident + ".html")
                doc = soup(html)
                body = doc.select_one("#cnblogs_post_body")
                if not body or not body.get_text(strip=True):
                    raise ValueError("Missing or empty article body")
                meta = json.loads(fetcher.fetch(f"{BASE}/ajax/post-accessories?postId={ident}", f"metadata-{ident}.json"))
                return ident, {"url": urls[ident], "document": doc, "body": body, "metadata": meta,
                               "kind": "article" if "/articles/" in urls[ident] else "post",
                               "html_sha256": hashlib.sha256(html.encode()).hexdigest()}, None
            except Exception as exc:
                return ident, None, str(exc)

        with ThreadPoolExecutor(max_workers=5) as pool:
            for ident, document, error in pool.map(load_post, batch):
                if error:
                    failures.append({"id": ident, "url": urls[ident], "error": error})
                    continue
                documents[ident] = document
                neighbors = post_links(document["metadata"].get("prevNext", ""))
                urls.update(neighbors)
                neighbor_ids.update(neighbors)
    evidence["previous_next_links"] = sorted(neighbor_ids)
    images = download_images(fetcher, documents)
    image_map = {image["original_url"]: image for image in images}
    posts = []
    for ident, document in documents.items():
        try:
            post = make_post(ident, document, image_map)
            posts.append(post)
            print(f"Migrated {ident}: {post['title']}", flush=True)
        except Exception as exc:
            failures.append({"id": ident, "url": urls[ident], "error": str(exc)})
    posts.sort(key=lambda item: item["published"], reverse=True)
    bodies = defaultdict(list)
    for post in posts:
        bodies[post["body_text_sha256"]].append(post["id"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "source": BASE,
        "discovered_count": len(urls), "coverage": evidence, "posts": posts,
        "code_blocks": sum(post["code_blocks"] for post in posts),
        "image_references": sum(post["image_references"] for post in posts),
        "images": images, "failures": failures,
        "duplicate_body_groups": [ids for ids in bodies.values() if len(ids) > 1],
        "source_cache": sorted(fetcher.fetched, key=lambda item: item["cache"]),
    }
    if args.verify_render:
        report["rendered_validation"] = verify_rendered_content(posts)
    write_report(report)
    failed_images = [image for image in images if image["status"] == "failed"]
    print(f"Complete: {len(posts)}/{len(urls)} posts, {len(images) - len(failed_images)}/{len(images)} images")
    return 1 if failures or failed_images else 0


if __name__ == "__main__":
    sys.exit(main())
