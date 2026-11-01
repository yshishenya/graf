#!/usr/bin/env bash
# F211 T112: normalize package sources on disposable GitHub Ubuntu runners.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != true || "${RUNNER_OS:-}" != Linux || "${RUNNER_ENVIRONMENT:-}" != github-hosted ]]; then
  echo 'CI APT preparation requires a GitHub-hosted Linux runner' >&2
  exit 1
fi
sudo python3 - <<'PY'
from pathlib import Path
import os
import re
import stat
import subprocess
import tempfile


def fail(reason):
    raise SystemExit('CI APT preparation: ' + reason)


def fingerprint(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def checked_read(path, limit, label):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_mode & 0o022 or not 0 < before.st_size <= limit:
        fail(f'unsafe {label} metadata type={stat.S_IFMT(before.st_mode)} '
             f'uid={before.st_uid} gid={before.st_gid} '
             f'mode={stat.S_IMODE(before.st_mode):o} size={before.st_size}')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        if fingerprint(os.fstat(stream.fileno())) != fingerprint(before):
            fail('input changed while opening')
        data = stream.read(limit + 1)
        if len(data) != before.st_size or fingerprint(os.fstat(stream.fileno())) != fingerprint(before):
            fail('input changed while reading')
    return data, before


platform = dict(line.split('=', 1) for line in Path('/usr/lib/os-release').read_text().splitlines()
                if line and not line.startswith('#') and '=' in line)
if any(platform.get(k, '').strip('"') != v for k, v in
       {'ID': 'ubuntu', 'VERSION_ID': '24.04', 'VERSION_CODENAME': 'noble'}.items()):
    fail('expected Ubuntu 24.04 noble')
if (subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip() != 'amd64'
        or subprocess.check_output(['dpkg', '--print-foreign-architectures'], text=True).strip()):
    fail('expected native amd64 without foreign architectures')
source = Path('/etc/apt/sources.list.d/ubuntu.sources')
parent = source.parent.lstat()
if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_mode & 0o022:
    fail('unsafe source directory')
keyring = Path('/usr/share/keyrings/ubuntu-archive-keyring.gpg')
checked_read(keyring, 1048576, 'keyring')
original, metadata = checked_read(source, 16384, 'source')
if any(byte > 126 or byte < 32 and byte not in (9, 10) for byte in original):
    fail('expected flat ASCII source')
allowed = {'types', 'uris', 'suites', 'components', 'signed-by', 'architectures', 'enabled'}
required = {'types', 'uris', 'suites', 'components', 'signed-by'}
seen_suites = set()
output = []
for section in re.split(r'\n[ \t]*\n', original.decode('ascii').strip('\n')):
    fields = {}
    for line in section.splitlines():
        if line.startswith('#'):
            continue
        name, separator, value = line.partition(':')
        name = name.lower()
        if not separator or name not in allowed or name in fields:
            fail('unsupported or duplicate source field')
        fields[name] = value.strip()
    if not fields:
        continue
    if not required <= fields.keys() or any(not value for value in fields.values()):
        fail('missing source field')
    for name, values in {'types': {'deb', 'deb-src'},
                         'suites': {'noble', 'noble-updates', 'noble-backports', 'noble-security'},
                         'components': {'main', 'restricted', 'universe', 'multiverse'}}.items():
        tokens = fields[name].split()
        if len(set(tokens)) != len(tokens) or not set(tokens) <= values:
            fail('unsupported or repeated package setting')
        fields[name] = ' '.join(tokens)
    if (fields['signed-by'] != '/usr/share/keyrings/ubuntu-archive-keyring.gpg'
            or fields.get('architectures', 'amd64') != 'amd64'
            or fields.get('enabled', 'yes') != 'yes'):
        fail('unsupported source trust or architecture')
    for suite in fields['suites'].split():
        if suite in seen_suites:
            fail('repeated suite across source sections')
        seen_suites.add(suite)
        host = 'security' if suite == 'noble-security' else 'archive'
        normalized = {**fields, 'uris': f'https://{host}.ubuntu.com/ubuntu/', 'suites': suite}
        output.append('\n'.join(f'{name}: {normalized[name.lower()]}' for name in
                      ('Types', 'URIs', 'Suites', 'Components', 'Signed-By', 'Architectures', 'Enabled')
                      if name.lower() in normalized))
if not output:
    fail('missing Ubuntu source')
canonical = ('\n\n'.join(output) + '\n').encode('ascii')
if len(canonical) > 16384:
    fail('normalized source exceeds size limit')
if canonical != original:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=source.parent, prefix='.ubuntu.sources-', delete=False) as stream:
            temporary = Path(stream.name)
            os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
            os.fchmod(stream.fileno(), stat.S_IMODE(metadata.st_mode))
            stream.write(canonical)
            stream.flush()
            os.fsync(stream.fileno())
        current, current_metadata = checked_read(source, 16384, 'source')
        if current != original or fingerprint(current_metadata) != fingerprint(metadata) or fingerprint(source.parent.lstat())[:5] != fingerprint(parent)[:5]:
            fail('source changed before replacement')
        os.replace(temporary, source)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    actual, final_metadata = checked_read(source, 16384, 'source')
    if actual != canonical or (final_metadata.st_uid, final_metadata.st_gid, final_metadata.st_mode) != (metadata.st_uid, metadata.st_gid, metadata.st_mode):
        fail('source write verification failed')
print('CI APT sources: official Ubuntu HTTPS archives')
PY
