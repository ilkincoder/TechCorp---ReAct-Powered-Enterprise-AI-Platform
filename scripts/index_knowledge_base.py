#!/usr/bin/env python3
"""Standalone knowledge base indexing script for Qdrant.

Usage:
    python scripts/index_knowledge_base.py                  # incremental
    python scripts/index_knowledge_base.py --force          # full rebuild
    python scripts/index_knowledge_base.py --department HR  # single dept
    python scripts/index_knowledge_base.py --dry-run        # preview only
"""

import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(
        description="Index TechCorp knowledge base PDFs into Qdrant"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-index all PDFs from scratch (ignore hash cache)",
    )
    parser.add_argument(
        "--department",
        type=str,
        default=None,
        help="Index only a specific department folder (e.g., 'HR', 'Engineering')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be indexed without actually indexing",
    )
    args = parser.parse_args()

    from techcorp_platform.config import KB_DIR, QDRANT_URL, QDRANT_COLLECTION
    from techcorp_platform.tools.rag_tool import RAGTool

    print(f"Qdrant URL: {QDRANT_URL}")
    print(f"Collection: {QDRANT_COLLECTION}")
    print(f"Knowledge base: {KB_DIR}")
    print(f"Mode: {'force rebuild' if args.force else 'incremental'}")
    if args.department:
        print(f"Department filter: {args.department}")
    if args.dry_run:
        print("*** DRY RUN — no changes will be made ***")
    print()

    tool = RAGTool()

    if args.dry_run:
        # Just list PDFs that would be processed
        pdf_files = sorted(KB_DIR.rglob("*.pdf"))
        if args.department:
            pdf_files = [p for p in pdf_files if p.parent.name == args.department]

        old_state = tool._load_index_state()
        print(f"Found {len(pdf_files)} PDFs:\n")
        for pdf_path in pdf_files:
            path_str = str(pdf_path)
            file_hash = RAGTool._compute_file_hash(pdf_path)
            status = "CHANGED" if old_state.get(path_str) != file_hash else "unchanged"
            if not args.force and path_str not in old_state:
                status = "NEW"
            marker = "→ index" if status in ("NEW", "CHANGED") else "→ skip"
            print(f"  [{status:9s}] {marker:7s}  {pdf_path.relative_to(KB_DIR)}")
        return

    # ── Progress callback with tqdm ─────────────────────────────────────────
    pbar = tqdm(total=0, desc="Indexing", unit="file")

    def progress_callback(done: int, total: int, current_file: str):
        if pbar.total != total:
            pbar.total = total
            pbar.refresh()
        pbar.set_postfix_str(current_file[:40])
        pbar.n = done
        pbar.refresh()

    # ── Run indexing ────────────────────────────────────────────────────────
    stats = tool._build_index(
        force=args.force,
        department=args.department,
        progress_callback=progress_callback,
    )
    pbar.close()

    # ── Report ──────────────────────────────────────────────────────────────
    print()
    print(f"  Total PDFs found : {stats['total_pdfs']}")
    print(f"  Indexed          : {stats['indexed']}")
    print(f"  Skipped (cached) : {stats['skipped']}")
    print(f"  Removed (deleted): {stats['removed']}")
    print(f"  Total chunks     : {stats['total_chunks']}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()