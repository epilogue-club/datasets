#!/usr/bin/env python3
"""Import authors from Suntrap, enriching them with Wikimedia data.

Only records with a resolved Wikipedia page, a biography, a representative
Wikimedia Commons image, and an image licence allowed by the author schema are
written. Existing records are left untouched unless --overwrite-existing is
passed.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORS_PATH = REPOSITORY_ROOT / "authors" / "authors.json"
DEFAULT_SCHEMA_PATH = REPOSITORY_ROOT / "schema" / "author.schema.json"
DEFAULT_SOURCE = "http://www.suntrap.ca/library/authors.csv"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA_TEXT_LICENSE = "CC BY-SA 4.0"
USER_AGENT = (
    "epilogue-datasets author importer/1.0 "
    "(https://github.com/epilogue-club/datasets)"
)
MAX_BIO_LENGTH = 512
API_BATCH_SIZE = 20

# Wikimedia's API sometimes uses a shorter label than our schema does.
LICENSE_ALIASES = {"CC0": "CC0 1.0"}


@dataclass(frozen=True)
class SourceAuthor:
    name: str
    wikipedia_url: str | None


@dataclass(frozen=True)
class WikipediaPage:
    title: str
    canonical_url: str
    extract: str
    image_title: str


@dataclass(frozen=True)
class CommonsImage:
    source_url: str
    license: str


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.casefold() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.urls.append(html.unescape(href))


def batched(values: list[str], size: int = API_BATCH_SIZE) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def read_source(source: str, timeout: float) -> str:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        request = Request(source, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8-sig")
    return Path(source).read_text(encoding="utf-8-sig")


def wikipedia_url(link_markup: str) -> str | None:
    parser = LinkParser()
    parser.feed(link_markup)
    for url in parser.urls:
        parsed = urlparse(url)
        if (
            parsed.scheme in {"http", "https"}
            and parsed.hostname is not None
            and parsed.hostname.endswith(".wikipedia.org")
            and parsed.path.startswith("/wiki/")
        ):
            return url
    return None


def parse_source(csv_text: str) -> list[SourceAuthor]:
    rows = csv.DictReader(io.StringIO(csv_text))
    required = {"NAME", "LINK"}
    if rows.fieldnames is None or not required.issubset(rows.fieldnames):
        raise ValueError("Suntrap CSV must contain NAME and LINK columns")

    authors: list[SourceAuthor] = []
    for row in rows:
        name = (row.get("NAME") or "").strip()
        if name:
            authors.append(
                SourceAuthor(
                    name=name,
                    wikipedia_url=wikipedia_url(row.get("LINK") or ""),
                )
            )
    return authors


def guessed_wikipedia_title(name: str) -> str:
    """Turn Suntrap's usually surname-first name into a likely page title."""
    without_alias = re.sub(r"\s*[\[(].*?[\])]", "", name).strip()
    parts = [part.strip() for part in without_alias.split(",")]
    if len(parts) >= 2 and parts[0] and parts[1]:
        # Extra comma-separated parts are generally suffixes or titles. Wikipedia
        # redirects usually resolve the simpler given-name/surname form.
        return f"{parts[1]} {parts[0]}"
    return without_alias


def wikipedia_target(author: SourceAuthor) -> tuple[str, str]:
    if author.wikipedia_url:
        parsed = urlparse(author.wikipedia_url)
        assert parsed.hostname is not None
        return parsed.hostname, unquote(parsed.path.removeprefix("/wiki/")).replace(
            "_", " "
        )
    return "en.wikipedia.org", guessed_wikipedia_title(author.name)


