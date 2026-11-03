"""One-time F282 acceptance proof; future landing changes do not run this in CI."""

import argparse
import hashlib
import re
import subprocess
from pathlib import Path

FEATURE = Path(__file__).resolve().parents[1]
ROOT = FEATURE.parents[1]
LINKS = (
    '          <a href="/transcription">Расшифровка аудио и видео</a>\n',
    '          <a href="/meeting-minutes">Протокол встречи</a>\n',
    '          <a href="/record-without-bot">Запись без бота</a>\n',
)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base-ref", help="Compare to the exact reviewed integration base instead of the historical baseline")
args = parser.parse_args()

baseline = (FEATURE / "evidence/baseline.md").read_text()
hashes = dict(re.findall(r"- `([^`]+)`: `([a-f0-9]{64})`", baseline))
assert len(hashes) == 4
for name, expected in hashes.items():
    if args.base_ref:
        base_content = subprocess.check_output(["git", "show", f"{args.base_ref}:{name}"], cwd=ROOT)
        expected = hashlib.sha256(base_content).hexdigest()
    content = (ROOT / name).read_bytes()
    if name.endswith("landing.html"):
        text = content.decode()
        for link in LINKS:
            assert text.count(link) == 1
            assert text.index(link) > text.index('<footer class="site-footer">')
            text = text.replace(link, "")
        content = text.encode()
    assert hashlib.sha256(content).hexdigest() == expected, name
print("F282 landing preservation: PASS (only three footer links; CSS/JS unchanged)")
