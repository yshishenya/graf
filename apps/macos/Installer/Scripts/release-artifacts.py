#!/usr/bin/env python3
"""Local release fingerprints and retries. Trust remains in the existing validators."""
import argparse
from contextlib import contextmanager
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import subprocess
import tempfile
import time
from uuid import UUID

SCRIPTS = Path(__file__).resolve().parent
MACOS = SCRIPTS.parents[1]
ROOT = MACOS.parents[1]
STATE = MACOS / '.build'
SPARKLE_SHA = 'cb6fdbdc8884f15d62a616e79face92b08322410fd2d425edc6596ccbf4ba3b0'
# A word that may safely appear in a failure message: lowercase command words,
# never paths, option values or anything a tool printed.
SAFE_WORD = re.compile('[a-z][a-z0-9-]{0,20}')
# What each release tool was supposed to achieve, so a failure names the stage
# instead of only the command family.
RELEASE_STEPS = (
    ('gh api', 'the GitHub release state was not read'),
    ('gh release upload', 'the draft release asset was not uploaded'),
    ('xcrun notarytool', 'Apple notarization did not answer'),
    ('xcrun stapler', 'the notarization ticket was not stapled or validated'),
    ('xcrun', 'the Apple toolchain step did not complete'),
    ('codesign', 'the code signature was not verified'),
    ('spctl', 'the Gatekeeper assessment did not pass'),
    ('pkgutil', 'the installer package signature was not read'),
    ('ditto', 'the release archive was not produced'),
    ('git', 'the release checkout was not read'),
    ('swift', 'the Swift toolchain was not read'),
    ('env', 'the prepared public update did not pass its own validation'),
)


def invocation(args):
    """The tool and its safe subcommand words: never paths, values or output."""
    words = [str(value) for value in args]
    return ' '.join([words[0], *[word for word in words[1:] if SAFE_WORD.fullmatch(word)][:2]])


def failed_step(args):
    """The release step behind a failed invocation, in plain words."""
    name = invocation(args)
    for prefix, step in RELEASE_STEPS:
        if name.startswith(prefix):
            return step
    return 'the release step'


def command(*args, output=None):
    """Run one external release tool.

    External output may contain credentials, so a failure reports the tool, its
    safe subcommand words, the exit status, the stage that needed it and the
    retry path -- never the tool's own output.
    """
    try:
        result = subprocess.run([str(a) for a in args], cwd=ROOT, stdout=output or subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False,
                                timeout=45 if args[:2] == ('xcrun', 'notarytool') else None)
    except subprocess.TimeoutExpired:
        raise ValueError(f'{invocation(args)} did not answer within 45 seconds: {failed_step(args)}; '
                         'the saved request and every existing release file are kept, so the same '
                         'command can be resumed') from None
    if result.returncode:
        raise ValueError(f'{invocation(args)} exited with status {result.returncode}: {failed_step(args)}; '
                         'nothing was uploaded or published, all existing release state is kept, and '
                         'the same command can be retried') from None
    return result.stdout.decode().strip() if output is None else ''


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def fingerprint(path):
    path = Path(path)
    mode = path.lstat().st_mode
    result = {'mode': stat.S_IMODE(mode)}
    if stat.S_ISREG(mode):
        with path.open('rb') as stream:
            result.update(sha256=hashlib.file_digest(stream, 'sha256').hexdigest(), size=path.stat().st_size)
    elif stat.S_ISLNK(mode):
        result['link'] = os.readlink(path)
    elif stat.S_ISDIR(mode):
        result['tree'] = digest({p.name: fingerprint(p) for p in sorted(path.iterdir())})
    else:
        raise ValueError(f'unsupported artifact file type at {path}: expected a regular file, '
                         'a directory or a symlink')
    return result


