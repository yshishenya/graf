"""Check the self-contained design prototype; does not contact product services."""
from pathlib import Path
import re
import subprocess

root = Path(__file__).parent
html = (root / 'prototype.html').read_text()
scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
assert len(scripts) == 1
script = scripts[0]
subprocess.run(['node', '--check'], input=script, text=True, check=True)
pure_rules = script.split('// DOM START')[0]
subprocess.run(['node', '-e', pure_rules + '\nconsole.log(checkRules()+" presentation checks passed");'], check=True)
ids = re.findall(r'\bid="([^"]+)"', html)
assert len(ids) == len(set(ids)), 'duplicate IDs'
lookups = set(re.findall(r"\$\('([^']+)'\)", script))
assert not lookups.difference(ids), lookups.difference(ids)
assert not re.search(r'\b(fetch|XMLHttpRequest|WebSocket)\s*\(', script), 'prototype must remain local'
for doc in root.rglob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
        if '://' not in target and not target.startswith('#'):
            assert (doc.parent / target.split('#')[0]).exists(), (doc, target)
print(f'HTML IDs: {len(ids)} unique; JS syntax and document links passed')
