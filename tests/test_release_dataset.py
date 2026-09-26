import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from scripts.release_dataset import build_release


class BuildReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.dataset = self.root / "authors.json"
        self.schema = self.root / "author.schema.json"
        self.output = self.root / "dist"
        self.dataset.write_text('[{"id": "one"}, {"id": "two"}]\n', encoding="utf-8")
        self.schema.write_text('{"type": "array"}\n', encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def build(self, **overrides: object) -> Path:
        arguments = {
            "dataset": self.dataset,
            "schema": self.schema,
            "output_dir": self.output,
            "schema_version": "1.2.3",
            "release_date": date(2026, 9, 26),
            "generated_at": datetime(2026, 9, 26, 12, 30, tzinfo=timezone.utc),
        }
        arguments.update(overrides)
        return build_release(**arguments)  # type: ignore[arg-type]

    def test_builds_release_and_manifest(self) -> None:
        release = self.build(data_through=date(2026, 9, 24))
        manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(release.name, "2026.09.26")
        self.assertEqual(manifest["dataset_version"], "2026.09.26")
        self.assertEqual(manifest["schema_version"], "1.2.3")
        self.assertEqual(manifest["data_through"], "2026-09-24")
        self.assertEqual(manifest["generated_at"], "2026-09-26T12:30:00Z")
        self.assertEqual(manifest["record_count"], 2)
        self.assertEqual(len(manifest["files"]["dataset"]["sha256"]), 64)
        self.assertEqual((release / self.dataset.name).read_bytes(), self.dataset.read_bytes())
        self.assertEqual((release / self.schema.name).read_bytes(), self.schema.read_bytes())

    def test_increments_same_day_revision(self) -> None:
        first = self.build()
        second = self.build()
        third = self.build()

        self.assertEqual(first.name, "2026.09.26")
        self.assertEqual(second.name, "2026.09.26.1")
        self.assertEqual(third.name, "2026.09.26.2")

    def test_rejects_invalid_schema_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid SemVer"):
            self.build(schema_version="version-one")


if __name__ == "__main__":
    unittest.main()
