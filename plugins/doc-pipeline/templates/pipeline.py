#!/usr/bin/env python3
"""Pipeline CLI: discover and fetch documentation sections as markdown.

Usage:
    python docs/pipeline.py <section_url> [--force] [--tab TAB] [--section-name NAME]

Examples:
    python docs/pipeline.py https://docs.example.com/en/product/getting-started
    python docs/pipeline.py https://docs.example.com/en/product/api-reference --force
    python docs/pipeline.py https://docs.example.com/en/product/guides --tab "Product X"

After this script completes, Claude Code takes over for the AI tiers
(scout → processor → auditor) to produce REFERENCE.md.
"""

import argparse
import os
import sys

# Allow running from project root: python docs/pipeline.py ...
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lib.discover import discover_pages
from lib.fetch import fetch_all
from lib.cache import get_changed_files, save_hashes


def derive_section_name(url: str) -> str:
    """Extract section name from URL path.

    Example: https://docs.example.com/en/product/getting-started → getting-started
    """
    path = url.rstrip("/").split("/")
    return path[-1]


def main():
    parser = argparse.ArgumentParser(
        description="Discover and fetch documentation sections as markdown"
    )
    parser.add_argument("url", help="Section URL to fetch")
    parser.add_argument("--force", action="store_true", help="Re-fetch all pages even if cached")
    parser.add_argument("--tab", default=None, help="Board/variant tab to select (if applicable)")
    parser.add_argument("--section-name", help="Override section name (default: derived from URL)")
    args = parser.parse_args()

    section_name = args.section_name or derive_section_name(args.url)
    docs_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(docs_dir, "sections", section_name, "raw")
    cache_path = os.path.join(docs_dir, "sections", section_name, "build_cache", "hashes.json")

    print(f"Section: {section_name}")
    print(f"Output:  {raw_dir}")
    print()

    # Step 1: Discover pages
    print("=== Discovering pages ===")
    pages = discover_pages(args.url)
    print(f"Found {len(pages)} pages:")
    for p in pages:
        indent = "  " * (p["depth"] + 1)
        print(f"{indent}{p['title']} ({p['slug']})")
    print()

    # Step 2: Fetch and convert to markdown
    print("=== Fetching pages ===")
    saved = fetch_all(pages, raw_dir, tab_label=args.tab)
    print(f"\nFetched {len(saved)} pages to {raw_dir}")
    print()

    # Step 3: Report what changed
    if not args.force:
        changed, new_hashes = get_changed_files(raw_dir, cache_path)
        save_hashes(new_hashes, cache_path)
        print(f"=== Cache status ===")
        print(f"Total files: {len(new_hashes)}")
        print(f"Changed:     {len(changed)}")
        if changed:
            for path in changed:
                print(f"  * {os.path.relpath(path, raw_dir)}")
    else:
        print("=== Cache skipped (--force) ===")

    # Step 4: Print manifest
    print()
    print("=== Manifest ===")
    total_size = 0
    for path in saved:
        size = os.path.getsize(path)
        total_size += size
        rel = os.path.relpath(path, raw_dir)
        print(f"  {rel:50s} {size:>6,d} bytes")
    print(f"  {'TOTAL':50s} {total_size:>6,d} bytes")
    print()
    print("Pipeline step 1 complete. Ready for AI tiers (scout → processor → auditor).")


if __name__ == "__main__":
    main()
