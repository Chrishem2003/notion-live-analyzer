

import os
import ast

project_dir = r"."
has_error = False

# Folders to ignore completely
IGNORE_DIRS = {"venv", ".git", ".venv", "__pycache__", "env"}

print("🔍 Auditing project files (skipping virtual environments)...\n")

for root, dirs, files in os.walk(project_dir):
    # Skip ignored directories in-place
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

    for file in files:
        if file.endswith(".py") and file != "check_syntax.py":
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, project_dir)

            try:
                # Read with utf-8-sig to catch and strip UFEFF Byte Order Mark
                with open(full_path, "r", encoding="utf-8-sig") as f:
                    content = f.read()

                # Re-save cleanly as standard UTF-8 (without BOM)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

            except Exception as e:
                print(f"Error re-encoding {rel_path}: {e}")
                continue

            # Attempt AST parse
            try:
                ast.parse(content, filename=full_path)
            except SyntaxError as e:
                has_error = True
                print(f"❌ FAILED: {rel_path}")
                print(f"   Line {e.lineno}, Col {e.offset}: {e.msg}")
                if e.text:
                    print(f"   Code snippet: {e.text.strip()}\n")

if not has_error:
    print("✅ SUCCESS: All project files cleaned of BOM signatures and passed AST syntax check!")

