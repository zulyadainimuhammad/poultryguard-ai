"""Build the local PoultryGuard AI knowledge-base index."""

from __future__ import annotations

import argparse
from pathlib import Path

from rag.indexing.indexer import KnowledgeBaseIndexer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk, embed and index PoultryGuard Markdown knowledge."
    )
    parser.add_argument(
        "--knowledge-base",
        type=Path,
        default=Path("knowledge_base"),
        help="Directory containing curated Markdown files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("vector_store"),
        help="Directory for the FAISS index and metadata.",
    )
    args = parser.parse_args()

    result = KnowledgeBaseIndexer(
        knowledge_base_dir=args.knowledge_base,
        index_dir=args.output,
    ).build()

    print("PoultryGuard knowledge index created successfully.")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
