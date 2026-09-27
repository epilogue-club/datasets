import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "update_authors.py"
SPEC = importlib.util.spec_from_file_location("update_authors", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
update_authors = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = update_authors
SPEC.loader.exec_module(update_authors)


class TestUpdateAuthors(unittest.TestCase):
    def test_parses_source_and_prefers_wikipedia_links(self) -> None:
        source = '''"NAME","BORN","DIED","BIO","LINK"
"Abbott, John","1805","1877","Bio","<a href='https://en.wikipedia.org/wiki/John_Abbott'>about</a>"
"Writer, Ada","1900","1980","Bio","none"
'''
        authors = update_authors.parse_source(source)

        self.assertEqual(authors[0].name, "Abbott, John")
        self.assertEqual(
            authors[0].wikipedia_url,
            "https://en.wikipedia.org/wiki/John_Abbott",
        )
        self.assertIsNone(authors[1].wikipedia_url)

    def test_guesses_surname_first_wikipedia_titles(self) -> None:
        self.assertEqual(
            update_authors.guessed_wikipedia_title(
                "Carroll, Lewis (Charles Lutwidge Dodgson)"
            ),
            "Lewis Carroll",
        )
        self.assertEqual(
            update_authors.guessed_wikipedia_title(
                "Carman, Bliss [William Bliss]"
            ),
            "Bliss Carman",
        )
        self.assertEqual(
            update_authors.guessed_wikipedia_title("Virginia Woolf"),
            "Virginia Woolf",
        )

    def test_concise_bio_respects_schema_limit(self) -> None:
        first_sentence = "A" * 100 + "."
        bio = update_authors.concise_bio(
            first_sentence + " " + "B" * update_authors.MAX_BIO_LENGTH
        )

        self.assertEqual(bio, first_sentence)
        self.assertLessEqual(len(bio), update_authors.MAX_BIO_LENGTH)

    def test_reads_accepted_licenses_from_schema(self) -> None:
        schema = {
            "items": {
                "properties": {
                    "image": {"properties": {"license": {"enum": ["CC0 1.0"]}}}
                }
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "schema.json"
            path.write_text(json.dumps(schema), encoding="utf-8")
            self.assertEqual(
                update_authors.accepted_image_licenses(path), {"CC0 1.0"}
            )

    def test_merging_preserves_existing_by_default(self) -> None:
        existing = [self.record("existing-id", "Ada Writer", "Ada_Writer", "old")]
        generated = [self.record("ada-writer", "Ada Writer", "Ada_Writer", "new")]

        merged, stats = update_authors.merge_records(existing, generated, False)

        self.assertEqual(merged, existing)
        self.assertEqual(stats["preserved_existing"], 1)

    def test_overwrite_retains_id_and_other_social_links(self) -> None:
        existing = [self.record("stable-id", "Ada Writer", "Ada_Writer", "old")]
        existing[0]["social_links"]["website"] = "https://example.com"
        generated = [self.record("ada-writer", "Ada Writer", "Ada_Writer", "new")]

        merged, stats = update_authors.merge_records(existing, generated, True)

        self.assertEqual(merged[0]["id"], "stable-id")
        self.assertEqual(merged[0]["about"]["text"], "new")
        self.assertEqual(
            merged[0]["social_links"]["website"], "https://example.com"
        )
        self.assertEqual(stats["updated"], 1)

    @staticmethod
    def record(author_id: str, name: str, page: str, bio: str) -> dict:
        url = f"https://en.wikipedia.org/wiki/{page}"
        return {
            "id": author_id,
            "name": name,
            "about": {
                "text": bio,
                "license": "CC BY-SA 4.0",
                "source_url": url,
                "origin": {"type": "human"},
            },
            "image": {
                "source_url": "https://commons.wikimedia.org/wiki/File:Ada.jpg",
                "license": "Public domain",
            },
            "social_links": {"wikipedia": url},
        }


if __name__ == "__main__":
    unittest.main()
