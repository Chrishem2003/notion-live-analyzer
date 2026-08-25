﻿#!/usr/bin/env python3
"""
Applies any round3_files/, round5_files/, round8_files/ staging folders
sitting in the repo root by copying their contents over the real files at
the matching path, then removes the now-empty staging folder.
"""
import re
import shutil
from pathlib import Path

STAGING_FOLDERS = ["round3_files", "round5_files", "round8_files"]

def find_real_pages_target(repo_root: Path, staged_name: str):
    m = re.match(r"^(\d+)_", staged_name)
    if not m:
        return None
    prefix = m.group(1)
    pages_dir = repo_root / "pages"
    if not pages_dir.is_dir():
        return None
    for candidate in pages_dir.glob(f"{prefix}_*.py"):
        return candidate
    for candidate in pages_dir.glob(f"{int(prefix):02d}_*.py"):
        return candidate
    return None

def main():
    repo_root = Path(".").resolve()
    applied = []
    unmatched = []

    for staging_name in STAGING_FOLDERS:
        staging = repo_root / staging_name
        if not staging.is_dir():
            continue
        for src in staging.rglob("*.py"):
            rel = src.relative_to(staging)
            parts = rel.parts

            if len(parts) >= 1 and parts[-2:-1] == ("pages",) or (len(parts) >= 1 and parts[0] == "pages"):
                dest = find_real_pages_target(repo_root, src.name)
                if dest is None:
                    unmatched.append(str(rel))
                    continue
            else:
                dest = repo_root / rel

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            applied.append(str(dest.relative_to(repo_root)))
        shutil.rmtree(staging)
        print(f"Applied and removed: {staging_name}/")

    if applied:
        print(f"\nCopied {len(applied)} files over their real counterparts:")
        for f in sorted(set(applied)):
            print(" ", f)
    if unmatched:
        print(f"\n{len(unmatched)} files could not be matched automatically:")
        for f in unmatched:
            print(" ", f)
    if not applied and not unmatched:
        print("No staging folders found - nothing to apply.")

if __name__ == "__main__":
    main()
