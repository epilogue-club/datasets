import json
import unittest
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import Request, urlopen


AUTHORS_PATH = Path(__file__).resolve().parents[2] / "authors" / "authors.json"
WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"
WIKIMEDIA_LICENSE_ALIASES = {
    "CC0": "CC0 1.0",
}


def normalize_wikimedia_license(license_name: str) -> str:
    return WIKIMEDIA_LICENSE_ALIASES.get(license_name, license_name)


def wikimedia_file_title(source_url: str) -> str | None:
    parsed_url = urlparse(source_url)

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


def fetch_wikimedia_license(file_title: str) -> str:
    query = urlencode(
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "imageinfo",
            "iiprop": "extmetadata",
            "titles": file_title,
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

    with urlopen(request, timeout=20) as response:
        result = json.load(response)

    page = result["query"]["pages"][0]
    if page.get("missing"):
        raise AssertionError(f"Wikimedia file does not exist: {file_title}")

    return page["imageinfo"][0]["extmetadata"]["LicenseShortName"]["value"]


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

        wikimedia_authors = [
            (author, wikimedia_file_title(author["image"]["source_url"]))
            for author in authors
            if wikimedia_file_title(author["image"]["source_url"]) is not None
        ]

        self.assertGreater(
            len(wikimedia_authors),
            0,
            "Expected at least one author image hosted on Wikimedia Commons",
        )

        for author, file_title in wikimedia_authors:
            with self.subTest(author=author["id"], file=file_title):
                api_license = normalize_wikimedia_license(
                    fetch_wikimedia_license(file_title)
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
