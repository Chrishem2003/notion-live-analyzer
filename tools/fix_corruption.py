#!/usr/bin/env python3
"""Repair the systemic encoding corruption where a binary plus operator
was replaced by two or more spaces.

The fixer is tokenizer-aware. It only rewrites whitespace gaps between
operand-like tokens on the same line; it does not touch strings, comments,
or indentation.

Usage:
    python tools/fix_corruption.py [--apply] [paths...]

Without --apply the tool is read-only. With --apply, each changed file is
rewritten atomically only after an exclusive adjacent .bak copy is created.
Existing backups are never overwritten. Symlinks, hard-linked files, and
non-UTF-8 source files are skipped. Paths in console output are JSON-quoted.
"""
from __future__ import annotations

import io
import json
import os
import stat
import sys
import tempfile
import tokenize
from pathlib import Path

# Keywords / tokens that can never be an operand of a binary plus operator.
NON_OPERAND_KEYWORDS = {
    "import", "from", "as", "return", "def", "class", "if", "elif", "else",
    "for", "while", "in", "not", "and", "or", "lambda", "pass", "break",
    "continue", "raise", "yield", "assert", "del", "global", "nonlocal",
    "is", "with", "try", "except", "finally", "async", "await", "match",
    "case", "=", "==", "!=", "<=", ">=", "<", ">", "->", ":", ";", ",",
    ".", "@", "*", "**", "/", "//", "%", "-", "+", "|", "&", "^",
    "<<", ">>", "+=", "-=", "*=", "/=", "//=", "%=", "|=", "&=", "^=",
    "**=", "<<=", ">>=", "(", "[", "{", "=>",
}

TOKEN_NAME = {v: k for k, v in vars(tokenize).items() if isinstance(v, int)}


def _is_operand_like(tok) -> bool:
    """True if a token can be one side of a binary plus expression."""
    tname = TOKEN_NAME.get(tok.type, "")
    if tname in ("NAME", "NUMBER", "STRING"):
        return tok.string not in NON_OPERAND_KEYWORDS
    if tname == "OP":
        return tok.string in (")", "]", "}")
    return False


