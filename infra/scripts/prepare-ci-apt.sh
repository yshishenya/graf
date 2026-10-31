#!/usr/bin/env bash
# F211 T099: use the official HTTPS fallbacks on disposable GitHub runners.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != true || "${RUNNER_OS:-}" != Linux ]]; then
  echo 'CI APT preparation requires a GitHub Linux runner' >&2
  exit 1
fi
sudo python3 - <<'PY'
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import re

def describe(uri):
    if uri == "mirror+file:/etc/apt/apt-mirrors.txt":
        return {"kind": "mirror_list"}
    try:
        value = urlsplit(uri)
        host = value.hostname or ""
        if (value.scheme in {"http", "https"}
                and len(host) <= 253
                and re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*ubuntu\.com", host)
                and all(32 < ord(char) < 127 for char in uri)
                and value.netloc.lower() == host
                and value.path in {"/ubuntu", "/ubuntu/"}
                and value.username is None and value.password is None
                and value.port is None and not value.query and not value.fragment):
            return {"kind": "ubuntu_uri", "scheme": value.scheme,
                    "host": host, "path": value.path}
    except ValueError:
        pass
    return {"kind": "UNKNOWN", "sha256": hashlib.sha256(uri.encode()).hexdigest()}

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
        uri = fields.get('uris', '')
        descriptions = ([describe(value) for value in uri.split()] if len(uri) <= 4096
                        else [{"kind": "UNKNOWN", "sha256": hashlib.sha256(uri.encode()).hexdigest()}])
        print(json.dumps({"uris": descriptions, "enabled": fields.get('enabled', 'yes') == 'yes'}), flush=True)
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
