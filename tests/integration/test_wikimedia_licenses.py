import json
import os
import subprocess
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen


AUTHORS_PATH = Path(__file__).resolve().parents[2] / "authors" / "authors.json"
WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"
WIKIMEDIA_LICENSE_ALIASES = {
    "CC0": "CC0 1.0",
}
WIKIMEDIA_BATCH_SIZE = 50
WIKIMEDIA_REQUEST_RETRIES = 4


def normalize_wikimedia_license(license_name: str) -> str:
    return WIKIMEDIA_LICENSE_ALIASES.get(license_name, license_name)


def changed_authors(authors: list[dict]) -> list[dict]:
    base_ref = os.environ.get("AUTHORS_BASE_REF", "HEAD")
    result = subprocess.run(
        ["git", "show", f"{base_ref}:authors/authors.json"],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Could not read authors/authors.json at {base_ref}: "
            f"{result.stderr.strip()}"
        )

    previous_authors = {
        author["id"]: author for author in json.loads(result.stdout)
    }
    return [
        author
        for author in authors
        if previous_authors.get(author["id"]) != author
    ]


def wikimedia_file_title(source_url: str) -> str | None:
    # urlparse separates text after a semicolon into ``params``, which corrupts
    # valid Commons filenames. urlsplit keeps the complete filename in ``path``.
    parsed_url = urlsplit(source_url)

    if parsed_url.hostname != "commons.wikimedia.org":
        return None

    if parsed_url.path.startswith("/wiki/"):
        title = unquote(parsed_url.path.removeprefix("/wiki/"))
    elif parsed_url.path == "/w/index.php":
        title = parse_qs(parsed_url.query).get("title", [None])[0]
    else:
        raise ValueError(f"Unrecognized Wikimedia Commons URL: {source_url}")

    if title is None or not title.startswith("File:"):
        raise ValueError(f"Commons URL does not identify a file: {source_url}")

    return title.replace("_", " ")


def fetch_wikimedia_licenses(file_titles: list[str]) -> dict[str, str]:
    licenses: dict[str, str] = {}
    unique_titles = list(dict.fromkeys(file_titles))

    for start in range(0, len(unique_titles), WIKIMEDIA_BATCH_SIZE):
        title_batch = unique_titles[start : start + WIKIMEDIA_BATCH_SIZE]
        query = urlencode(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "redirects": "1",
                "maxlag": "5",
                "prop": "imageinfo",
                "iiprop": "extmetadata",
                "titles": "|".join(title_batch),
            }
        )
        request = Request(
            f"{WIKIMEDIA_API_URL}?{query}",
            headers={
                "User-Agent": (
                    "epilogue-datasets Wikimedia licence integration test "
                    "(https://github.com/epilogue-club/datasets)"
                )
            },
        )

        for attempt in range(WIKIMEDIA_REQUEST_RETRIES):
            try:
                with urlopen(request, timeout=20) as response:
                    result = json.load(response)
                break
            except HTTPError as error:
                if error.code != 429 and error.code < 500:
                    raise
                retry_after = error.headers.get("Retry-After", "")
                error.close()
                if attempt == WIKIMEDIA_REQUEST_RETRIES - 1:
                    raise
                delay = float(retry_after) if retry_after.isdigit() else 2**attempt
                time.sleep(min(delay, 10))

        query_result = result["query"]
        aliases = {
            item["from"]: item["to"]
            for key in ("normalized", "redirects")
            for item in query_result.get(key, [])
        }
        pages = {page["title"]: page for page in query_result["pages"]}

        for requested_title in title_batch:
            resolved_title = requested_title.replace("_", " ")
            seen: set[str] = set()
            while resolved_title in aliases and resolved_title not in seen:
                seen.add(resolved_title)
                resolved_title = aliases[resolved_title]

            page = pages.get(resolved_title)
            if page is None or page.get("missing"):
                raise AssertionError(
                    f"Wikimedia file does not exist: {requested_title}"
                )
            licenses[requested_title] = page["imageinfo"][0]["extmetadata"][
                "LicenseShortName"
            ]["value"]

    return licenses


class TestWikimediaLicenses(unittest.TestCase):
    def test_extracts_file_title_from_commons_urls(self) -> None:
        self.assertEqual(
            wikimedia_file_title(
                "https://commons.wikimedia.org/wiki/File:Example_image.jpg"
            ),
            "File:Example image.jpg",
        )
        self.assertEqual(
            wikimedia_file_title(
                "https://commons.wikimedia.org/w/index.php"
                "?title=File:Example_image.jpg"
            ),
            "File:Example image.jpg",
        )
        self.assertEqual(
            wikimedia_file_title(
                "https://commons.wikimedia.org/wiki/"
                "File:Example;_with_parameters.jpg"
            ),
            "File:Example; with parameters.jpg",
        )

    def test_rejects_unrecognized_commons_urls(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Unrecognized Wikimedia Commons URL"
        ):
            wikimedia_file_title("https://commons.wikimedia.org/not-a-file")

    def test_normalizes_wikimedia_license_names(self) -> None:
        self.assertEqual(normalize_wikimedia_license("CC0"), "CC0 1.0")
        self.assertEqual(
            normalize_wikimedia_license("CC BY-SA 4.0"),
            "CC BY-SA 4.0",
        )

    def test_image_licenses_match_wikimedia(self) -> None:
        with AUTHORS_PATH.open(encoding="utf-8") as authors_file:
            authors = json.load(authors_file)

        authors = changed_authors(authors)
        wikimedia_authors = [
            (author, wikimedia_file_title(author["image"]["source_url"]))
            for author in authors
            if wikimedia_file_title(author["image"]["source_url"]) is not None
        ]

        if not wikimedia_authors:
            self.skipTest("No changed authors use Wikimedia Commons images")

        licenses = fetch_wikimedia_licenses(
            [file_title for _, file_title in wikimedia_authors]
        )

        for author, file_title in wikimedia_authors:
            with self.subTest(author=author["id"], file=file_title):
                api_license = normalize_wikimedia_license(
                    licenses[file_title]
                )
                self.assertEqual(
                    author["image"]["license"],
                    api_license,
                    (
                        f"{author['id']} has image licence "
                        f"{author['image']['license']!r}, but Wikimedia reports "
                        f"{api_license!r}"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
