"""Fix syntax errors in audit_portal.py - remove injected garbage characters."""
import pathlib

p = pathlib.Path('d:/notion-live-analyzer/modules/audit_portal.py')
text = p.read_text(encoding='utf-8')

# The create_file tool injects stray " characters into SQL strings
# Fix: remove spurious "" chars that appear before closing parens in SQL
import re

# Fix pattern: ," followed by newline and (pid
text = text.replace(',"\n                (pid', ',\n                (pid')

# Fix any other stray " chars in SQL context
lines = text.split('\n')
fixed = []
for line in lines:
    # Remove trailing " that breaks SQL continuation
    if line.rstrip().endswith('","') and '= c.execute("' not in line:
        line = line.rstrip()[:-1]
    if line.rstrip().endswith('?"'):
        # Keep as is - this is valid SQL parameter marker
        pass
    fixed.append(line)

text = '\n'.join(fixed)

# Also fix the student_stats method - the whole block after t variable
# Let's verify the syntax
p.write_text(text)
print(f"Written {len(text)} bytes")

# Try to compile
try:
    compile(text, 'audit_portal.py', 'exec')
    print("COMPILE OK - no syntax errors")
except SyntaxError as e:
    print(f"Still has error: {e}")
    # Find and print around the error
    lines = text.split('\n')
    lineno = e.lineno or 1
    for i in range(max(0,lineno-3), min(len(lines),lineno+2)):
        print(f"{i+1}: {lines[i]}")
</create_file>
