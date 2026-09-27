import json
import unittest
from pathlib import Path
from urllib.parse import unquote, urlencode, urlparse
from urllib.request import Request, urlopen


AUTHORS_PATH = Path(__file__).resolve().parents[2] / "authors" / "authors.json"
WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"


def wikimedia_file_title(source_url: str) -> str | None:
    parsed_url = urlparse(source_url)

    if parsed_url.hostname != "commons.wikimedia.org":
        return None

    prefix = "/wiki/"
    if not parsed_url.path.startswith(prefix):
        return None

    title = unquote(parsed_url.path.removeprefix(prefix)).replace("_", " ")
    return title if title.startswith("File:") else None


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
                api_license = fetch_wikimedia_license(file_title)
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
