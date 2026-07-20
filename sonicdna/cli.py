"""SonicDNA persistent-index command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path

from sonicdna.database import IndexDatabase, default_database_path
from sonicdna.features import extract_features
from sonicdna.indexing import update_index
from sonicdna.search import search_index


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Find acoustically similar audio samples.")
    result.add_argument("query", type=Path, help="query audio sample")
    result.add_argument("folder", type=Path, help="sample-library folder")
    result.add_argument("--limit", type=int, default=10, help="maximum matches (default: 10)")
    result.add_argument("--database", type=Path, help="custom SQLite index path")
    result.add_argument("--rebuild", action="store_true", help="re-extract every file")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not args.query.is_file():
        parser().error(f"query is not a file: {args.query}")
    if not args.folder.is_dir():
        parser().error(f"library is not a folder: {args.folder}")
    if args.limit < 1:
        parser().error("--limit must be at least 1")
    database_path = args.database or default_database_path()
    print(f"Index: {database_path}")
    with IndexDatabase(database_path) as database:
        folder_id, summary = update_index(database, args.folder, rebuild=args.rebuild)
        print(
            f"Scan: {summary.discovered} found, {summary.indexed} indexed, "
            f"{summary.unchanged} unchanged, {summary.removed} removed"
        )
        query_vector = extract_features(args.query)
        results = search_index(
            query_vector, args.query, database.samples_for_folder(folder_id), args.limit
        )
    for rank, result in enumerate(results, 1):
        print(f"{rank:>3}  {result.similarity_score:>6.2f}  {result.path}")
    if summary.errors:
        print(f"Skipped {len(summary.errors)} unreadable file(s).")
        for error in summary.errors:
            print(f"  {error}")
    if not results:
        print("No searchable audio files found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
