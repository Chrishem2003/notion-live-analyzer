#!/usr/bin/env python3
"""Repair the systemic encoding corruption where the binary ``+`` operator
was replaced by two (or more) spaces, e.g.::

    str(args)  str(kwargs)      ->  str(args) + str(kwargs)
    range(1, sample_size  1)    ->  range(1, sample_size + 1)
    time.time()  min(...)       ->  time.time() + min(...)
    top_vars[i  1:]             ->  top_vars[i + 1:]

The fixer is tokenizer-aware: it only rewrites gaps *between two operand-like
tokens* (not adjacent to an existing operator/keyword) that are separated by
2+ spaces, and it never touches strings, comments, or indentation.

Usage::

    python tools/fix_corruption.py [--apply] [paths...]

Without ``--apply`` it runs in dry-run mode. With ``--apply`` it rewrites
files in place.
"""
from __future__ import annotations

import io
import sys
import tokenize
from pathlib import Path

# Keywords / tokens that can never be an operand of a binary ``+``.
NON_OPERAND_KEYWORDS = {
    "import", "from", "as", "return", "def", "class", "if", "elif", "else",
    "for", "while", "in", "not", "and", "or", "lambda", "pass", "break",
    "continue", "raise", "yield", "assert", "del", "global", "nonlocal",
    "is", "with", "try", "except", "finally", "async", "await", "match",
    "case", "=", "==", "!=", "<=", ">=", "<", ">", "->", ":", ";", ",",
    ".", "@", "->", "*", "**", "/", "//", "%", "-", "+", "|", "&", "^",
    "<<", ">>", "+=", "-=", "*=", "/=", "//=", "%=", "|=", "&=", "^=",
    "**=", "<<=", ">>=", "(", "[", "{", "=>",
}


TOKEN_NAME = {v: k for k, v in vars(tokenize).items() if isinstance(v, int)}


def _is_operand_like(tok) -> bool:
    """True if a token can be one side of a binary ``+`` expression."""
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
        # Un-terminated string / inconsistent unindent â€” leave as-is; the file
        # is reported separately (indentation corruption is a different bug).
        return src, 0

    lines = src.split("\n")
    # fixes_by_line: line_no (1-based) -> list of (gap_start, gap_end) columns
    fixes_by_line: dict[int, list[tuple[int, int]]] = {}

    for i, tok in enumerate(tokens):
        prev = tokens[i - 1] if i > 0 else None
        if prev is None:
            continue
        if prev.end[0] != tok.start[0]:
            continue  # different lines
        gap_start = prev.end[1]
        gap_end = tok.start[1]
        if gap_end - gap_start < 2:
            continue
        if not (_is_operand_like(prev) and _is_operand_like(tok)):
            continue
        line_idx = tok.start[0] - 1
        line = lines[line_idx]
        gap_text = line[gap_start:gap_end]
        if gap_text.strip() != "":
            continue  # gap contains non-whitespace (unexpected)
        fixes_by_line.setdefault(tok.start[0], []).append((gap_start, gap_end))

    total_fixed = 0
    for lineno, ranges in fixes_by_line.items():
        line = lines[lineno - 1]
        for start, end in sorted(ranges, key=lambda r: r[0], reverse=True):
            line = line[:start] + " + " + line[end:]
            total_fixed += 1
        lines[lineno - 1] = line

    return "\n".join(lines), total_fixed


def main() -> int:
    apply = "--apply" in sys.argv
    paths = [p for p in sys.argv[1:] if p != "--apply"]

    if not paths:
        print(__doc__)
        return 0

    total_files = 0
    total_fixes = 0
    for raw in paths:
        p = Path(raw)
        files = sorted(p.rglob("*.py")) if p.is_dir() else [p]
        for f in files:
            try:
                src = f.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                print(f"SKIP  {f}: {e}")
                continue
            new_src, n = fix_source(src)
            if n == 0:
                continue
            total_files += 1
            total_fixes += n
            if apply:
                f.write_text(new_src, encoding="utf-8")
                print(f"FIXED {f}  ({n} gaps)")
            else:
                print(f"WOULD FIX {f}  ({n} gaps)")

    print(f"\nSummary: {total_files} file(s), {total_fixes} gap(s).")
    if not apply:
        print("Dry-run only. Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