def fix_source(src: str) -> tuple[str, int]:
    """Return (fixed_source, number_of_gaps_fixed)."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError):
        # Unterminated strings and inconsistent unindent are separate defects.
        return src, 0

    lines = src.split("\n")
    fixes_by_line: dict[int, list[tuple[int, int]]] = {}

    for i, tok in enumerate(tokens):
        prev = tokens[i - 1] if i > 0 else None
        if prev is None or prev.end[0] != tok.start[0]:
            continue
        gap_start = prev.end[1]
        gap_end = tok.start[1]
        if gap_end - gap_start < 2:
            continue
        if not (_is_operand_like(prev) and _is_operand_like(tok)):
            continue
        line_idx = tok.start[0] - 1
        line = lines[line_idx]
        if line[gap_start:gap_end].strip() != "":
            continue
        fixes_by_line.setdefault(tok.start[0], []).append((gap_start, gap_end))

    total_fixed = 0
    for lineno, ranges in fixes_by_line.items():
        line = lines[lineno - 1]
        for start, end in sorted(ranges, key=lambda r: r[0], reverse=True):
            line = line[:start] + " + " + line[end:]
            total_fixed += 1
        lines[lineno - 1] = line

    return "\n".join(lines), total_fixed


def _quoted_path(path: Path) -> str:
    """Render filesystem paths without allowing terminal/log control injection."""
    return json.dumps(str(path), ensure_ascii=True)


def _remove_created_backup(backup: Path, created_stat: os.stat_result) -> None:
    """Remove only the backup inode created by this invocation."""
    try:
        current = backup.lstat()
        if (
            stat.S_ISREG(current.st_mode)
            and (current.st_dev, current.st_ino)
            == (created_stat.st_dev, created_stat.st_ino)
        ):
            backup.unlink()
    except OSError:
        pass


def _write_with_backup(
    path: Path,
    original_bytes: bytes,
    updated_bytes: bytes,
    original_stat: os.stat_result,
) -> tuple[bool, str]:
    """Create an exclusive backup, then atomically replace an unchanged file."""
    if path.is_symlink():
        return False, "symbolic link detected; source left unchanged"
    if original_stat.st_nlink > 1:
        return False, "hard-linked file detected; source left unchanged"

    try:
        current_stat = path.lstat()
        if (
            not stat.S_ISREG(current_stat.st_mode)
            or (current_stat.st_dev, current_stat.st_ino)
            != (original_stat.st_dev, original_stat.st_ino)
            or path.read_bytes() != original_bytes
        ):
            return False, "source changed during processing; refusing to overwrite"
    except OSError:
        return False, "source could not be rechecked; refusing to overwrite"

    backup = path.with_name(path.name + ".bak")
    try:
        backup_fd = os.open(
            str(backup), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
    except FileExistsError:
        return False, "adjacent .bak backup already exists; refusing to overwrite"
    except OSError:
        return False, "could not reserve an adjacent .bak backup; source unchanged"

    created_stat = os.fstat(backup_fd)
    try:
        with os.fdopen(backup_fd, "wb") as backup_stream:
            backup_stream.write(original_bytes)
            backup_stream.flush()
            os.fsync(backup_stream.fileno())
    except OSError:
        _remove_created_backup(backup, created_stat)
        return False, "backup write failed; source unchanged"

    temp_path: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=".fix-corruption-", suffix=".tmp", dir=str(path.parent)
        )
        temp_path = Path(temp_name)
        with os.fdopen(fd, "wb") as temp_stream:
            temp_stream.write(updated_bytes)
            temp_stream.flush()
            os.fsync(temp_stream.fileno())
        os.chmod(temp_path, stat.S_IMODE(original_stat.st_mode))

        current_stat = path.lstat()
        if (
            not stat.S_ISREG(current_stat.st_mode)
            or (current_stat.st_dev, current_stat.st_ino)
            != (original_stat.st_dev, original_stat.st_ino)
            or path.read_bytes() != original_bytes
        ):
            return False, "source changed during processing; backup retained"

        os.replace(temp_path, path)
        temp_path = None
        return True, "backup created as adjacent .bak file"
    except OSError:
        return False, "atomic replacement failed; original left unchanged and backup retained"
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass


def main() -> int:
    apply = "--apply" in sys.argv[1:]
    paths = [arg for arg in sys.argv[1:] if arg != "--apply"]

    if not paths:
        print(__doc__)
        return 0

    candidate_files = 0
    candidate_fixes = 0
    written_files = 0
    skipped_files = 0

    for raw in paths:
        root = Path(raw)
        if root.is_symlink():
            files = [root]
        else:
            files = sorted(root.rglob("*.py")) if root.is_dir() else [root]

        for source in files:
            display = _quoted_path(source)
            try:
                source_stat = source.lstat()
            except OSError:
                print(f"SKIP {display}: source cannot be inspected safely")
                skipped_files += 1
                continue

            if stat.S_ISLNK(source_stat.st_mode):
                print(f"SKIP {display}: symbolic link is not modified")
                skipped_files += 1
                continue
            if not stat.S_ISREG(source_stat.st_mode):
                print(f"SKIP {display}: not a regular file")
                skipped_files += 1
                continue
            if source_stat.st_nlink > 1:
                print(f"SKIP {display}: hard-linked file is not modified")
                skipped_files += 1
                continue

            try:
                original_bytes = source.read_bytes()
            except OSError:
                print(f"SKIP {display}: source cannot be read safely")
                skipped_files += 1
                continue
            try:
                src = original_bytes.decode("utf-8")
            except UnicodeDecodeError:
                print(f"SKIP {display}: source is not valid UTF-8; refusing to rewrite")
                skipped_files += 1
                continue

            new_src, count = fix_source(src)
            if count == 0:
                continue

            candidate_files += 1
            candidate_fixes += count
            if not apply:
                print(f"WOULD FIX {display} ({count} gaps)")
                continue

            success, message = _write_with_backup(
                source, original_bytes, new_src.encode("utf-8"), source_stat
            )
            if success:
                written_files += 1
                print(f"FIXED {display} ({count} gaps); {message}")
            else:
                skipped_files += 1
                print(f"SKIP {display}: {message}")

    print(
        f"\nSummary: {candidate_files} candidate file(s), {candidate_fixes} gap(s), "
        f"{written_files} file(s) written, {skipped_files} skipped."
    )
    if not apply:
        print("Dry-run only. No files were written.")
    return 1 if skipped_files else 0


if __name__ == "__main__":
    raise SystemExit(main())
