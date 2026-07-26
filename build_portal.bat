@echo off
python -c "import pathlib; t=pathlib.Path('d:/notion-live-analyzer/gen_stealth.py').read_text()"
python -c "t=open('d:/notion-live-analyzer/gen_stealth.py').read(); i=t.rfind('def render_stealth_humanizer_ui'); open('d:/notion-live-analyzer/gen_stealth_clean.py','w').write(t[:i])" 
echo Part 1 written
type d:\notion-live-analyzer\gen_stealth_clean.py | find /c /v ""
pause
