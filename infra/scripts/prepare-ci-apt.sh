#!/usr/bin/env bash
# F211 T099: use the official HTTPS fallbacks on disposable GitHub runners.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != true || "${RUNNER_OS:-}" != Linux ]]; then
  echo 'CI APT preparation requires a GitHub Linux runner' >&2
  exit 1
fi
sudo python3 - <<'PY'
from pathlib import Path
import re

source = Path('/etc/apt/sources.list.d/ubuntu.sources')
mirror = Path('/etc/apt/apt-mirrors.txt')
for path in (source, mirror):
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f'CI APT preparation: expected a regular file: {path}')
# Accept only the runner's flat deb822 fields, including multiple stanzas.
sections = re.split(r'\n[ \t]*\n', source.read_text().strip())
for section in sections:
    fields = {}
    for line in section.splitlines():
        if line.startswith('#'):
            continue
        key, separator, value = line.partition(':')
        if not separator or not key or key[0].isspace() or key.lower() in fields:
            raise SystemExit('CI APT preparation: unsupported Ubuntu source fields')
        fields[key.lower()] = value.strip()
    if not fields:
        continue
    if (fields.get('uris') != 'mirror+file:/etc/apt/apt-mirrors.txt'
            or fields.get('enabled', 'yes') != 'yes'):
        raise SystemExit('CI APT preparation: unsupported Ubuntu mirror source')
if not any(line.startswith('URIs:') for line in source.read_text().splitlines()):
    raise SystemExit('CI APT preparation: missing Ubuntu mirror source')
azure = b'http://azure.archive.ubuntu.com/ubuntu/\tpriority:1\n'
official = (b'https://archive.ubuntu.com/ubuntu/\tpriority:2\n'
            b'https://security.ubuntu.com/ubuntu/\tpriority:3\n')
current = mirror.read_bytes()
if current not in (azure + official, official):
    raise SystemExit('CI APT preparation: unsupported Ubuntu mirror list')
if current != official:
    mirror.write_bytes(official)
if mirror.read_bytes() != official:
    raise SystemExit('CI APT preparation: mirror write verification failed')
print('CI APT mirrors: official Ubuntu HTTPS archives; Azure excluded')
PY
