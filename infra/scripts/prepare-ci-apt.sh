#!/usr/bin/env bash
# F211 T112: normalize package sources on disposable GitHub Ubuntu runners.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != true || "${RUNNER_OS:-}" != Linux || "${RUNNER_ENVIRONMENT:-}" != github-hosted ]]; then
  echo 'CI APT preparation requires a GitHub-hosted Linux runner' >&2
  exit 1
fi
sudo python3 - <<'PY'
from pathlib import Path
import hashlib
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
    repairable = (label == 'keyring' and stat.S_ISREG(before.st_mode)
                  and before.st_uid == before.st_gid == 0
                  and stat.S_IMODE(before.st_mode) == 0o777 and before.st_size == 3607)
    if not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_mode & 0o022 and not repairable or not 0 < before.st_size <= limit:
        fail(f'unsafe {label} metadata type={stat.S_IFMT(before.st_mode)} '
             f'uid={before.st_uid} gid={before.st_gid} '
             f'mode={stat.S_IMODE(before.st_mode):o} size={before.st_size}')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        if fingerprint(os.fstat(stream.fileno())) != fingerprint(before):
            fail('input changed while opening')
        data = stream.read(limit + 1)
        if len(data) != before.st_size or fingerprint(os.fstat(stream.fileno())) != fingerprint(before):
            fail('input changed while reading')
    # Ubuntu's official 2023.11.28.1build1 archive key; only its permissions may be repaired.
    if repairable and hashlib.sha256(data).hexdigest() != '80a36b0a6de2f69f49d2df75ef473ccde121e9e190b9ea01d20a4f63778d5c31':
        fail('unrecognized writable Ubuntu keyring')
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
key_parent = keyring.parent.lstat()
repair_parent = (stat.S_ISDIR(key_parent.st_mode) and key_parent.st_uid == key_parent.st_gid == 0
                 and stat.S_IMODE(key_parent.st_mode) == 0o777)
if not stat.S_ISDIR(key_parent.st_mode) or key_parent.st_uid != 0 or key_parent.st_mode & 0o022 and not repair_parent:
    fail(f'unsafe keyring-directory metadata type={stat.S_IFMT(key_parent.st_mode)} '
         f'uid={key_parent.st_uid} gid={key_parent.st_gid} '
         f'mode={stat.S_IMODE(key_parent.st_mode):o} size={key_parent.st_size}')
if repair_parent:
    for ancestor in (keyring.parent.parent, keyring.parent.parent.parent):
        value = ancestor.lstat()
        if not stat.S_ISDIR(value.st_mode) or value.st_uid != 0 or value.st_mode & 0o022:
            summaries = []
            for label, path in (('share', keyring.parent.parent), ('usr', keyring.parent.parent.parent), ('root', Path('/'))):
                metadata = path.lstat()
                summaries.append(f'{label} type={stat.S_IFMT(metadata.st_mode)} '
                                 f'uid={metadata.st_uid} gid={metadata.st_gid} '
                                 f'mode={stat.S_IMODE(metadata.st_mode):o} size={metadata.st_size}')
            fail('unsafe keyring ancestor; ' + '; '.join(summaries))
key_data, key_metadata = checked_read(keyring, 1048576, 'keyring')
if repair_parent and ((key_metadata.st_uid, key_metadata.st_gid, key_metadata.st_size) != (0, 0, 3607)
                      or stat.S_IMODE(key_metadata.st_mode) not in (0o644, 0o777)
                      or hashlib.sha256(key_data).hexdigest() != '80a36b0a6de2f69f49d2df75ef473ccde121e9e190b9ea01d20a4f63778d5c31'):
    fail('unrecognized keyring in writable directory')
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
if repair_parent:
    directory_fd = os.open(keyring.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if fingerprint(os.fstat(directory_fd)) != fingerprint(key_parent):
            fail('keyring directory changed while opening')
        os.fchmod(directory_fd, 0o755)
        os.fsync(directory_fd)
        secured = os.fstat(directory_fd)
        if ((secured.st_uid, secured.st_gid, stat.S_IMODE(secured.st_mode)) != (0, 0, 0o755)
                or fingerprint(keyring.parent.lstat()) != fingerprint(secured)):
            fail('keyring directory verification failed')
        key_parent = secured
    finally:
        os.close(directory_fd)
    for path, data, before, limit, label in ((keyring, key_data, key_metadata, 1048576, 'keyring'),
                                            (source, original, metadata, 16384, 'source')):
        current, actual_metadata = checked_read(path, limit, label)
        if current != data or fingerprint(actual_metadata) != fingerprint(before):
            fail('input changed while securing keyring directory')
if repair_parent or key_metadata.st_mode & 0o022:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=keyring.parent, prefix='.ubuntu-keyring-', delete=False) as stream:
            temporary = Path(stream.name)
            os.fchown(stream.fileno(), 0, 0)
            os.fchmod(stream.fileno(), 0o644)
            stream.write(key_data)
            stream.flush()
            os.fsync(stream.fileno())
        current, current_metadata = checked_read(keyring, 1048576, 'keyring')
        if current != key_data or fingerprint(current_metadata) != fingerprint(key_metadata) or fingerprint(keyring.parent.lstat())[:5] != fingerprint(key_parent)[:5]:
            fail('keyring changed before replacement')
        os.replace(temporary, keyring)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    actual, final_metadata = checked_read(keyring, 1048576, 'keyring')
    if actual != key_data or (final_metadata.st_uid, final_metadata.st_gid, stat.S_IMODE(final_metadata.st_mode)) != (0, 0, 0o644):
        fail('keyring write verification failed')
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
