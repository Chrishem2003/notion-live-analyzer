@echo off
python -c "import pathlib; t=pathlib.Path('d:/notion-live-analyzer/gen_stealth.py').read_text(); print(len(t),'bytes'); print('Last 100 chars:',repr(t[-100:]))"
pause
