"""One-time F282 acceptance proof; future landing changes do not run this in CI."""

import hashlib
import re
from pathlib import Path

FEATURE = Path(__file__).resolve().parents[1]
ROOT = FEATURE.parents[1]
LINKS = (
    '          <a href="/transcription">Расшифровка аудио и видео</a>\n',
    '          <a href="/meeting-minutes">Протокол встречи</a>\n',
    '          <a href="/record-without-bot">Запись без бота</a>\n',
)

baseline = (FEATURE / "evidence/baseline.md").read_text()
hashes = dict(re.findall(r"- `([^`]+)`: `([a-f0-9]{64})`", baseline))
assert len(hashes) == 4
for name, expected in hashes.items():
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
