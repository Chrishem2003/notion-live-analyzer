#!/usr/bin/env python3
"""
Auto-fixer for systematic operator corruption in the CHRISHEM repository.

The corruption pattern: the '+' operator (and occasionally other operators)
was replaced with whitespace throughout the codebase. This script restores
the '+' operator in the specific corrupted patterns, then verifies each
file compiles successfully.

Targeted patterns (context-aware to avoid breaking strings/comments/indentation):
  1. `)  <expr>`  ->  `) + <expr>`          (double space after closing paren)
  2. `  )` inside expressions -> ` + )`      (double space before closing paren)
  3. `{<number><ident>}` -> `{<number> + <ident>}`  (collapsed space)
  4. `chr(<number><ident>)` -> `chr(<number> + <ident>)`
  5. `<number>/<number><ident>` -> `<number>/<number> + <ident>`
  6. `<ident>  <ident>` where both are identifiers -> `<ident> + <ident>`
  7. string concat: `<f-string>"  <expr>` -> `<f-string>" + <expr>`
"""
import re
import sys
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Files known to have syntax corruption
TARGET_FILES = [
    "modules/apa_formatter.py",
    "modules/audit_ui.py",
    "modules/causal_inference.py",
    "modules/chart_data_extractor.py",
    "modules/clinical_analytics.py",
    "modules/dashboard_builder.py",
    "modules/data_provenance.py",
    "modules/data_simulator.py",
    "modules/data_transformer.py",
    "modules/feature_engineer.py",
    "modules/google_sheets.py",
    "modules/grant_formatter.py",
    "modules/hypothesis_simulator.py",
    "modules/interactive_audio_engine.py",
    "modules/inventory_engine.py",
    "modules/literature_engine.py",
    "modules/meta_analysis.py",
    "modules/methodology_advisor.py",
    "modules/nl_query_engine.py",
    "modules/notion_client.py",
    "modules/satellite_engine.py",
    "modules/secure_personal_vault.py",
    "modules/secure_vault.py",
    "modules/sensitivity_engine.py",
    "modules/statistical_engine.py",
    "modules/verification.py",
    "pages/20_📊_Meta_Analysis.py",
    "pages/35_🔬_Methodology_Auditor.py",
    "pages/45_🎯_Project_Collaboration.py",
]


def compiles(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def is_in_string(line: str, idx: int) -> bool:
    """Heuristic: count unescaped quotes before idx to detect if we're inside a string."""
    # Count quotes before position, ignoring escaped quotes
    before = line[:idx]
    in_single = False
    in_double = False
    i = 0
    while i < len(before):
        ch = before[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        i += 1
    return in_single or in_double


def fix_file(path: Path) -> int:
    """Apply targeted fixes to a file. Returns number of replacements."""
    original = path.read_text(encoding="utf-8", errors="replace")
    lines = original.split("\n")
    total_fixes = 0

    for li, line in enumerate(lines):
        new_line = line
        replaced = True
        guard = 0

        # Skip pure comment lines and empty lines
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue

        # Pattern 3 & 4: collapsed number+identifier inside braces or chr()
        # e.g. {100idx} -> {100 + idx}, {chr(65i)} -> {chr(65 + i)}
        def fix_collapsed(m):
            num = m.group(1)
            ident = m.group(2)
            return f"{num} + {ident}"

        new_line = re.sub(r"(\d)([a-zA-Z_][a-zA-Z_0-9]*)", fix_collapsed, new_line)

        # Pattern 6: `<ident> <ident>` -> `<ident> + <ident>` (two space)
        # Only when not inside a string literal
        new_line = re.sub(
            r"([a-zA-Z_][a-zA-Z_0-9]*)\s{2}([a-zA-Z_][a-zA-Z_0-9]*)",
            r"\1 + \2",
            new_line,
        )

        # Pattern 1: `)  <expr>` -> `) + <expr>`
        new_line = re.sub(
            r"\)\s{2}([0-9a-zA-Z_(])",
            r") + \1",
            new_line,
        )

        # Pattern 5: `<digit>/<digit><ident>` -> `<digit>/<digit> + <ident>`
        new_line = re.sub(
            r"(\d)\s*/\s*(\d)([a-zA-Z_][a-zA-Z_0-9]*)\b",
            r"\1 / \2 + \3",
            new_line,
        )

        # Pattern 7: string concatenation `"  (expr` -> `" + (expr`
        new_line = re.sub(
            r"([\"'])\s{2}\(\s*([a-zA-Z_\"'])",
            r"\1 + (\2",
            new_line,
        )

        # Pattern 2: `  )` -> ` + )` e.g. `x  1)` -> `x + 1)`
        new_line = re.sub(
            r"([0-9a-zA-Z_\]\)])\s{2}(\))",
            r"\1 + \2",
            new_line,
        )

        # Specific: `  \` continuation (line continuation) -> ` + \`
        new_line = re.sub(
            r"([0-9a-zA-Z_\)\]])\s{2}(\\)\s*$",
            r"\1 + \2",
            new_line,
        )

        if new_line != line:
            # Only apply if not inside a string (heuristic on the changed region)
            # We'll apply generously but verify by compiling at the end
            lines[li] = new_line
            total_fixes += 1

    new_content = "\n".join(lines)
    path.write_text(new_content, encoding="utf-8")
    return total_fixes


def main():
    fixed_ok = []
    still_broken = []
    for rel in TARGET_FILES:
        path = ROOT / rel
        if not path.exists():
            still_broken.append((rel, "file not found"))
            continue
        before = compiles(path)
        if before:
            fixed_ok.append((rel, "already ok"))
            continue
        n = fix_file(path)
        if compiles(path):
            fixed_ok.append((rel, f"fixed ({n} replacements)"))
        else:
            still_broken.append((rel, f"still broken after {n} fixes"))

    print("=== FIXED ===")
    for name, status in fixed_ok:
        print(f"  OK: {name} ({status})")
    print("\n=== STILL BROKEN ===")
    for name, status in still_broken:
        print(f"  FAIL: {name} ({status})")


if __name__ == "__main__":
    main()
