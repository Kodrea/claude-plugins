"""MD5 hash-based cache for incremental pipeline runs."""

import hashlib
import json
import os


def get_file_hash(path: str) -> str:
    """Compute MD5 hash of a file's contents."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_hashes(cache_path: str) -> dict[str, str]:
    """Load stored hash map from a JSON file."""
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return json.load(f)
    return {}


def save_hashes(hashes: dict[str, str], cache_path: str) -> None:
    """Persist hash map as JSON."""
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(hashes, f, indent=2)


def get_changed_files(directory: str, cache_path: str) -> tuple[list[str], dict[str, str]]:
    """Compare files in directory against cached hashes.

    Returns:
        Tuple of (changed_files, new_hashes) where changed_files is a list
        of paths that are new or modified since the last run.
    """
    old_hashes = load_hashes(cache_path)
    new_hashes = {}
    changed = []

    for root, _dirs, files in os.walk(directory):
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            path = os.path.join(root, fname)
            rel = os.path.relpath(path, directory)
            h = get_file_hash(path)
            new_hashes[rel] = h
            if old_hashes.get(rel) != h:
                changed.append(path)

    return changed, new_hashes