def regular(path):
    value = fingerprint(path)
    if 'sha256' not in value:
        raise ValueError(f'{path} is not a regular file; release inputs and outputs must be regular files')
    return value


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.release-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_dir(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_json(path):
    regular(path)
    return json.loads(Path(path).read_text())


@contextmanager
def locked(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.mkdir()
    except FileExistsError:
        raise ValueError(f'another release attempt is in progress: {path} already exists; '
                         'verify the owner of that attempt before any recovery') from None
    try:
        yield
    finally:
        path.rmdir()


def stage_outputs(directory):
    return {p.name: fingerprint(p) for p in sorted(Path(directory).iterdir())
            if p.name != '.prepared.json'}


def sync_tree(directory):
    directory = Path(directory)
    for path in sorted(directory.rglob('*'), reverse=True):
        if path.is_file() and not path.is_symlink():
            with path.open('rb') as stream:
                os.fsync(stream.fileno())
        elif path.is_dir() and not path.is_symlink():
            sync_dir(path)
    sync_dir(directory)


def save_stage(directory, identity):
    directory = Path(directory)
    sync_tree(directory)
    atomic_json(directory / '.prepared.json',
                {'schema': 1, 'identity': identity, 'outputs': stage_outputs(directory)})


def stage_difference(saved, current):
    """The names that differ between a saved mapping and the current one."""
    names = [name for name in sorted(set(saved) | set(current)) if saved.get(name) != current.get(name)]
    return ', '.join(names) if names else 'none'


def check_stage(directory, identity):
    directory = Path(directory)
    saved = read_json(directory / '.prepared.json')
    if saved.get('schema') != 1 or saved.get('identity') != identity:
        differing = stage_difference(saved.get('identity') or {}, identity)
        raise ValueError(f'prepared release identity differs in: {differing}; keep the original version '
                         'unchanged, or prepare the new version under its own version number')
    if not saved.get('outputs') or saved['outputs'] != stage_outputs(directory):
        differing = stage_difference(saved.get('outputs') or {}, stage_outputs(directory))
        raise ValueError(f'prepared release output is incomplete or changed in: {differing}; '
                         're-prepare the release instead of publishing these files')
    # A retry also acknowledges a directory write that may have failed previously.
    sync_dir(directory)


def swift_key():
    return digest({'checkout': str(ROOT), 'swift': command('swift', '--version'),
                   'sdk': [command('xcrun', '--sdk', 'macosx', option) for option in
                           ('--show-sdk-path', '--show-sdk-version', '--show-sdk-build-version')],
                   'packages': {name: regular(MACOS / name) for name in ('Package.swift', 'Package.resolved')},
                   'args': ['-c', 'release', '--product', 'TwoBrainRecApp',
                            'arm64-apple-macosx14.5', 'x86_64-apple-macosx14.5']})


def clean_source(expected=None):
    source = command('git', 'rev-parse', 'HEAD')
    changes = command('git', 'status', '--porcelain', '--untracked-files=all')
    if not re.fullmatch('[0-9a-f]{40}', source):
        raise ValueError(f'git reported HEAD as {source!r}, which is not a commit SHA; '
                         'a public release needs a real commit, not a branch name or an empty checkout')
    if changes:
        first = changes.splitlines()[0]
        raise ValueError(f'the release checkout is dirty ({first}); commit or stash every change '
                         'before preparing a public release')
    if expected and source != expected:
        raise ValueError(f'the checkout is at {source} but this release was prepared for {expected}; '
                         'check out the prepared commit and retry')
    return source


def stage_identity(args):
    tools = [SCRIPTS / name for name in ('release-artifacts.py', 'prepare-app-update.sh',
             'release-signing-common.sh', 'sign-graf-app-update-local.sh')]
    tools += [SCRIPTS / 'verify-release-signing-custody.sh',
              SCRIPTS / 'derive-sparkle-public-key.swift',
              MACOS / 'Scripts/validate-app-updates.sh',
              MACOS / 'Scripts/validate-packaged-app-launch.sh']
    tools += [MACOS / '.build/artifacts/sparkle/Sparkle/bin' / name
              for name in ('generate_appcast', 'generate_keys', 'sign_update')]
    return {'version': args.version, 'source': command('git', 'rev-parse', 'HEAD'),
            'tag': f'v{args.version}', 'public': args.public,
            'app': fingerprint(args.app), 'previous': fingerprint(args.previous),
            'notes': regular(args.notes), 'url': args.url,
            'signing': regular(SCRIPTS.parent / 'UpdateSigningKey.json'),
            'tools': {p.name: regular(p) for p in tools}, 'sparkle': SPARKLE_SHA,
            'external': read_json(args.context) if args.context else None}


def release_for_tag(repo, tag):
    """Find a release by tag, including drafts.

    The by-tag endpoint is tried first, so published releases keep the exact
    behaviour they had before.  It answers 404 for a draft release, and a draft
    is visible only through the release list, so that list is the fallback while
    a release is still a draft.
    """
    try:
        release = json.loads(command('gh', 'api', f'repos/{repo}/releases/tags/{tag}'))
    except ValueError as error:
        # A draft release has no by-tag answer; the release list below is the fallback.
        lookup_error = error
    else:
        lookup_error = None
        if isinstance(release, dict) and release.get('tag_name') == tag:
            return release
    page = 1
    while True:
        rows = json.loads(command('gh', 'api', f'repos/{repo}/releases?per_page=100&page={page}'))
        for row in rows:
            if row.get('tag_name') == tag:
                return row
        if len(rows) < 100:
            cause = f'; the by-tag lookup failed with: {lookup_error}' if lookup_error else ''
            raise ValueError(f'release {tag} was not found in {repo} after reading every release page{cause}; '
                             'create the draft release for this tag before publishing to it')
        page += 1


def latest_app_release(repo, before=None, limit=40):
    """Find the newest release that actually publishes a GRAF app update.

    A server-only release carries no GRAF-<version>.zip, so the predecessor for
    a Sparkle update is not simply the previous tag.  Scanning is bounded and
    reads published releases only; drafts are never signing inputs.
    """
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('invalid release identity')
    if before is not None and not re.fullmatch(r'v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*', before):
        raise ValueError('invalid release identity')
    page = 1
    seen = 0
    while seen < limit:
        rows = json.loads(command('gh', 'api', f'repos/{repo}/releases?per_page=100&page={page}'))
        if not rows:
            break
        for row in rows:
            tag = row.get('tag_name', '')
            if row.get('draft') or not re.fullmatch(r'v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*', tag):
                continue
            if before is not None and tag >= before:
                continue
            seen += 1
            asset = f'GRAF-{tag.removeprefix("v")}.zip'
            for candidate in row.get('assets', []):
                if candidate.get('name') == asset and candidate.get('state') == 'uploaded':
                    return tag, asset
            if seen >= limit:
                break
        if len(rows) < 100:
            break
        page += 1
    return None


def release_snapshot(repo, tag, source=None, draft=None):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or not re.fullmatch(r'[A-Za-z0-9_.-]+', tag):
        raise ValueError(f'release identity {repo!r} / {tag!r} is not a GitHub owner/repo and a plain tag; '
                         'pass the repository and tag exactly as they appear on GitHub')
    release = release_for_tag(repo, tag)
    if release['tag_name'] != tag or not isinstance(release['id'], int):
        raise ValueError(f'the release found for {tag} in {repo} answers with tag {release["tag_name"]!r} '
                         f'and id {release["id"]!r}; refusing to publish to a release that is not this tag')
    if draft is not None and release['draft'] is not draft:
        state = 'a draft' if release['draft'] else 'published'
        wanted = 'a draft' if draft else 'published'
        raise ValueError(f'release {tag} is {state} but this step requires it to be {wanted}; '
                         'change the release state on GitHub before retrying')
    if source is not None:
        remote = json.loads(command('gh', 'api', f'repos/{repo}/commits/{tag}'))['sha']
        if remote != source:
            raise ValueError(f'release {tag} points at commit {remote} instead of the prepared source {source}; '
                             'the tag was moved, so stop and re-cut the release')
    identity = {'repository': repo, 'tag': tag, 'id': release['id'], 'source': source, 'draft': release['draft']}
    assets = []
    page = 1
    while True:
        rows = json.loads(command('gh', 'api', f'repos/{repo}/releases/{release["id"]}/assets?per_page=100&page={page}'))
        assets.extend(rows)
        if len(rows) < 100:
            return identity, assets
        page += 1


def one_asset(assets, name):
    matches = [a for a in assets if a['name'] == name]
    if len(matches) > 1:
        raise ValueError(f'{len(matches)} release assets are named {name}; a duplicated name cannot be '
                         'pinned to exact bytes, so remove the duplicate on the release first')
    return matches[0] if matches else None


def asset_identity(asset):
    if asset.get('state') != 'uploaded' or not isinstance(asset.get('id'), int):
        raise ValueError(f'release asset {asset.get("name")!r} is in state {asset.get("state")!r} without a '
                         'server ID; its upload never finished, so retry the upload instead of trusting it')
    return {key: asset.get(key) for key in ('id', 'name', 'size', 'digest', 'updated_at')}


def download_asset(repo, asset, destination):
    with Path(destination).open('xb') as stream:
        try:
            command('gh', 'api', f'repos/{repo}/releases/assets/{asset["id"]}',
                    '-H', 'Accept: application/octet-stream', output=stream)
        except ValueError as error:
            raise ValueError(f'release asset {asset.get("name")!r} (id {asset["id"]}) was not downloaded '
                             f'from {repo}: {error}') from None
        stream.flush()
        os.fsync(stream.fileno())


def cached_asset(repo, release, asset, cache, expected_digest=None):
    identity = {'release': release, 'asset': asset_identity(asset)}
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f'{digest([repo, release["tag"], asset["name"]])}.asset'
    record = path.with_suffix('.json')
    if path.is_symlink() or record.is_symlink():
        raise ValueError(f'cached input {path.name} or its record is a symlink; a cached input must be '
                         'a regular file created by this helper')
    if record.exists():
        saved = read_json(record)
        content = regular(path)
        if saved != {'identity': identity, 'content': content}:
            difference = 'identity' if saved.get('identity') != identity else 'bytes'
            raise ValueError(f'cached input {path.name} differs in its {difference} from the saved record '
                             f'{record.name}; establish whether the local cache or the remote asset changed '
                             'before removing either file')
    else:
        if path.exists():
            regular(path)  # An interrupted record write can leave an ordinary asset.
        with tempfile.TemporaryDirectory(dir=cache) as work:
            temporary = Path(work) / 'asset'
            download_asset(repo, asset, temporary)
            content = regular(temporary)
            verify_asset_bytes(asset, content, expected_digest)
            os.replace(temporary, path)
            atomic_json(record, {'identity': identity, 'content': content})
    verify_asset_bytes(asset, content, expected_digest)
    return path


def verify_asset_bytes(asset, content, expected_digest=None):
    name = asset.get('name')
    if content['size'] != asset['size']:
        raise ValueError(f'release asset {name!r} size differs: the downloaded file is {content["size"]} '
                         f'bytes but the release lists {asset["size"]} bytes; the download was discarded, '
                         'so retry it instead of using the partial file')
    remote_digest = asset.get('digest')
    if remote_digest and remote_digest != 'sha256:' + content['sha256']:
        raise ValueError(f'release asset {name!r} digest differs: the downloaded bytes are sha256 '
                         f'{content["sha256"]} but the release lists {remote_digest}; the download was '
                         'discarded, so retry it and report a persistent mismatch')
    if expected_digest and content['sha256'] != expected_digest:
        raise ValueError(f'release asset {name!r} digest differs from the pinned digest: the downloaded '
                         f'bytes are sha256 {content["sha256"]} but this release pins {expected_digest}; '
                         'do not replace the pinned input without an explicit decision')


def validate_context(context):
    snapshots = {}
    for label, expected in context['releases'].items():
        actual, rows = release_snapshot(expected['repository'], expected['tag'], expected['source'], expected['draft'])
        if actual != expected:
            differing = stage_difference(expected, actual)
            raise ValueError(f'the recorded {label} release identity changed in: {differing}; '
                             're-read the release on GitHub before publishing anything')
        snapshots[label] = rows
    for saved in context['inputs']:
        actual = one_asset(snapshots[saved['release']], saved['asset']['name'])
        if not actual or asset_identity(actual) != saved['asset']:
            raise ValueError(f'the {saved["release"]} release input {saved["asset"]["name"]!r} is no longer '
                             'the asset this release was prepared from; stop and re-prepare the release')
    return snapshots['candidate']


def remote_matches(repo, asset, path):
    """True only when the remote asset is byte-for-byte the local file."""
    asset_identity(asset)
    content = regular(path)
    if asset['size'] != content['size']:
        return False
    if asset.get('digest'):
        return asset['digest'] == 'sha256:' + content['sha256']
    with tempfile.TemporaryDirectory() as work:
        remote = Path(work) / 'asset'
        download_asset(repo, asset, remote)
        observed = regular(remote)
        return (observed['sha256'], observed['size']) == (content['sha256'], content['size'])


def upload_missing(context, files):
    release = context['releases']['candidate']
    repo, tag = release['repository'], release['tag']
    originals = {Path(p).name: regular(p) for p in files}
    if len(originals) != len(files):
        raise ValueError(f'a duplicate local release asset is listed: {len(files)} files but only '
                         f'{len(originals)} distinct names; each prepared release asset must be uploaded '
                         'exactly once')

    def preflight():
        rows = validate_context(context)
        missing = []
        for path in map(Path, files):
            if regular(path) != originals[path.name]:
                raise ValueError(f'the local release asset {path.name} changed while the upload was running; '
                                 'nothing was uploaded from the changed file, so re-prepare the release')
            remote = one_asset(rows, path.name)
            if remote is None:
                missing.append(path)
            elif not remote_matches(repo, remote, path):
                raise ValueError(f'release asset {path.name} already exists on {tag} with different bytes; '
                                 'this helper never overwrites a published asset, so resolve the conflict '
                                 'on the release first')
        return missing

    for path in preflight():
        if path not in preflight():
            continue
        try:
            command('gh', '--repo', repo, 'release', 'upload', tag, path)
        except ValueError as error:
            # An interrupted response is success only after exact remote readback.
            if path in preflight():
                raise ValueError(f'{error}; release asset {path.name} is still missing from {tag} after the '
                                 'failed upload, so nothing was acknowledged and the same upload can be '
                                 'retried') from None
        if path in preflight():
            raise ValueError(f'release asset {path.name} is still missing from {tag} after the upload '
                             'command reported success; nothing was acknowledged, so retry the upload')
    still_missing = preflight()
    if still_missing:
        raise ValueError(f'release {tag} is still missing {", ".join(p.name for p in still_missing)}; '
                         'nothing further was published, so rerun the upload for this prepared release')


def cache_inputs(args):
    # The caller names a staging directory that does not exist yet, and copying
    # the cached assets into it failed with a bare "no such file or directory"
    # after the whole app build had already succeeded.
    Path(args.output).mkdir(parents=True, exist_ok=True)
    context = {'releases': {}, 'inputs': []}
    for label, tag, source, draft in (('candidate', args.tag, args.source, True),
                                     ('previous', args.previous_tag, args.previous_source, False)):
        release, rows = release_snapshot(args.repo, tag, source, draft)
        context['releases'][label] = release
        names = [args.candidate, args.notes] if label == 'candidate' else [args.previous]
        for name in names:
            if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]*', name):
                raise ValueError(f'{name!r} is not a usable release asset name; use letters, digits, dots, '
                                 'dashes and underscores, starting with a letter or digit')
            asset = one_asset(rows, name)
            if asset is None:
                raise ValueError(f'the {label} release {tag} has no asset named {name}; upload that release '
                                 'input before preparing this release')
            path = cached_asset(args.repo, release, asset, STATE / 'release-inputs')
            shutil.copyfile(path, Path(args.output) / name)
            context['inputs'].append({'release': label, 'asset': asset_identity(asset), 'content': regular(path)})
    validate_context(context)
    atomic_json(Path(args.output) / 'release-inputs.json', context)


def cache_sparkle(output):
    repo = 'sparkle-project/Sparkle'
    tag = '2.9.4'
    release, rows = release_snapshot(repo, tag, draft=False)
    asset = one_asset(rows, 'Sparkle-for-Swift-Package-Manager.zip')
    if asset is None:
        raise ValueError(f'release {tag} of {repo} no longer offers Sparkle-for-Swift-Package-Manager.zip; '
                         f'the pinned Sparkle archive cannot be fetched, and its digest '
                         f'{SPARKLE_SHA} must not be replaced without a new decision')
    path = cached_asset(repo, release, asset, STATE / 'release-inputs', SPARKLE_SHA)
    shutil.copyfile(path, output)


def calver(value):
    if not re.fullmatch(r'[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*', value):
        raise ValueError(f'release version {value!r} is not CalVer YYYY.MM.DD.N with a positive build '
                         'number, for example 2026.09.17.2')
    year, month, day, _ = map(int, value.split('.'))
    try:
        date(year, month, day)
    except ValueError:
        raise ValueError(f'release version {value!r} contains the impossible date '
                         f'{year:04d}-{month:02d}-{day:02d}') from None
    return value


def request_id(value):
    try:
        canonical = str(UUID(value))
    except (AttributeError, TypeError, ValueError):
        raise ValueError(f'Apple request ID {value!r} is not a UUID; pass the exact ID that Apple '
                         'returned for this submission') from None
    if canonical != value.lower():
        raise ValueError(f'Apple request ID {value!r} is not in canonical form {canonical}; pass the exact '
                         'ID that Apple returned for this submission')
    return value


def validate_signed_build(app, pkg, version):
    app = Path(app)
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    if info['CFBundleVersion'] != version or info['CFBundleIdentifier'] != 'pro.2brain.graf':
        raise ValueError(f'the app {app} declares version {info["CFBundleVersion"]!r} and identifier '
                         f'{info["CFBundleIdentifier"]!r}, but this release needs version {version!r} and '
                         'identifier pro.2brain.graf; rebuild the app for this version')
    command('codesign', '--verify', '--deep', '--strict', app)
    try:
        signature = subprocess.run(['codesign', '-dv', '--verbose=4', str(app)],
                                   capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        raise ValueError(f'codesign could not read the signature of {app} (exit status '
                         f'{error.returncode}); sign the app with the Developer ID Application identity '
                         'before writing a public build receipt') from None
    authority = 'Authority=Developer ID Application:' in signature.stderr
    team = 'TeamIdentifier=94N8HYG672' in signature.stderr
    if not authority or not team:
        missing = ', '.join(part for part, found in (('the Developer ID Application authority', authority),
                                                     ('team identifier 94N8HYG672', team)) if not found)
        raise ValueError(f'the app {app} is not signed by the trusted GRAF Developer ID: missing {missing}; '
                         'rebuild it with the release signing identity')
    package_signature = command('pkgutil', '--check-signature', pkg)
    if 'Developer ID Installer:' not in package_signature or '(94N8HYG672)' not in package_signature:
        raise ValueError(f'the installer package {pkg} is not signed by the trusted GRAF Developer ID '
                         'Installer identity 94N8HYG672; re-sign the package before publishing it')


def receipt_source(pkg):
    """Return the source commit recorded by the build receipt for this package."""
    receipt = read_json(str(pkg) + '.build.json')
    source = receipt.get('source')
    if not isinstance(source, str) or not re.fullmatch('[0-9a-f]{40}', source):
        raise ValueError('build receipt does not name a source commit')
    if receipt.get('tag') != 'v' + str(receipt.get('version')):
        raise ValueError('invalid public build receipt')
    return source


def build_receipt(args):
    calver(args.version)
    source = clean_source(args.source)
    validate_signed_build(args.app, args.pkg, args.version)
    atomic_json(Path(str(args.pkg) + '.build.json'), {
        'schema': 1, 'source': source, 'tag': f'v{args.version}', 'version': args.version,
        'build_key': args.key, 'app': fingerprint(args.app), 'pkg': regular(args.pkg)})


def notarize_jobs(directory, profile, recover):
    directory = Path(directory)
    state_path = directory / 'requests.json'
    state = read_json(state_path)
    if set(state['inputs']) != {'zip', 'pkg'} or not set(state['jobs']) <= {'zip', 'pkg'}:
        raise ValueError(f'the saved notary attempt {state_path} describes inputs {sorted(state["inputs"])} '
                         f'and jobs {sorted(state["jobs"])} instead of exactly one zip and one pkg '
                         'submission; recover the Apple requests for this build before retrying')
    for kind, job in state['jobs'].items():
        if job['status'] not in ('submitting', 'submitted', 'Accepted'):
            raise ValueError(f'the saved {kind} notary job has status {job["status"]!r}, which is not a '
                             f'state this helper writes; inspect {state_path} before retrying')
        if job.get('id'):
            request_id(job['id'])
        elif job['status'] != 'submitting':
            raise ValueError(f'the saved {kind} notary job is {job["status"]!r} without an Apple request ID; '
                             f'pass the ID that submitted these exact bytes as --recover {kind}=<ID>')
    for kind in ('zip', 'pkg'):
        original = directory / f'submitted.{kind}'
        if regular(original) != state['inputs'][kind]:
            raise ValueError(f'the saved {original.name} no longer matches the bytes that were submitted '
                             f'(sha256 {state["inputs"][kind]["sha256"]}); restore the original file or '
                             'notarize a new build instead of resubmitting changed bytes')
        job = state['jobs'].get(kind)
        if job is None:
            job = state['jobs'][kind] = {'status': 'submitting'}
            atomic_json(state_path, state)  # Never submit without durable intent.
            try:
                answer = json.loads(command('xcrun', 'notarytool', 'submit', original,
                                            '--keychain-profile', profile, '--output-format', 'json'))
            except ValueError as error:
                raise ValueError(f'the {kind} submission did not complete: {error}; the durable '
                                 f'"submitting" intent is kept, so pass the Apple request ID as '
                                 f'--recover {kind}=<ID> once it is known and rerun') from None
            identifier = request_id(answer['id'])
            job.update(id=identifier, status='submitted')
            atomic_json(state_path, state)
        elif not job.get('id'):
            identifier = recover.get(kind)
            if not identifier:
                raise ValueError(f'the {kind} submission is ambiguous: it started but no Apple request ID '
                                 'was saved, so no status can be read; recover the digest-bound Apple ID '
                                 f'of the request that uploaded these exact bytes and pass it as '
                                 f'--recover {kind}=<ID> before any retry')
            request_id(identifier)
            try:
                log = json.loads(command('xcrun', 'notarytool', 'log', identifier, '--keychain-profile', profile))
            except ValueError as error:
                raise ValueError(f'the Apple log for the recovered {kind} request {identifier} could not be '
                                 f'read: {error}; without it the request cannot be bound to these bytes') from None
            if log.get('jobId') != identifier or log.get('sha256') != state['inputs'][kind]['sha256']:
                raise ValueError(f'the Apple log for {identifier} reports job {log.get("jobId")!r} and digest '
                                 f'{log.get("sha256")!r}, which do not bind the submitted {kind} digest '
                                 f'{state["inputs"][kind]["sha256"]}; pass the request ID that submitted '
                                 'these exact bytes')
            job.update(id=identifier, status='submitted')
            atomic_json(state_path, state)
    # Both submissions have durable IDs. Poll together; no long, opaque wait command.
    deadline = time.monotonic() + 45 * 60
    while True:
        pending = []
        for kind, job in state['jobs'].items():
            if job['status'] == 'Accepted':
                continue
            try:
                answer = json.loads(command('xcrun', 'notarytool', 'info', job['id'],
                                            '--keychain-profile', profile, '--output-format', 'json'))
            except ValueError as error:
                raise ValueError(f'the status of the submitted {kind} request {job["id"]} could not be read: '
                                 f'{error}; the request is saved, so rerun the same command to keep '
                                 'polling') from None
            if answer.get('id') != job['id']:
                raise ValueError(f'Apple answered about request {answer.get("id")!r} while {job["id"]} was '
                                 f'asked about the {kind} submission; stop and confirm the request IDs '
                                 'before retrying')
            if answer.get('status') == 'In Progress':
                pending.append(kind)
            elif answer.get('status') == 'Accepted':
                job['status'] = 'Accepted'
                atomic_json(state_path, state)
            else:
                raise ValueError(f'Apple has not accepted the {kind} submission {job["id"]}: status '
                                 f'{answer.get("status")!r}; the request is kept, so read its Apple log '
                                 'before any resubmission')
        if not pending:
            break
        if time.monotonic() >= deadline:
            raise ValueError(f'Apple has not accepted the {", ".join(pending)} submission within 45 minutes; '
                             'the saved request IDs are kept, so rerun the same command to keep polling or '
                             'read the Apple log')
        print(f'notary=waiting inputs={",".join(pending)}; interruption is resumable', flush=True)
        time.sleep(10)
    return state


def validate_notarized(app, pkg):
    """The notarized app and package must pass signature, staple and Gatekeeper checks."""
    try:
        command('codesign', '--verify', '--deep', '--strict', app)
    except ValueError as error:
        raise ValueError(f'the notarized app {app} did not verify as signed: {error}') from None
    for path, kind in ((app, 'execute'), (pkg, 'install')):
        for check in (('xcrun', 'stapler', 'validate', path), ('spctl', '--assess', '--type', kind, '--verbose=4', path)):
            try:
                command(*check)
            except ValueError as error:
                raise ValueError(f'the notarized {kind} artifact {path} did not pass {" ".join(check[:2])}: '
                                 f'{error}') from None


def notarize(args):
    with locked(STATE / '.graf-installer.lock'):
        receipt_path = str(args.pkg) + '.build.json'
        if not Path(receipt_path).exists():
            raise ValueError(f'there is no build receipt at {receipt_path}; notarization only accepts the '
                             'exact artifacts of a recorded build, so build this version with '
                             'build-local-installer.sh first')
        receipt = read_json(receipt_path)
        calver(receipt['version'])
        clean_source(receipt['source'])
        if receipt['schema'] != 1 or receipt['tag'] != 'v' + receipt['version']:
            raise ValueError(f'the public build receipt {str(args.pkg) + ".build.json"} has schema '
                             f'{receipt["schema"]!r} and tag {receipt["tag"]!r}, but this helper writes '
                             'schema 1 with tag v<version>; rebuild the app with build-local-installer.sh '
                             'instead of editing the receipt')
        if fingerprint(args.app) != receipt['app'] or regular(args.pkg) != receipt['pkg']:
            changed = ', '.join(part for part, same in
                                ((f'the app {args.app}', fingerprint(args.app) == receipt['app']),
                                 (f'the package {args.pkg}', regular(args.pkg) == receipt['pkg'])) if not same)
            raise ValueError(f'the build receipt does not bind {changed}: the bytes differ from the build '
                             'that was recorded, so notarize the exact artifacts of that build')
        validate_signed_build(args.app, args.pkg, receipt['version'])
        directory = STATE / 'notary' / f'{receipt["version"]}-{receipt["source"]}'
        if directory.exists():
            if read_json(directory / 'build.json') != receipt:
                raise ValueError(f'the saved notary attempt {directory} belongs to another build of '
                                 f'{receipt["version"]}; finish or discard that attempt before starting a '
                                 'new one for these artifacts')
        else:
            directory.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=directory.parent) as temporary:
                work = Path(temporary) / 'attempt'
                work.mkdir()
                # This stored copy is the evidence of the exact submitted bytes,
                # and the stapled final app is built from it rather than from the
                # mutable build output. It is deliberately a real copy, not a
                # link: a later rebuild of the same path must not be able to
                # change what was notarized.
                command('ditto', args.app, work / 'GRAF.app')
                shutil.copyfile(args.pkg, work / 'submitted.pkg')
                if fingerprint(work / 'GRAF.app') != receipt['app']:
                    raise ValueError(f'the copy of {args.app} that was staged for notarization no longer '
                                     'matches the recorded build; the app changed while the attempt was '
                                     'prepared, so rebuild and notarize again')
                command('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', work / 'GRAF.app', work / 'submitted.zip')
                inputs = {kind: regular(work / f'submitted.{kind}') for kind in ('zip', 'pkg')}
                if inputs['pkg']['sha256'] != receipt['pkg']['sha256']:
                    raise ValueError(f'the copy of {args.pkg} that was staged for notarization has sha256 '
                                     f'{inputs["pkg"]["sha256"]} instead of the recorded '
                                     f'{receipt["pkg"]["sha256"]}; the package changed while the attempt was '
                                     'prepared, so rebuild and notarize again')
                atomic_json(work / 'build.json', receipt)
                atomic_json(work / 'requests.json', {'inputs': inputs, 'jobs': {}})
                sync_tree(work)
                os.replace(work, directory)
                sync_dir(directory.parent)
        if fingerprint(directory / 'GRAF.app') != receipt['app']:
            raise ValueError(f'the app saved in the notary attempt {directory} differs from the build '
                             'receipt; notarization must restart from the recorded build, so discard this '
                             'attempt explicitly')
        sync_dir(directory.parent)
        recover = {}
        for value in args.recover:
            kind, separator, identifier = value.partition('=')
            if kind not in ('zip', 'pkg') or not separator or kind in recover:
                raise ValueError(f'recovery {value!r} is not usable; pass the Apple request ID exactly once '
                                 'per input, as --recover zip=<ID> or --recover pkg=<ID>')
            recover[kind] = identifier
        state = notarize_jobs(directory, args.profile, recover)
        identity = {'build': receipt, 'requests': state}
        final = directory / 'final'
        app, pkg = final / 'GRAF.app', final / f'GRAF-{receipt["version"]}.pkg'
        if final.exists():
            check_stage(final, identity)
            validate_notarized(app, pkg)
        else:
            with tempfile.TemporaryDirectory(dir=directory) as temporary:
                work = Path(temporary) / 'final'
                work.mkdir()
                command('ditto', directory / 'GRAF.app', work / 'GRAF.app')
                shutil.copyfile(directory / 'submitted.pkg', work / pkg.name)
                for path in (work / 'GRAF.app', work / pkg.name):
                    command('xcrun', 'stapler', 'staple', path)
                validate_notarized(work / 'GRAF.app', work / pkg.name)
                command('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', work / 'GRAF.app',
                        work / f'GRAF-{receipt["version"]}-candidate.zip')
                clean_source(receipt['source'])
                save_stage(work, identity)
                os.replace(work, final)
        sync_dir(directory)
        clean_source(receipt['source'])
        print(f'notary=Accepted final={final} published=no')


def upload_prepared(args):
    context = read_json(args.context)
    release = context['releases']['candidate']
    directory = Path(args.files[0]).parent
    if directory.resolve() != (STATE / 'updates').resolve():
        raise ValueError(f'the upload takes files from {directory} but this release prepares them in '
                         f'{STATE / "updates"}; prepare the update before uploading it')
    version = calver(release['tag'].removeprefix('v'))
    expected_names = {f'GRAF-{version}.zip', 'graf-appcast.xml', f'GRAF-{version}.sha256',
                      f'GRAF-{version}-signing-attestation.json'}
    given_names = {Path(p).name for p in args.files}
    if given_names != expected_names or any(Path(p).parent != directory for p in args.files):
        missing = ', '.join(sorted(expected_names - given_names)) or 'none'
        unexpected = ', '.join(sorted(given_names - expected_names)) or 'none'
        raise ValueError(f'the upload must contain the exact four prepared assets of {version} from one '
                         f'directory: missing {missing}; unexpected {unexpected}')
    clean_source(release['source'])
    origin = command('git', 'remote', 'get-url', 'origin').removesuffix('.git')
    allowed = (f'https://github.com/{release["repository"]}',
               f'git@github.com:{release["repository"]}',
               f'ssh://git@github.com/{release["repository"]}')
    if origin not in allowed:
        raise ValueError(f'the upload targets {release["repository"]} but this checkout has origin '
                         f'{origin}; publish from a checkout of that repository')
    info = plistlib.loads((Path(args.app) / 'Contents/Info.plist').read_bytes())
    url = info['SUFeedURL'].removesuffix('/graf-appcast.xml')
    # Reuse the public validation path, including fresh Keychain and both signatures.
    # Verify-only cannot create, sign or replace a missing/different prepared version.
    try:
        command('env', 'GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1', 'GRAF_REQUIRE_RELEASE_PROVENANCE=1',
                'GRAF_RELEASE_SIGNING_MODE=keychain', f'GRAF_VERSION={version}',
                f'GRAF_UPDATE_APP_BUNDLE={args.app}', f'GRAF_PREVIOUS_APP_BUNDLE={args.previous}',
                f'GRAF_UPDATE_RELEASE_NOTES={args.notes}', f'GRAF_UPDATE_DOWNLOAD_BASE_URL={url}',
                f'GRAF_RELEASE_INPUT_CONTEXT={args.context}',
                f'GRAF_RELEASE_SIGNING_KEYCHAIN_ATTESTATION={directory / ("GRAF-" + version + "-signing-attestation.json")}',
                SCRIPTS / 'prepare-app-update.sh', '--verify-only')
    except ValueError as error:
        raise ValueError(f'the prepared update for {version} did not pass its own public validation: '
                         f'{error}; fix the prepared inputs and re-prepare the release instead of '
                         'uploading it') from None
    with locked(STATE / '.graf-update-staging.lock'):
        identity_args = argparse.Namespace(app=args.app, previous=args.previous, notes=args.notes,
                                           version=version, url=url, public='1', context=args.context)
        identity = stage_identity(identity_args)
        check_stage(directory, identity)
        for architecture in ('arm64', 'x86_64'):
            try:
                command(MACOS / 'Scripts/validate-packaged-app-launch.sh', args.app, '5', architecture)
            except ValueError as error:
                raise ValueError(f'the packaged app did not start cleanly for {architecture}: {error}; '
                                 'the prepared update is not publishable') from None
        check_stage(directory, stage_identity(identity_args))
        clean_source(release['source'])
        upload_missing(context, args.files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('swift-key')
    sub.add_parser('source').add_argument('--expected')
    identity = sub.add_parser('stage-identity')
    for name in ('app', 'previous', 'notes', 'version', 'url', 'public'):
        identity.add_argument('--' + name, required=True)
    identity.add_argument('--context')
    for action in ('stage-save', 'stage-check'):
        stage = sub.add_parser(action)
        stage.add_argument('directory')
        stage.add_argument('identity')
    sub.add_parser('sync-dir').add_argument('directory')
    receipt = sub.add_parser('build-receipt')
    for name in ('source', 'version', 'key', 'app', 'pkg'):
        receipt.add_argument('--' + name, required=True)
    sub.add_parser('receipt-source').add_argument('pkg')
    previous = sub.add_parser('latest-app-release')
    previous.add_argument('--repo', required=True)
    previous.add_argument('--before', default=None)
    inputs = sub.add_parser('cache-inputs')
    for name in ('repo', 'tag', 'source', 'previous-tag', 'previous-source', 'candidate', 'previous', 'notes', 'output'):
        inputs.add_argument('--' + name, required=True)
    sub.add_parser('cache-sparkle').add_argument('output')
    upload = sub.add_parser('upload')
    for name in ('app', 'previous', 'notes'):
        upload.add_argument('--' + name, required=True)
    upload.add_argument('context')
    upload.add_argument('files', nargs=4)
    notary = sub.add_parser('notarize')
    notary.add_argument('--app', required=True)
    notary.add_argument('--pkg', required=True)
    notary.add_argument('--profile', default='graf-notary')
    notary.add_argument('--recover', action='append', default=[])
    args = parser.parse_args()
    if args.action == 'swift-key':
        print(swift_key())
    elif args.action == 'source':
        print(clean_source(args.expected))
    elif args.action == 'stage-identity':
        print(json.dumps(stage_identity(args), sort_keys=True))
    elif args.action in ('stage-save', 'stage-check'):
        (save_stage if args.action == 'stage-save' else check_stage)(args.directory, read_json(args.identity))
    elif args.action == 'sync-dir':
        sync_dir(args.directory)
    elif args.action == 'build-receipt':
        build_receipt(args)
    elif args.action == 'receipt-source':
        print(receipt_source(args.pkg))
    elif args.action == 'latest-app-release':
        found = latest_app_release(args.repo, args.before)
        if found is None:
            raise SystemExit('release-artifacts: no earlier release publishes an app update')
        print(f'tag={found[0]}\nasset={found[1]}')
    elif args.action == 'cache-inputs':
        cache_inputs(args)
    elif args.action == 'cache-sparkle':
        cache_sparkle(args.output)
    elif args.action == 'upload':
        upload_prepared(args)
    elif args.action == 'notarize':
        notarize(args)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f'release-artifacts: {error}') from None
