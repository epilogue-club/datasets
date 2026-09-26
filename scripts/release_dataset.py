#!/usr/bin/env python3
"""Build a versioned, self-describing dataset release.

Dataset releases use calendar versions (YYYY.MM.DD, then YYYY.MM.DD.N for
additional releases on the same UTC day). Schema versions remain SemVer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path


SEMVER = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_version_from_git(repository: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "tag", "--list", "--sort=-version:refname", "v[0-9]*"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise ValueError(
            "could not determine the schema version from Git tags; "
            "pass --schema-version explicitly"
        ) from error

    tags = result.stdout.splitlines()
    if not tags:
        raise ValueError(
            "could not determine the schema version from Git tags; "
            "pass --schema-version explicitly"
        )

    latest_tag = tags[0].strip()
    version = latest_tag.removeprefix("v")
    if not SEMVER.fullmatch(version):
        raise ValueError(f"latest Git tag is not a SemVer version: {latest_tag}")
    return version


def next_dataset_version(output_dir: Path, release_date: date) -> str:
    base = release_date.strftime("%Y.%m.%d")
    used_revisions: set[int] = set()

    if output_dir.exists():
        pattern = re.compile(rf"^{re.escape(base)}(?:\.(\d+))?$")
        for child in output_dir.iterdir():
            if not child.is_dir():
                continue
            match = pattern.fullmatch(child.name)
            if match:
                used_revisions.add(int(match.group(1) or 0))

    if 0 not in used_revisions:
        return base

    revision = 1
    while revision in used_revisions:
        revision += 1
    return f"{base}.{revision}"


def load_record_count(dataset: Path) -> int:
    with dataset.open(encoding="utf-8") as source:
        contents = json.load(source)
    if not isinstance(contents, list):
        raise ValueError(f"dataset must contain a top-level JSON array: {dataset}")
    return len(contents)


def ensure_json_object(path: Path, description: str) -> None:
    with path.open(encoding="utf-8") as source:
        contents = json.load(source)
    if not isinstance(contents, dict):
        raise ValueError(f"{description} must contain a top-level JSON object: {path}")


def build_release(
    *,
    dataset: Path,
    schema: Path,
    output_dir: Path,
    schema_version: str,
    release_date: date,
    generated_at: datetime,
    data_through: date | None = None,
) -> Path:
    if not SEMVER.fullmatch(schema_version):
        raise ValueError(f"invalid SemVer schema version: {schema_version}")
    if not dataset.is_file():
        raise ValueError(f"dataset does not exist: {dataset}")
    if not schema.is_file():
        raise ValueError(f"schema does not exist: {schema}")

    record_count = load_record_count(dataset)
    ensure_json_object(schema, "schema")
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_version = next_dataset_version(output_dir, release_date)
    destination = output_dir / dataset_version

    with tempfile.TemporaryDirectory(prefix="dataset-release-", dir=output_dir) as temporary:
        staging = Path(temporary)
        released_dataset = staging / dataset.name
        released_schema = staging / schema.name
        shutil.copyfile(dataset, released_dataset)
        shutil.copyfile(schema, released_schema)

        manifest: dict[str, object] = {
            "dataset_version": dataset_version,
            "schema_version": schema_version,
            "generated_at": generated_at.astimezone(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
            "record_count": record_count,
            "files": {
                "dataset": {
                    "path": released_dataset.name,
                    "bytes": released_dataset.stat().st_size,
                    "sha256": sha256(released_dataset),
                },
                "schema": {
                    "path": released_schema.name,
                    "bytes": released_schema.stat().st_size,
                    "sha256": sha256(released_schema),
                },
            },
        }
        if data_through is not None:
            manifest["data_through"] = data_through.isoformat()

        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=4) + "\n", encoding="utf-8"
        )
        try:
            staging.rename(destination)
        except FileExistsError as error:
            raise ValueError(
                f"release destination already exists (another build may have won): {destination}"
            ) from error

    return destination


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected a date in YYYY-MM-DD format") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("authors/authors.json"))
    parser.add_argument("--schema", type=Path, default=Path("schema/author.schema.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("dist/authors"))
    parser.add_argument(
        "--schema-version",
        help="SemVer schema version; defaults to the latest v-prefixed Git tag",
    )
    parser.add_argument(
        "--data-through",
        type=parse_iso_date,
        help="optional source-confirmed data cutoff in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--release-date",
        type=parse_iso_date,
        help="release date override for reproducible builds (defaults to today in UTC)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = Path(__file__).resolve().parent.parent

    try:
        schema_version = args.schema_version or schema_version_from_git(repository)
        release_date = args.release_date or datetime.now(timezone.utc).date()
        destination = build_release(
            dataset=args.dataset,
            schema=args.schema,
            output_dir=args.output_dir,
            schema_version=schema_version,
            release_date=release_date,
            generated_at=datetime.now(timezone.utc),
            data_through=args.data_through,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