class WikimediaClient:
    def __init__(self, timeout: float = 20.0, retries: int = 3) -> None:
        self.timeout = timeout
        self.retries = retries

    def get_json(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        request = Request(
            f"{endpoint}?{urlencode(params)}",
            headers={"User-Agent": USER_AGENT},
        )
        for attempt in range(self.retries):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.load(response)
            except HTTPError as error:
                if error.code != 429 and error.code < 500:
                    raise
                if attempt == self.retries - 1:
                    raise
                retry_after = error.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(min(delay, 10))
            except URLError:
                if attempt == self.retries - 1:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("unreachable")

    def wikipedia_pages(
        self, host: str, requested_titles: list[str]
    ) -> dict[str, WikipediaPage]:
        resolved: dict[str, WikipediaPage] = {}
        endpoint = f"https://{host}/w/api.php"
        for title_batch in batched(list(dict.fromkeys(requested_titles))):
            payload = self.get_json(
                endpoint,
                {
                    "action": "query",
                    "format": "json",
                    "formatversion": "2",
                    "redirects": "1",
                    "prop": "extracts|pageimages|info|pageprops",
                    "exintro": "1",
                    "explaintext": "1",
                    "piprop": "name",
                    "inprop": "url",
                    "titles": "|".join(title_batch),
                },
            )
            query = payload.get("query", {})
            aliases = _title_aliases(query)
            pages = {
                page.get("title", ""): page for page in query.get("pages", [])
            }
            for requested in title_batch:
                canonical_title = _follow_aliases(requested, aliases)
                page = pages.get(canonical_title)
                if not page or page.get("missing") or "disambiguation" in page.get(
                    "pageprops", {}
                ):
                    continue
                extract = (page.get("extract") or "").strip()
                image_name = page.get("pageimage")
                canonical_url = page.get("canonicalurl")
                page_id = page.get("pageid")
                if not extract or not image_name or not canonical_url or not page_id:
                    continue
                resolved[requested] = WikipediaPage(
                    title=page["title"],
                    canonical_url=canonical_url,
                    extract=extract,
                    image_title=f"File:{image_name}",
                )
        return resolved

    def commons_images(self, requested_titles: list[str]) -> dict[str, CommonsImage]:
        resolved: dict[str, CommonsImage] = {}
        for title_batch in batched(list(dict.fromkeys(requested_titles))):
            payload = self.get_json(
                COMMONS_API,
                {
                    "action": "query",
                    "format": "json",
                    "formatversion": "2",
                    "redirects": "1",
                    "prop": "imageinfo|info",
                    "iiprop": "extmetadata",
                    "inprop": "url",
                    "titles": "|".join(title_batch),
                },
            )
            query = payload.get("query", {})
            aliases = _title_aliases(query)
            pages = {
                page.get("title", ""): page for page in query.get("pages", [])
            }
            for requested in title_batch:
                canonical_title = _follow_aliases(requested, aliases)
                page = pages.get(canonical_title)
                image_info = (page or {}).get("imageinfo") or []
                if not page or page.get("missing") or not image_info:
                    continue
                metadata = image_info[0].get("extmetadata", {})
                license_name = metadata.get("LicenseShortName", {}).get("value")
                source_url = page.get("canonicalurl")
                if license_name and source_url:
                    resolved[requested] = CommonsImage(
                        source_url=source_url,
                        license=normalize_license(license_name),
                    )
        return resolved


def _title_aliases(query: dict[str, Any]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for key in ("normalized", "redirects"):
        for item in query.get(key, []):
            aliases[item["from"]] = item["to"]
    return aliases


def _follow_aliases(title: str, aliases: dict[str, str]) -> str:
    current = title.replace("_", " ")
    seen: set[str] = set()
    while current in aliases and current not in seen:
        seen.add(current)
        current = aliases[current]
    return current


def normalize_license(license_name: str) -> str:
    return LICENSE_ALIASES.get(html.unescape(license_name).strip(), license_name.strip())


def accepted_image_licenses(schema_path: Path) -> set[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return set(schema["items"]["properties"]["image"]["properties"]["license"]["enum"])


def concise_bio(extract: str, limit: int = MAX_BIO_LENGTH) -> str:
    text = re.sub(r"\s+", " ", extract).strip()
    if len(text) <= limit:
        return text

    candidate = text[:limit]
    sentence_ends = [match.end() for match in re.finditer(r"[.!?](?=\s|$)", candidate)]
    useful_ends = [position for position in sentence_ends if position >= 80]
    if useful_ends:
        return candidate[: useful_ends[-1]].strip()

    shortened = candidate[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{shortened}…"


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.casefold()).strip("-") or "author"


def display_name(wikipedia_title: str) -> str:
    """Remove Wikipedia's trailing parenthetical disambiguation suffix."""
    return re.sub(r"\s+\([^()]+\)$", "", wikipedia_title).strip()


def normalized_page_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{(parsed.hostname or '').casefold()}{unquote(parsed.path).rstrip('/')}"


def build_records(
    source_authors: list[SourceAuthor],
    client: WikimediaClient,
    allowed_licenses: set[str],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    stats: Counter[str] = Counter(source_rows=len(source_authors))
    targets: list[tuple[SourceAuthor, str, str]] = []
    titles_by_host: dict[str, list[str]] = defaultdict(list)
    for author in source_authors:
        host, title = wikipedia_target(author)
        targets.append((author, host, title))
        titles_by_host[host].append(title)

    wikipedia_pages: dict[tuple[str, str], WikipediaPage] = {}
    for host, titles in titles_by_host.items():
        for requested, page in client.wikipedia_pages(host, titles).items():
            wikipedia_pages[(host, requested)] = page

    commons_titles = [page.image_title for page in wikipedia_pages.values()]
    commons_images = client.commons_images(commons_titles)

    records: list[dict[str, Any]] = []
    seen_pages: set[str] = set()
    for _author, host, requested_title in targets:
        page = wikipedia_pages.get((host, requested_title))
        if page is None:
            stats["skipped_wikipedia"] += 1
            continue

        page_key = normalized_page_url(page.canonical_url)
        if page_key in seen_pages:
            stats["skipped_duplicate"] += 1
            continue
        seen_pages.add(page_key)

        image = commons_images.get(page.image_title)
        if image is None:
            stats["skipped_image"] += 1
            continue
        if image.license not in allowed_licenses:
            stats[f"skipped_license:{image.license}"] += 1
            continue

        name = display_name(page.title)
        records.append(
            {
                "about": {
                    "license": WIKIPEDIA_TEXT_LICENSE,
                    "origin": {"type": "human"},
                    "source_url": page.canonical_url,
                    "text": concise_bio(page.extract),
                },
                "id": slugify(name),
                "image": {
                    "license": image.license,
                    "source_url": image.source_url,
                },
                "name": name,
                "social_links": {"wikipedia": page.canonical_url},
            }
        )
        stats["eligible"] += 1
    return records, stats


def merge_records(
    existing: list[dict[str, Any]],
    generated: list[dict[str, Any]],
    overwrite_existing: bool,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    result = list(existing)
    stats: Counter[str] = Counter()
    indexes_by_wiki: dict[str, int] = {}
    indexes_by_name: dict[str, int] = {}
    used_ids = {author["id"] for author in result}
    for index, author in enumerate(result):
        wiki = author.get("social_links", {}).get("wikipedia")
        if wiki:
            indexes_by_wiki[normalized_page_url(wiki)] = index
        indexes_by_name[author["name"].casefold()] = index

    for record in generated:
        wiki_key = normalized_page_url(record["social_links"]["wikipedia"])
        existing_index = indexes_by_wiki.get(wiki_key)
        if existing_index is None:
            existing_index = indexes_by_name.get(record["name"].casefold())

        if existing_index is not None:
            if not overwrite_existing:
                stats["preserved_existing"] += 1
                continue
            old = result[existing_index]
            record["id"] = old["id"]
            record["social_links"] = {
                **old.get("social_links", {}),
                **record["social_links"],
            }
            result[existing_index] = record
            stats["updated"] += 1
            continue

        candidate_id = record["id"]
        if candidate_id in used_ids:
            suffix = 2
            while f"{candidate_id}-{suffix}" in used_ids:
                suffix += 1
            record["id"] = f"{candidate_id}-{suffix}"
        used_ids.add(record["id"])
        result.append(record)
        indexes_by_wiki[wiki_key] = len(result) - 1
        indexes_by_name[record["name"].casefold()] = len(result) - 1
        stats["added"] += 1
    return result, stats


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = json.dumps(value, ensure_ascii=False, indent=4) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        temporary.write(contents)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def print_summary(stats: Counter[str], dry_run: bool) -> None:
    action = "Would write" if dry_run else "Wrote"
    print(
        f"{action}: {stats['added']} added, {stats['updated']} updated, "
        f"{stats['preserved_existing']} existing preserved."
    )
    print(
        f"Source: {stats['source_rows']} rows; {stats['eligible']} eligible; "
        f"{stats['skipped_wikipedia']} without a resolvable Wikipedia page; "
        f"{stats['skipped_image']} without a Commons image; "
        f"{stats['skipped_duplicate']} duplicate page rows."
    )
    rejected = sorted(
        (key.removeprefix("skipped_license:"), count)
        for key, count in stats.items()
        if key.startswith("skipped_license:")
    )
    if rejected:
        details = ", ".join(f"{license_name} ({count})" for license_name, count in rejected)
        print(f"Rejected image licences: {details}.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Suntrap CSV URL or local file path (default: %(default)s)",
    )
    parser.add_argument(
        "--authors-path",
        type=Path,
        default=DEFAULT_AUTHORS_PATH,
        help="authors.json path",
    )
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="author schema path used for the image-licence allowlist",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="refresh matching records; otherwise preserve them",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="resolve data without writing authors.json"
    )
    parser.add_argument(
        "--limit", type=int, help="process only the first N source rows"
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be at least 1")

    source_authors = parse_source(read_source(args.source, args.timeout))
    if args.limit is not None:
        source_authors = source_authors[: args.limit]
    existing = json.loads(args.authors_path.read_text(encoding="utf-8"))
    allowed_licenses = accepted_image_licenses(args.schema_path)
    generated, build_stats = build_records(
        source_authors,
        WikimediaClient(timeout=args.timeout),
        allowed_licenses,
    )
    merged, merge_stats = merge_records(
        existing, generated, args.overwrite_existing
    )
    stats = build_stats + merge_stats
    if not args.dry_run:
        write_json_atomic(args.authors_path, merged)
    print_summary(stats, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
