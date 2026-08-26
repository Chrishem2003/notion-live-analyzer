#!/usr/bin/env python3
"""
CHRISHEM palette remap - old cyan/near-black colors -> new instrument-console
palette (amber/graphite/verdigris). Run from the repo root: python3 remap_palette.py

Idempotent - safe to re-run any time. Only rewrites files that actually change.
"""
import glob

REMAP = {
    "#E8A33D": "#E8A33D", "#e8a33d": "#e8a33d",
    "#4FB8A6": "#4FB8A6", "#4fb8a6": "#4fb8a6",
    "#B5790E": "#B5790E", "#b5790e": "#b5790e",
    "#8B93A8": "#8B93A8", "#8b93a8": "#8b93a8",
    "#171B23": "#171B23", "#171B23": "#171B23",
    "#171B23": "#171B23",
    "#0B0E11": "#0B0E11",
    "#262B33": "#262B33", "#262B33": "#262B33",
    "#3A4048": "#3A4048",
    "#6B7280": "#6B7280", "#6B7280": "#6B7280",
    "#A8B0BC": "#A8B0BC", "#A8B0BC": "#A8B0BC",
    "#EDEFF2": "#EDEFF2", "#EDEFF2": "#EDEFF2",
    "#0B0E11": "#0B0E11", "#0B0E11": "#0B0E11",
    "#E5484D": "#E5484D", "#e5484d": "#e5484d",
    "#34C787": "#34C787", "#34c787": "#34c787",
    "#E8A33D": "#E8A33D", "#e8a33d": "#e8a33d",
}


def main():
    targets = sorted(set(
        glob.glob('*.py') + glob.glob('modules/*.py') + glob.glob('pages/*.py')
    ))
    changed = []
    for f in targets:
        text = open(f, encoding='utf-8').read()
        orig = text
        for old, new in REMAP.items():
            text = text.replace(old, new)
        if text != orig:
            with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(text)
            changed.append(f)
    print(f"Checked {len(targets)} files. Remapped colors in {len(changed)} files.")
    for f in changed:
        print(" ", f)


if __name__ == '__main__':
    main()
