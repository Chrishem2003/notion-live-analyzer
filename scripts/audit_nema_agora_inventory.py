#!/usr/bin/env python3
"""Static import inventory for the NEMA-AGORA package.

This is a triage tool, not a deletion oracle: dynamic imports, plugin entrypoints,
deployment configuration, and external consumers may not appear in the graph.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

PHASE_SUFFIX = re.compile(r"_phase\d+\.py$", re.IGNORECASE)


def _module_name(path: Path, root: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_from(current_module: str, node: ast.ImportFrom, *, is_package_init: bool = False) -> str:
    if node.level == 0:
        return node.module or ""
    current_parts = current_module.split(".")
    package_parts = current_parts if is_package_init else current_parts[:-1]
    remove = max(node.level - 1, 0)
    if remove:
        package_parts = package_parts[:-remove]
    if node.module:
        package_parts.extend(node.module.split("."))
    return ".".join(part for part in package_parts if part)


def _imports(source: str, module_name: str, *, is_package_init: bool = False) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from(module_name, node, is_package_init=is_package_init)
            if base:
                found.add(base)
                if base == "nema_agora":
                    found.update(f"{base}.{alias.name}" for alias in node.names)
    return found


def build_inventory(root: Path) -> dict[str, object]:
    package_root = root / "nema_agora"
    if not package_root.is_dir():
        raise FileNotFoundError(f"Expected package directory: {package_root}")
    module_paths = sorted(package_root.rglob("*.py"))
    module_names = {_module_name(path, root): path for path in module_paths}
    reverse: dict[str, set[str]] = defaultdict(set)
    unresolved: dict[str, set[str]] = defaultdict(set)
    syntax_errors: list[dict[str, str]] = []
    phase_suffixed: list[str] = []

    scan_paths = sorted(
        path for base in (package_root, root / "pages", root / "tests")
        if base.exists() for path in base.rglob("*.py")
    )
    for path in scan_paths:
        importer = _module_name(path, root)
        try:
            source = path.read_text(encoding="utf-8-sig")
            imports = _imports(source, importer, is_package_init=path.name == "__init__.py")
        except OSError as exc:
            syntax_errors.append({"path": str(path.relative_to(root)), "error": type(exc).__name__})
            continue
        except UnicodeError:
            syntax_errors.append({"path": str(path.relative_to(root)), "error": "UnicodeError"})
            continue
        if path.is_relative_to(package_root) and PHASE_SUFFIX.search(path.name):
            phase_suffixed.append(str(path.relative_to(root)))
        for imported in imports:
            if imported in module_names:
                if imported != importer:
                    reverse[imported].add(importer)
            elif imported.startswith("nema_agora."):
                unresolved[imported].add(importer)

    records = []
    for name, path in sorted(module_names.items()):
        importers = sorted(reverse.get(name, set()))
        records.append({
            "module": name,
            "path": str(path.relative_to(root)),
            "static_importer_count": len(importers),
            "static_importers": importers,
            "phase_suffixed": bool(PHASE_SUFFIX.search(path.name)),
            "no_static_importers": not importers,
        })
    return {
        "schema_version": 1,
        "scope": ["nema_agora/**/*.py", "pages/**/*.py", "tests/**/*.py"],
        "module_count": len(module_names),
        "scanned_python_file_count": len(scan_paths),
        "phase_suffixed_package_files": sorted(phase_suffixed),
        "modules": records,
        "unresolved_nema_imports": [
            {"import": name, "importers": sorted(importers)}
            for name, importers in sorted(unresolved.items())
        ],
        "syntax_or_read_errors": syntax_errors,
        "warning": (
            "Static import absence is not proof of dead code. Review dynamic imports, "
            "API routes, deployment configuration, entrypoints, and external consumers "
            "before removing or renaming any module."
        ),
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    parser.add_argument("--output", type=Path, help="write JSON to this path instead of stdout")
    args = parser.parse_args(argv)
    report = build_inventory(args.root.resolve())
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if not report["syntax_or_read_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
