#!/usr/bin/env python3
"""
CHRISHEM repo mojibake fixer.
Run from the repo root: python3 fix_mojibake.py

Fixes cp1252-decoded-as-utf8 double-encoding corruption (the recurring
" ðŸ ", "â€"", "×" style garbage in icons/dashes/emoji) without touching
already-correct text. Safe to re-run any time - it's idempotent, and it
only rewrites a file if something actually changed.
"""
import codecs
import glob
import re
import sys

cp1252_chars = set()
for b in range(0x80, 0x100):
    ch = bytes([b]).decode('cp1252', errors='ignore')
    if ch:
        cp1252_chars.add(ch)
for hole in (0x81, 0x8D, 0x8F, 0x90, 0x9D):
    cp1252_chars.add(chr(hole))

rev = {}
for b in range(256):
    ch = bytes([b]).decode('cp1252', errors='ignore')
    if ch:
        rev[ch] = b
for hole in (0x81, 0x8D, 0x8F, 0x90, 0x9D):
    rev[chr(hole)] = hole

run_pattern = re.compile('[' + ''.join(re.escape(c) for c in cp1252_chars) + ']+')

def encode_custom(s):
    return bytes(rev[ch] if ch in rev else ord(ch) for ch in s)

def fix_run(m):
    seg = m.group(0)
    try:
        return encode_custom(seg).decode('utf-8')
    except (KeyError, UnicodeDecodeError):
        return seg  # already-correct text, e.g. a real em-dash - leave it alone

def fix_text(text):
    for _ in range(5):  # handles rare multi-layer corruption
        new = run_pattern.sub(fix_run, text)
        if new == text:
            break
        text = new
    return text

def main():
    targets = sorted(set(
        glob.glob('*.py') + glob.glob('modules/*.py') + glob.glob('pages/*.py')
    ))
    changed = []
    still_bad = []
    for path in targets:
        raw = open(path, 'rb').read()
        if raw.startswith(codecs.BOM_UTF8):
            raw = raw[len(codecs.BOM_UTF8):]
        try:
            text = raw.decode('utf-8').replace('\r\n', '\n')
        except UnicodeDecodeError:
            still_bad.append((path, 'undecodable as utf-8'))
            continue
        fixed = fix_text(text)
        if fixed != text:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(fixed)
            changed.append(path)
        remaining = sum(1 for c in fixed if 0x80 <= ord(c) <= 0x9F)
        if remaining:
            still_bad.append((path, f'{remaining} chars need manual review'))

    print(f'Checked {len(targets)} files.')
    print(f'Fixed {len(changed)} files.')
    if still_bad:
        print(f'{len(still_bad)} files still need manual attention:')
        for p, msg in still_bad:
            print(f'  {p}: {msg}')
    else:
        print('No remaining corruption detected.')

if __name__ == '__main__':
    sys.exit(main())
