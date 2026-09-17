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


def command(*args, output=None):
    try:
        result = subprocess.run([str(a) for a in args], cwd=ROOT, stdout=output or subprocess.PIPE,
                                stderr=subprocess.PIPE, check=False,
                                timeout=45 if args[:2] == ('xcrun', 'notarytool') else None)
    except subprocess.TimeoutExpired:
        raise ValueError(f'{args[0]} timed out; existing release state retained') from None
    if result.returncode:
        # External output may contain credentials. Report only the command family.
        raise ValueError(f'{args[0]} failed; no release stage acknowledged')
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
        raise ValueError('unsupported artifact file type')
    return result


def regular(path):
    value = fingerprint(path)
    if 'sha256' not in value:
        raise ValueError('artifact must be a regular file')
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
        raise ValueError('another release attempt is in progress; verify the owner before recovery') from None
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


def check_stage(directory, identity):
    directory = Path(directory)
    saved = read_json(directory / '.prepared.json')
    if saved.get('schema') != 1 or saved.get('identity') != identity:
        raise ValueError('prepared release identity differs; keep the original version unchanged')
    if not saved.get('outputs') or saved['outputs'] != stage_outputs(directory):
        raise ValueError('prepared release output is incomplete or changed')
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
    if not re.fullmatch('[0-9a-f]{40}', source) or command('git', 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('public release requires clean exact source')
    if expected and source != expected:
        raise ValueError('release source changed')
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

    The by-tag endpoint answers 404 for a draft release, so the release list is
    the only reliable lookup while the release is still a draft.  Published
    releases are still resolvable through the by-tag endpoint as a fallback.
    """
    page = 1
    while True:
        rows = json.loads(command('gh', 'api', f'repos/{repo}/releases?per_page=100&page={page}'))
        for row in rows:
            if row.get('tag_name') == tag:
                return row
        if len(rows) < 100:
            break
        page += 1
    return json.loads(command('gh', 'api', f'repos/{repo}/releases/tags/{tag}'))


def release_snapshot(repo, tag, source=None, draft=None):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or not re.fullmatch(r'[A-Za-z0-9_.-]+', tag):
        raise ValueError('invalid release identity')
    release = release_for_tag(repo, tag)
    if release['tag_name'] != tag or not isinstance(release['id'], int):
        raise ValueError('release identity differs')
    if draft is not None and release['draft'] is not draft:
        raise ValueError('release draft state differs')
    if source is not None:
        if json.loads(command('gh', 'api', f'repos/{repo}/commits/{tag}'))['sha'] != source:
            raise ValueError('remote source differs')
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
        raise ValueError('duplicate remote release asset')
    return matches[0] if matches else None


def asset_identity(asset):
    if asset.get('state') != 'uploaded' or not isinstance(asset.get('id'), int):
        raise ValueError('remote asset upload is incomplete')
    return {key: asset.get(key) for key in ('id', 'name', 'size', 'digest', 'updated_at')}


def download_asset(repo, asset, destination):
    with Path(destination).open('xb') as stream:
        command('gh', 'api', f'repos/{repo}/releases/assets/{asset["id"]}',
                '-H', 'Accept: application/octet-stream', output=stream)
        stream.flush()
        os.fsync(stream.fileno())


def cached_asset(repo, release, asset, cache, expected_digest=None):
    identity = {'release': release, 'asset': asset_identity(asset)}
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f'{digest([repo, release["tag"], asset["name"]])}.asset'
    record = path.with_suffix('.json')
    if path.is_symlink() or record.is_symlink():
        raise ValueError('cached input must not be a symlink')
    if record.exists():
        saved = read_json(record)
        content = regular(path)
        if saved != {'identity': identity, 'content': content}:
            raise ValueError('cached input identity or bytes differ')
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
    if content['size'] != asset['size']:
        raise ValueError('remote asset size differs')
    remote_digest = asset.get('digest')
    if remote_digest and remote_digest != 'sha256:' + content['sha256']:
        raise ValueError('remote asset digest differs')
    if expected_digest and content['sha256'] != expected_digest:
        raise ValueError('pinned asset digest differs')


def validate_context(context):
    snapshots = {}
    for label, expected in context['releases'].items():
        actual, rows = release_snapshot(expected['repository'], expected['tag'], expected['source'], expected['draft'])
        if actual != expected:
            raise ValueError('release identity changed')
        snapshots[label] = rows
    for saved in context['inputs']:
        actual = one_asset(snapshots[saved['release']], saved['asset']['name'])
        if not actual or asset_identity(actual) != saved['asset']:
            raise ValueError('release input asset changed')
    return snapshots['candidate']


def remote_matches(repo, asset, path):
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
        raise ValueError('duplicate local release asset')

    def preflight():
        rows = validate_context(context)
        missing = []
        for path in map(Path, files):
            if regular(path) != originals[path.name]:
                raise ValueError('local upload bytes changed')
            remote = one_asset(rows, path.name)
            if remote is None:
                missing.append(path)
            elif not remote_matches(repo, remote, path):
                raise ValueError('remote asset conflict; no overwrite is allowed')
        return missing

    for path in preflight():
        if path not in preflight():
            continue
        try:
            command('gh', '--repo', repo, 'release', 'upload', tag, path)
        except ValueError:
            # An interrupted response is success only after exact remote readback.
            if path in preflight():
                raise
        if path in preflight():
            raise ValueError('uploaded release asset is still missing')
    if preflight():
        raise ValueError('release upload is incomplete')


def cache_inputs(args):
    context = {'releases': {}, 'inputs': []}
    for label, tag, source, draft in (('candidate', args.tag, args.source, True),
                                     ('previous', args.previous_tag, args.previous_source, False)):
        release, rows = release_snapshot(args.repo, tag, source, draft)
        context['releases'][label] = release
        names = [args.candidate, args.notes] if label == 'candidate' else [args.previous]
        for name in names:
            if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]*', name):
                raise ValueError('invalid input asset name')
            asset = one_asset(rows, name)
            if asset is None:
                raise ValueError('required release input is missing')
            path = cached_asset(args.repo, release, asset, STATE / 'release-inputs')
            shutil.copyfile(path, Path(args.output) / name)
            context['inputs'].append({'release': label, 'asset': asset_identity(asset), 'content': regular(path)})
    validate_context(context)
    atomic_json(Path(args.output) / 'release-inputs.json', context)


def cache_sparkle(output):
    repo = 'sparkle-project/Sparkle'
    release, rows = release_snapshot(repo, '2.9.4', draft=False)
    asset = one_asset(rows, 'Sparkle-for-Swift-Package-Manager.zip')
    if asset is None:
        raise ValueError('pinned Sparkle archive is missing')
    path = cached_asset(repo, release, asset, STATE / 'release-inputs', SPARKLE_SHA)
    shutil.copyfile(path, output)


def calver(value):
    if not re.fullmatch(r'[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*', value):
        raise ValueError('invalid release version')
    year, month, day, _ = map(int, value.split('.'))
    date(year, month, day)
    return value


def request_id(value):
    if str(UUID(value)) != value.lower():
        raise ValueError('invalid Apple request ID')
    return value


def validate_signed_build(app, pkg, version):
    app = Path(app)
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    if info['CFBundleVersion'] != version or info['CFBundleIdentifier'] != 'pro.2brain.graf':
        raise ValueError('build product identity differs')
    command('codesign', '--verify', '--deep', '--strict', app)
    signature = subprocess.run(['codesign', '-dv', '--verbose=4', str(app)], capture_output=True, text=True, check=True)
    if ('Authority=Developer ID Application:' not in signature.stderr
            or 'TeamIdentifier=94N8HYG672' not in signature.stderr):
        raise ValueError('build does not have the trusted Developer ID identity')
    package_signature = command('pkgutil', '--check-signature', pkg)
    if 'Developer ID Installer:' not in package_signature or '(94N8HYG672)' not in package_signature:
        raise ValueError('package does not have the trusted Developer ID Installer identity')


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
        raise ValueError('invalid notary input set')
    for job in state['jobs'].values():
        if job['status'] not in ('submitting', 'submitted', 'Accepted'):
            raise ValueError('invalid saved notary status')
        if job.get('id'):
            request_id(job['id'])
        elif job['status'] != 'submitting':
            raise ValueError('saved notary status requires a request ID')
    for kind in ('zip', 'pkg'):
        original = directory / f'submitted.{kind}'
        if regular(original) != state['inputs'][kind]:
            raise ValueError('notary submitted bytes changed')
        job = state['jobs'].get(kind)
        if job is None:
            job = state['jobs'][kind] = {'status': 'submitting'}
            atomic_json(state_path, state)  # Never submit without durable intent.
            answer = json.loads(command('xcrun', 'notarytool', 'submit', original,
                                        '--keychain-profile', profile, '--output-format', 'json'))
            identifier = request_id(answer['id'])
            job.update(id=identifier, status='submitted')
            atomic_json(state_path, state)
        elif not job.get('id'):
            identifier = recover.get(kind)
            if not identifier:
                raise ValueError(f'{kind} submission is ambiguous; recover its digest-bound Apple ID before retry')
            request_id(identifier)
            log = json.loads(command('xcrun', 'notarytool', 'log', identifier, '--keychain-profile', profile))
            if log.get('jobId') != identifier or log.get('sha256') != state['inputs'][kind]['sha256']:
                raise ValueError('Apple recovery ID does not bind submitted digest')
            job.update(id=identifier, status='submitted')
            atomic_json(state_path, state)
    # Both submissions have durable IDs. Poll together; no long, opaque wait command.
    deadline = time.monotonic() + 45 * 60
    while True:
        pending = []
        for kind, job in state['jobs'].items():
            if job['status'] == 'Accepted':
                continue
            answer = json.loads(command('xcrun', 'notarytool', 'info', job['id'],
                                        '--keychain-profile', profile, '--output-format', 'json'))
            if answer.get('id') != job['id']:
                raise ValueError('Apple response request ID differs')
            if answer.get('status') == 'In Progress':
                pending.append(kind)
            elif answer.get('status') == 'Accepted':
                job['status'] = 'Accepted'
                atomic_json(state_path, state)
            else:
                raise ValueError('Apple has not accepted this submission; existing request retained')
        if not pending:
            break
        if time.monotonic() >= deadline:
            raise ValueError('Apple has not accepted this submission within 45 minutes; resume the same request')
        print(f'notary=waiting inputs={",".join(pending)}; interruption is resumable', flush=True)
        time.sleep(10)
    return state


def validate_notarized(app, pkg):
    command('codesign', '--verify', '--deep', '--strict', app)
    for path, kind in ((app, 'execute'), (pkg, 'install')):
        command('xcrun', 'stapler', 'validate', path)
        command('spctl', '--assess', '--type', kind, '--verbose=4', path)


def notarize(args):
    with locked(STATE / '.graf-installer.lock'):
        receipt = read_json(str(args.pkg) + '.build.json')
        calver(receipt['version'])
        clean_source(receipt['source'])
        if receipt['schema'] != 1 or receipt['tag'] != 'v' + receipt['version']:
            raise ValueError('invalid public build receipt')
        if fingerprint(args.app) != receipt['app'] or regular(args.pkg) != receipt['pkg']:
            raise ValueError('build receipt does not bind the current app/package')
        validate_signed_build(args.app, args.pkg, receipt['version'])
        directory = STATE / 'notary' / f'{receipt["version"]}-{receipt["source"]}'
        if directory.exists():
            if read_json(directory / 'build.json') != receipt:
                raise ValueError('notary attempt belongs to another build')
        else:
            directory.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=directory.parent) as temporary:
                work = Path(temporary) / 'attempt'
                work.mkdir()
                command('ditto', args.app, work / 'GRAF.app')
                shutil.copyfile(args.pkg, work / 'submitted.pkg')
                if fingerprint(work / 'GRAF.app') != receipt['app']:
                    raise ValueError('app changed while creating notary input')
                command('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', work / 'GRAF.app', work / 'submitted.zip')
                inputs = {kind: regular(work / f'submitted.{kind}') for kind in ('zip', 'pkg')}
                if inputs['pkg']['sha256'] != receipt['pkg']['sha256']:
                    raise ValueError('package changed while creating notary input')
                atomic_json(work / 'build.json', receipt)
                atomic_json(work / 'requests.json', {'inputs': inputs, 'jobs': {}})
                sync_tree(work)
                os.replace(work, directory)
                sync_dir(directory.parent)
        if fingerprint(directory / 'GRAF.app') != receipt['app']:
            raise ValueError('saved notary app differs from the original build')
        sync_dir(directory.parent)
        recover = {}
        for value in args.recover:
            kind, separator, identifier = value.partition('=')
            if kind not in ('zip', 'pkg') or not separator or kind in recover:
                raise ValueError('recovery must be zip=ID or pkg=ID, once per input')
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
        raise ValueError('upload must use the prepared update directory')
    version = calver(release['tag'].removeprefix('v'))
    expected_names = {f'GRAF-{version}.zip', 'graf-appcast.xml', f'GRAF-{version}.sha256',
                      f'GRAF-{version}-signing-attestation.json'}
    if {Path(p).name for p in args.files} != expected_names or any(Path(p).parent != directory for p in args.files):
        raise ValueError('upload must contain the exact four prepared assets')
    clean_source(release['source'])
    origin = command('git', 'remote', 'get-url', 'origin').removesuffix('.git')
    if origin not in (f'https://github.com/{release["repository"]}',
                      f'git@github.com:{release["repository"]}',
                      f'ssh://git@github.com/{release["repository"]}'):
        raise ValueError('upload repository differs from origin')
    info = plistlib.loads((Path(args.app) / 'Contents/Info.plist').read_bytes())
    url = info['SUFeedURL'].removesuffix('/graf-appcast.xml')
    # Reuse the public validation path, including fresh Keychain and both signatures.
    # Verify-only cannot create, sign or replace a missing/different prepared version.
    command('env', 'GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1', 'GRAF_REQUIRE_RELEASE_PROVENANCE=1',
            'GRAF_RELEASE_SIGNING_MODE=keychain', f'GRAF_VERSION={version}',
            f'GRAF_UPDATE_APP_BUNDLE={args.app}', f'GRAF_PREVIOUS_APP_BUNDLE={args.previous}',
            f'GRAF_UPDATE_RELEASE_NOTES={args.notes}', f'GRAF_UPDATE_DOWNLOAD_BASE_URL={url}',
            f'GRAF_RELEASE_INPUT_CONTEXT={args.context}',
            f'GRAF_RELEASE_SIGNING_KEYCHAIN_ATTESTATION={directory / ("GRAF-" + version + "-signing-attestation.json")}',
            SCRIPTS / 'prepare-app-update.sh', '--verify-only')
    with locked(STATE / '.graf-update-staging.lock'):
        identity_args = argparse.Namespace(app=args.app, previous=args.previous, notes=args.notes,
                                           version=version, url=url, public='1', context=args.context)
        identity = stage_identity(identity_args)
        check_stage(directory, identity)
        for architecture in ('arm64', 'x86_64'):
            command(MACOS / 'Scripts/validate-packaged-app-launch.sh', args.app, '5', architecture)
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
