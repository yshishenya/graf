#!/usr/bin/env python3
"""Prepare the two local release images for exactly one locked deploy attempt.

State, in the git-private ``graf-release-images`` directory:

    active.json             the attempt that owns the runtime right now
    attempts/<id>/          one create-once deploy attempt
        baseline.json       previous images and the containers seen before any build
        previous.json       pinned override for those previous images
        identity.json       release identity this attempt was prepared for
        candidate.json      images for the exact source SHA (built or pulled)
        override.json       pinned override for those candidate images
        no-rollback.json    durable boundary before an activated runtime is touched
        start-intent.json   durable permission for the first activated runtime launch
        start-boundary.json consumer identities after the stop, just before launch
        start-observed.json candidate consumer creation or restart seen before cleanup
        forward-stop.json   active receipt for the stopped runtime
        forward-stops/      immutable history of reconciled stops
        result.json         terminal outcome, create-once, only after verification
        release-images.py   immutable copy of this helper, survives the rollback reset
    images/<sha>-<platform>.json
                            reusable build cache for one exact source SHA

    prepare -> verify candidate -> finish deployed    successful upgrade
    prepare -> verify previous  -> finish restored    rollback to the previous images
    prepare -> finish unchanged                       the runtime was never touched

``prepare`` refuses to run while ``active.json`` names an attempt without a
terminal result: a half-finished deploy is recovered explicitly first.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import fcntl
import hashlib
from html.parser import HTMLParser
from http.client import HTTPSConnection
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from uuid import UUID, uuid4
from xml.etree import ElementTree

SOURCE_LABEL = "org.2brain.graf.dev.source-sha"
TARGET_LABEL = "org.2brain.graf.release.build-target"
PROJECT = "twobrain-rec"
MEDIA_WORKER = "rec-media-worker"
REQUIRED_CONSUMERS = {"rec-api", "rec-processing-worker", "rec-maintenance", MEDIA_WORKER}
INFRASTRUCTURE_SERVICES = {"rec-postgres", "rec-minio", "rec-temporal"}
REQUIRED_DEPLOYED_SERVICES = REQUIRED_CONSUMERS | INFRASTRUCTURE_SERVICES
FORWARD_COMPOSE = ("docker", "compose", "--profile", "operations", "-f", "infra/docker-compose.yml", "-f", "-")
NORMALIZATION_ENABLED = "TWOBRAIN_PLAYBACK_NORMALIZATION_ENABLED"
NORMALIZATION_DISPATCH = "TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED"
PUBLIC_GET_DEADLINE = 90
PUBLIC_PROOF_DEADLINE = 300
NO_ROLLBACK = "no-rollback.json"
# docker build targets that produce the application images.
TARGETS = ("runtime", "media-runtime")
# docker info reports uname architectures, docker image inspect reports Go ones.
ARCHITECTURES = {"x86_64": "amd64", "aarch64": "arm64"}

SOURCE_SHA = re.compile(r"[0-9a-f]{40}")
ATTEMPT_ID = re.compile(r"[0-9a-f]{32}")
CONTAINER_ID = re.compile(r"[0-9a-f]{64}")
DOCKER_START_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z")
DOCKER_NOT_STARTED = "0001-01-01T00:00:00Z"
SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
SERVICE = re.compile(r"rec-[a-z0-9-]+")
IMAGE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@-]*")
CANDIDATE_ID = re.compile(r"rc-[A-Za-z0-9-]{1,100}")
SCHEMA_REVISION = re.compile(r"[0-9A-Za-z_]+")
BUCKET = re.compile(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]")

# Both recorded sides of an attempt: the images that must be running and the
# pinned override that keeps them pinned.
SIDES = {
    "candidate": dict(record="candidate.json", override="override.json"),
    "previous": dict(record="baseline.json", override="previous.json"),
}
# A terminal result names the side the runtime is left on. Nothing else may
# finish an attempt, and only a finished attempt may be replaced.
RESULTS = {"deployed": "candidate", "unchanged": "previous", "restored": "previous"}


def require(value, message):
    if not value:
        raise ValueError(message)


def require_match(value, pattern, message):
    require(isinstance(value, str) and pattern.fullmatch(value), message)
    return value


def command(*args, input=None, env=None, pass_fds=(), timeout=None):
    # Compose configuration can contain secret locations: parse it in memory, never log it.
    result = subprocess.run(args, input=input, env=env, pass_fds=pass_fds, timeout=timeout,
                            text=True, capture_output=True)
    require(result.returncode == 0, f"{args[0]} {args[1]} failed")
    return result.stdout.strip()


def read(path):
    return json.loads(Path(path).read_text())


def sync_directory(path):
    directory = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def write(path, value, *, keep_unconfirmed_result=False):
    """Persist JSON atomically.

    A reader never sees a partial file. A ``result.json`` that could not be
    acknowledged durably is removed again, so an unacknowledged result is never
    read as a finished deployment. Forward recovery can retain that rename
    for verification and acknowledgement under the release lock.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent)
    replaced = False
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        replaced = True
        sync_directory(path.parent)
    except OSError:
        if replaced and (path.name == "forward-result-confirmed.json"
                         or path.name == "result.json" and not keep_unconfirmed_result):
            path.unlink(missing_ok=True)
            sync_directory(path.parent)
        raise
    finally:
        Path(temporary).unlink(missing_ok=True)


def state_dir():
    return Path(command("git", "rev-parse", "--git-path", "graf-release-images")).resolve()


def require_deployment_lock(fd):
    require(fd >= 3, "an inherited deployment lock descriptor is required")
    path = command("git", "rev-parse", "--git-path", "twobrain-rec-deploy.lock")
    expected = os.stat(path, follow_symlinks=False)
    require(stat.S_ISREG(expected.st_mode) and os.path.samestat(expected, os.fstat(fd)),
            "descriptor does not identify the deployment lock")
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def active(state):
    """The attempt that owns the runtime now, per the durable active pointer."""
    name = require_match(read(state / "active.json")["attempt"], ATTEMPT_ID, "invalid attempt identity")
    return state / "attempts" / name


def require_exact_source(expected, message="release source is not the exact clean checkout"):
    """The checkout must be exactly this commit with no local change at all."""
    require(command("git", "rev-parse", "HEAD") == expected
            and not command("git", "status", "--porcelain", "--untracked-files=all"), message)


def platform():
    system, arch = command("docker", "info", "--format", "{{.OSType}}/{{.Architecture}}").split("/")
    arch = ARCHITECTURES.get(arch, arch)
    require(system == "linux" and arch in {"amd64", "arm64"}, "unsupported Docker platform")
    return f"{system}/{arch}"


def image(ref, target_platform, source=None, *, target=None):
    """Inspect one image and refuse anything but the exact expected identity.

    A digest ref must resolve to itself, the platform must match the target, and
    an application image must also prove the source SHA in label and environment.
    """
    info = json.loads(command("docker", "image", "inspect", ref))[0]
    require_match(info["Id"], SHA256, "invalid image ID")
    require(not ref.startswith("sha256:") or info["Id"] == ref, "image ID mismatch")
    require(f"{info['Os']}/{info['Architecture']}" == target_platform, "image platform mismatch")
    if source is not None:
        require(info["Config"].get("Labels", {}).get(SOURCE_LABEL) == source
                and f"GRAF_DEV_SOURCE_SHA={source}" in info["Config"].get("Env", []), "image source mismatch")
    if target is not None:
        require(info["Config"].get("Labels", {}).get(TARGET_LABEL) == target, "image build target mismatch")
    return info["Id"]


def resolved_compose(source, *, timeout=None):
    """Resolve Compose from an exact commit without moving the checkout."""
    text = command("git", "show", f"{source}:infra/docker-compose.yml")
    config = json.loads(command("docker", "compose", "--project-directory", str(Path.cwd() / "infra"),
                                "--profile", "operations", "-f", "-", "config", "--format", "json", input=text,
                                **({"timeout": timeout} if timeout is not None else {})))
    require(config.get("name") == PROJECT, "unexpected Compose project")
    return config


def compose_config(source):
    return compose_images(resolved_compose(source))


def compose_images(config):
    services = {}
    for name, service in config["services"].items():
        require_match(name, SERVICE, "invalid Compose service")
        build = service.get("build")
        target = None
        if build:
            require(set(build) <= {"context", "dockerfile", "target"}
                    and Path(build["context"]).resolve() == Path.cwd().resolve()
                    and build.get("dockerfile") == "infra/server/Dockerfile", "unsupported release build configuration")
            target = build.get("target", "runtime")
            require(target in TARGETS, "unknown release target")
        ref = service.get("image") or f"{PROJECT}-{name}"
        require_match(ref, IMAGE_REF, "invalid image ref")
        services[name] = dict(ref=ref, target=target)
    require(services and any(row["target"] for row in services.values()), "missing application services")
    return services


def project_container_ids(timeout=None):
    options = {"timeout": timeout} if timeout is not None else {}
    return command("docker", "ps", "-aq", "--no-trunc", "--filter",
                   f"label=com.docker.compose.project={PROJECT}", **options).splitlines()


def containers(*, reject_active_oneoffs=False, include_start_time=False, timeout=None):
    """Every non-one-off container of this Compose project, keyed by service."""
    observed = {}
    ids = project_container_ids(timeout)
    if not ids:
        return observed
    options = {"timeout": timeout} if timeout is not None else {}
    for row in json.loads(command("docker", "inspect", *ids, **options)):
        labels = row["Config"].get("Labels", {})
        require(labels.get("com.docker.compose.project") == PROJECT, "container project mismatch")
        state = row["State"]
        if reject_active_oneoffs:
            require(not state.get("Restarting") and not state.get("Paused"),
                    "release container is restarting or paused")
        if labels.get("com.docker.compose.oneoff", "false").lower() == "true":
            require(not reject_active_oneoffs or not state["Running"], "one-off release operation is still running")
            continue
        name = labels.get("com.docker.compose.service")
        require(name and name not in observed, "missing/ambiguous container service")
        observed[name] = dict(id=row["Id"], image=row["Image"], running=state["Running"])
        if include_start_time and name not in INFRASTRUCTURE_SERVICES:
            observed[name]["started_at"] = require_match(state["StartedAt"], DOCKER_START_TIME,
                                                          "invalid container start time")
    return observed


def override(images):
    """The pinned image override for one recorded side of an attempt."""
    return {"services": {name: {"image": row["image"], "pull_policy": "never"} for name, row in images.items()}}


def validate_override(path):
    """Refuse any override that is not exactly a mapping of service to pinned image."""
    value = read(path)
    require(set(value) == {"services"} and value["services"], "invalid image override")
    for name, row in value["services"].items():
        pinned = (isinstance(name, str) and SERVICE.fullmatch(name)
                  and isinstance(row, dict) and set(row) == {"image", "pull_policy"}
                  and isinstance(row["image"], str) and SHA256.fullmatch(row["image"])
                  and row["pull_policy"] == "never")
        require(pinned, "unsafe image override")
    return value


def pinned_image(path, service):
    """One pinned image ID out of a validated override."""
    services = validate_override(path)["services"]
    require(service in services, f"{service} is not part of this release override")
    return services[service]["image"]


def retain(images):
    """Hold every image of a side under an immutable local tag.

    A later build or pull can move the tag a recorded ID came from; the explicit
    ``graf-release/retained`` tag keeps the exact image alive instead.
    """
    for identity in {row["image"] for row in images.values()}:
        command("docker", "image", "tag", identity, f"graf-release/retained:{identity[7:]}")


def sealed_receipt(attempt):
    record = read(attempt / NO_ROLLBACK)
    require(record.get("schema_version") == 3, "unknown activated deployment receipt")
    require(attempt_digest(attempt, "baseline") == record.get("baseline_sha256")
            and attempt_digest(attempt, "candidate") == record.get("candidate_sha256")
            and attempt_digest(attempt, "identity") == record.get("identity_sha256"),
            "activated release evidence does not match the receipt")
    require(validate_override(attempt / "override.json") == override(read(attempt / "candidate.json")["images"]),
            "activated release override does not match the candidate")
    return record


def completed_side(attempt):
    result_file = attempt / "result.json"
    require(result_file.is_file(), "unfinished deployment requires explicit recovery; baseline retained")
    result = read(result_file).get("result")
    require(result in RESULTS, "unknown deployment outcome")
    if os.path.lexists(attempt / NO_ROLLBACK):
        require(result == "deployed", "activated deployment requires forward recovery")
        seal = sealed_receipt(attempt)
        if "forward" in seal:
            record = verify_forward_result_record(attempt, seal)
            expected = dict(result_sha256=attempt_digest(attempt, "result"))
            ack = attempt / "forward-result-confirmed.json"
            require(ack.is_file() and read(ack) == expected, "forward result needs locked confirmation")
            sync_directory(attempt)
            require(read(ack) == expected and read(result_file) == record,
                    "forward result changed during confirmation")
            observed = forward_running(attempt, REQUIRED_CONSUMERS, allow_restart=True)
            require(all(same_container(observed[name], row) for name, row in record["forward"]["containers"].items()),
                    "running forward release differs from its result")
            verify_forward_ready_storage(observed, seal)
            require(forward_running(attempt, REQUIRED_CONSUMERS, allow_restart=True) == observed,
                    "forward predecessor changed during verification")
            return RESULTS[result]
        # A result rename can survive even when the write was not acknowledged.
        verify_finished_runtime(attempt, "deployed", read(attempt / "baseline.json"))
    return RESULTS[result]


def recorded_images(state, previous_sha):
    """Images recorded by the completed attempt whose runtime this deploy replaces.

    Only a finished attempt may be replaced, and its record may supply an image ID
    only when it describes exactly this previous source SHA.
    """
    if not os.path.lexists(state / "active.json"):
        return {}
    prior = active(state)
    side = completed_side(prior)
    data = read(prior / SIDES[side]["record"])
    if os.path.lexists(prior / NO_ROLLBACK):
        require(data["source_sha"] == previous_sha, "activated release source differs from the checkout")
    return data["images"] if data["source_sha"] == previous_sha else {}


def previous_image(service, row, observed, recorded, target_platform):
    """One previous image: the live container, else a recorded ID, else the Compose ref."""
    ref = observed.get(service, {}).get("image") or recorded.get(service, {}).get("image") or row["ref"]
    return image(ref, target_platform)


def candidate_image(service, row, previous, targets, target_platform, source_sha):
    """One candidate image: built from this source SHA, reused, or pulled by exact ref."""
    if row["target"]:
        return image(targets[row["target"]], target_platform, source_sha)
    if service in previous and row["ref"] == previous[service]["ref"]:
        # An unchanged third-party ref reuses the exact ID already verified as previous.
        return image(previous[service]["image"], target_platform)
    # A changed third-party ref is pulled before downtime and pinned by its measured ID.
    command("docker", "pull", "--platform", target_platform, row["ref"])
    return image(row["ref"], target_platform)


def build_targets(state, attempt, source_sha, target_platform):
    """Both application images for this exact source SHA, reused or built.

    Returns the target IDs and the cache file to publish once the checkout is
    confirmed unchanged, or ``None`` when cached images were reused. Every cached
    image is inspected again: a stale ID, platform, source label or environment
    is a hard failure, never a silent rebuild.
    """
    cache = state / "images" / f"{source_sha}-{target_platform.replace('/', '-')}.json"
    cached = read(cache) if cache.exists() else None
    if cached:
        require(cached.get("source_sha") == source_sha and cached.get("platform") == target_platform,
                "cached image identity mismatch")
        require(set(cached["targets"]) == set(TARGETS), "incomplete cached targets")
        return {name: image(ref, target_platform, source_sha) for name, ref in cached["targets"].items()}, None
    targets = {}
    for target in TARGETS:
        iidfile = attempt / f"{target}.iid"
        command("docker", "build", "--platform", target_platform, "--target", target,
                "--build-arg", f"GRAF_DEV_SOURCE_SHA={source_sha}", "--iidfile", str(iidfile),
                "-f", "infra/server/Dockerfile", ".")
        targets[target] = image(iidfile.read_text().strip(), target_platform, source_sha)
    retain({target: dict(image=identity) for target, identity in targets.items()})
    return targets, cache


def claim_attempt(state, args, target_platform, previous, observed):
    """Create the create-once attempt and make it the active one.

    The baseline, the pinned previous override, the release identity and an
    immutable copy of this helper are durable before ``active.json`` names the
    attempt, so an active attempt always has a recorded baseline to recover from.
    """
    attempt = state / "attempts" / args.attempt_id
    require(not attempt.exists(), "deployment attempt is create-once")
    write(attempt / "baseline.json", dict(schema_version=1, source_sha=args.previous_sha,
                                          platform=target_platform, images=previous, containers=observed))
    write(attempt / "previous.json", override(previous))
    write(attempt / "identity.json", dict(source_sha=args.source_sha, candidate_id=args.candidate_id,
                                          decision_digest=args.decision_digest, full_digest=args.full_digest))
    helper = attempt / "release-images.py"
    with helper.open("xb") as handle:
        # Keep the helper across the existing rollback's source reset.
        handle.write(Path(__file__).read_bytes())
        handle.flush()
        os.fsync(handle.fileno())
    # The deploy lock serializes attempts. A completed predecessor alone may be replaced.
    write(state / "active.json", dict(attempt=attempt.name))
    return attempt


def prepare(args):
    """Claim one attempt: record the previous images, then resolve the candidate images."""
    # The request must be exactly identified before any state is touched.
    require_match(args.source_sha, SOURCE_SHA, "invalid source SHA")
    require_match(args.previous_sha, SOURCE_SHA, "invalid source SHA")
    require_match(args.candidate_id, CANDIDATE_ID, "invalid candidate ID")
    require_match(args.attempt_id, ATTEMPT_ID, "invalid attempt ID")
    for digest_value in (args.decision_digest, args.full_digest):
        require_match(digest_value, SHA256, "invalid release evidence identity")
    require_exact_source(args.source_sha)

    # A finished attempt may be replaced; an attempt without a result must not be.
    state = state_dir()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    recorded = recorded_images(state, args.previous_sha)

    # Both sides are resolved before anything is claimed: nothing that can still
    # reject this release may leave an unfinished attempt behind.
    target_platform = platform()
    previous_config, candidate_config = compose_config(args.previous_sha), compose_config(args.source_sha)
    observed = containers()
    require(observed.get("rec-api", {}).get("running") is True, "previous API is not running")
    # Previous identities come from the running runtime, never from a moving tag.
    previous = {service: dict(row, image=previous_image(service, row, observed, recorded, target_platform))
                for service, row in previous_config.items()}

    attempt = claim_attempt(state, args, target_platform, previous, observed)
    # Hold every previous ID before the first build can move a tag it came from.
    retain(previous)

    # Candidate identities: built, reused, or pulled before downtime.
    targets, cache = build_targets(state, attempt, args.source_sha, target_platform)
    candidate = {service: dict(row, image=candidate_image(service, row, previous, targets,
                                                          target_platform, args.source_sha))
                 for service, row in candidate_config.items()}
    retain(candidate)

    # Neither a moved checkout nor a changed tree may publish a reusable cache.
    require_exact_source(args.source_sha, "release source changed during preparation")
    if cache is not None:
        write(cache, dict(source_sha=args.source_sha, platform=target_platform, targets=targets))
    write(attempt / "candidate.json", dict(schema_version=1, source_sha=args.source_sha,
                                           platform=target_platform, images=candidate))
    write(attempt / "override.json", override(candidate))
    print(attempt)


def verify(attempt, side, services=()):
    """Prove the running runtime uses exactly the images recorded for one side."""
    data = read(attempt / SIDES[side]["record"])
    require(data["platform"] == platform(), "Docker platform changed")
    current = containers()
    names = set(services) or {name for name, row in current.items() if row["running"]}
    require(names, "no runtime containers observed")
    for name in names:
        require(name in data["images"] and current.get(name, {}).get("running") is True
                and current[name]["image"] == data["images"][name]["image"], "runtime image mismatch")
    return current


def attempt_digest(attempt, record):
    return hashlib.sha256((attempt / f"{record}.json").read_bytes()).hexdigest()


def storage_binding_digest():
    scope = os.environ.get("TWOBRAIN_STRICT_STORAGE_SCOPE", "")
    recovery_id = os.environ.get("TWOBRAIN_STRICT_STORAGE_RECOVERY_ID", "")
    require(scope.strip() and recovery_id, "storage recovery binding is required")
    return hashlib.sha256(json.dumps([scope, str(UUID(recovery_id))]).encode()).hexdigest()


def storage_recovery_state(media_image, *, timeout=None):
    require_match(media_image, SHA256, "storage probe image must be pinned")
    volume = "twobrain-rec-storage-recovery"
    directory = "/run/graf-storage-recovery"
    # Do not let Docker silently create a missing operator volume.
    options = {"timeout": timeout} if timeout is not None else {}
    command("docker", "volume", "inspect", volume, **options)
    mode = command(
        "docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
        "--mount", f"type=volume,source={volume},target={directory},readonly,volume-nocopy",
        "-e", f"TWOBRAIN_STRICT_STORAGE_RECOVERY_DIRECTORY={directory}",
        "-e", f"TWOBRAIN_STRICT_STORAGE_SCOPE={os.environ.get('TWOBRAIN_STRICT_STORAGE_SCOPE', '')}",
        "-e", f"TWOBRAIN_STRICT_STORAGE_RECOVERY_ID={os.environ.get('TWOBRAIN_STRICT_STORAGE_RECOVERY_ID', '')}",
        "-e", "TWOBRAIN_STRICT_STORAGE_RECOVERY_ALLOW_LEGACY="
        + (os.environ.get("TWOBRAIN_STRICT_STORAGE_RECOVERY_ALLOW_LEGACY") or "false"),
        media_image, "python", "-c", """
from pathlib import Path
from twobrain_rec_server.config import Settings
from twobrain_rec_server.storage.recovery import storage_recovery_token

settings = Settings(_env_file=None)
if settings.strict_storage_recovery_directory != Path("/run/graf-storage-recovery"):
    raise SystemExit(1)
token = storage_recovery_token(settings)
if token == "legacy" and settings.strict_storage_recovery_allow_legacy:
    print("legacy")
elif (settings.strict_storage_recovery_id is not None
      and token == str(settings.strict_storage_recovery_id)
      and not settings.strict_storage_recovery_allow_legacy):
    print("reconciled")
else:
    raise SystemExit(1)
""",
        **options,
    )
    require(mode in ("legacy", "reconciled"), "storage recovery volume is unverified")
    return mode


def observed_storage(observed, *, timeout=None):
    """Capture native store identities and the current migration revision."""
    for service in ("rec-postgres", "rec-minio"):
        require(observed.get(service, {}).get("running") is True, "storage service is not running")
    postgres = require_match(observed["rec-postgres"]["id"], CONTAINER_ID, "invalid PostgreSQL container identity")
    options = {"timeout": timeout} if timeout is not None else {}
    row = command("docker", "exec",
                  "--env=PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=5000",
                  "--env=PGCONNECT_TIMEOUT=5", postgres, "psql", "-wXAtq", "-v", "ON_ERROR_STOP=1",
                  "-U", "twobrain_rec", "-d", "twobrain_rec", "-c",
                  "SELECT system_identifier::text || '|' || version_num FROM pg_control_system() "
                  "CROSS JOIN alembic_version", **options)
    postgres_id, _, schema = row.partition("|")
    require_match(postgres_id, re.compile(r"[1-9][0-9]{0,19}"), "invalid PostgreSQL system identity")
    require_match(schema, SCHEMA_REVISION, "current database schema is not unique")
    minio = require_match(observed["rec-minio"]["id"], CONTAINER_ID, "invalid MinIO container identity")
    format_data = json.loads(command("docker", "exec", minio, "cat", "/data/.minio.sys/format.json", **options))
    require(isinstance(format_data, dict) and format_data.get("format") == "xl-single",
            "unsupported MinIO storage format")
    minio_id = UUID(require_match(format_data.get("id"), re.compile(r"[0-9a-fA-F-]{36}"),
                                  "invalid MinIO deployment identity"))
    require(minio_id.int != 0, "invalid MinIO deployment identity")
    stores = hashlib.sha256(json.dumps([postgres_id, str(minio_id)]).encode()).hexdigest()
    return stores, schema


def forbid_rollback(attempt, args):
    """Seal the active attempt before changing an activated runtime."""
    require(attempt.name == args.attempt_id, "cannot seal another deployment attempt")
    require(not (attempt / "result.json").exists(), "deployment is already finished")
    marker = attempt / NO_ROLLBACK
    require(not os.path.lexists(marker), "no-rollback boundary is create-once")
    for revision in (args.previous_schema, args.candidate_schema):
        require_match(revision, SCHEMA_REVISION, "invalid schema revision")
    require(args.backup_reference.is_absolute(), "verified backup reference must be absolute")
    candidate = read(attempt / "candidate.json")
    require(storage_recovery_state(candidate["images"][MEDIA_WORKER]["image"]) == "reconciled",
            "activated storage recovery volume is unverified")
    stores, schema = observed_storage(containers())
    require(schema == args.previous_schema, "database schema changed before sealing")
    write(marker, dict(schema_version=3, previous_schema=args.previous_schema,
                       candidate_schema=args.candidate_schema, backup_reference=str(args.backup_reference),
                       binding_sha256=storage_binding_digest(),
                       stores_sha256=stores,
                       baseline_sha256=attempt_digest(attempt, "baseline"),
                       candidate_sha256=attempt_digest(attempt, "candidate"),
                       identity_sha256=attempt_digest(attempt, "identity")))
    state = attempt.parent.parent
    for directory in (attempt.parent, state, state.parent):
        sync_directory(directory)


def check_forward_baseline(state, failed_attempt, failed_sha, *, checkout_sha=None, expected_active=None,
                           allow_pending_smoke=False, proposing_stop=False):
    """Read the current schema without starting a consumer or changing the active attempt."""
    require_match(failed_attempt, ATTEMPT_ID, "invalid failed attempt ID")
    require_match(failed_sha, SOURCE_SHA, "invalid failed source SHA")
    require_exact_source(checkout_sha or failed_sha)
    require(active(state).name == (expected_active or failed_attempt), "failed attempt is not active")
    attempt = state / "attempts" / failed_attempt
    receipt = sealed_receipt(attempt)
    abandoned_result = unconfirmed_forward_result_digest(attempt, receipt)
    if abandoned_result and not proposing_stop:
        _, stop = read_forward_stop(attempt)
        require(stop.get("abandoned_result_sha256") == abandoned_result,
                "unconfirmed forward result needs a verified stop receipt")
    if not allow_pending_smoke and os.path.lexists(attempt / "forward-smoke-started.json"):
        run_id = read(attempt / "forward-smoke-started.json")["run_id"]
        proof = attempt / "forward-smoke.json"
        if not (proof.is_file() and read(proof) == forward_smoke_receipt(run_id)):
            verify_forward_smoke_cleanup(attempt, run_id)
    require(receipt.get("binding_sha256") == storage_binding_digest(), "storage recovery binding differs")
    baseline = read(attempt / "baseline.json")
    candidate = read(attempt / "candidate.json")
    require(candidate["source_sha"] == read(attempt / "identity.json")["source_sha"] == failed_sha,
            "failed source does not match the recorded candidate")
    require(platform() == candidate["platform"] == baseline["platform"], "Docker platform changed")
    observed = containers(reject_active_oneoffs=True)
    running = {name for name, row in observed.items() if row["running"]}
    require(running == INFRASTRUCTURE_SERVICES, "release consumers must be stopped and infrastructure running")
    for service in running:
        require(observed[service]["image"] in {side["images"][service]["image"] for side in (baseline, candidate)},
                "unrecorded infrastructure image")
    require(storage_recovery_state(candidate["images"][MEDIA_WORKER]["image"]) == "reconciled",
            "activated storage recovery volume is unverified")
    stores, schema = observed_storage(observed)
    require(stores == receipt.get("stores_sha256"), "PostgreSQL or MinIO storage identity changed")
    require(schema in (receipt["previous_schema"], receipt["candidate_schema"]),
            "current database schema was not recorded by the failed release")
    if abandoned_result and not proposing_stop:
        verify_forward_stop(attempt, schema)
    return schema


def activated_start_attempt(state, attempt_id, deployment_lock_fd):
    require_deployment_lock(deployment_lock_fd)
    attempt = active(state)
    require(attempt.name == attempt_id and not os.path.lexists(attempt / "result.json"),
            "start evidence requires the active unfinished attempt")
    receipt = sealed_receipt(attempt)
    require("forward" not in receipt, "ordinary start cannot authorize forward recovery")
    candidate = read(attempt / "candidate.json")
    source = candidate["source_sha"]
    require_exact_source(require_match(source, SOURCE_SHA, "invalid start intent source SHA"))
    require(source == read(attempt / "identity.json")["source_sha"], "start source does not match release identity")
    return attempt, candidate


def record_start_intent(state, attempt_id, deployment_lock_fd):
    """Record the ordinary activated launch before Compose can change consumers."""
    attempt, _ = activated_start_attempt(state, attempt_id, deployment_lock_fd)
    write_start_intent(attempt, containers(reject_active_oneoffs=True))


def write_start_intent(attempt, observed):
    marker = attempt / "start-intent.json"
    require(not os.path.lexists(marker), "start intent is create-once; reconcile before another launch")
    write(marker, dict(schema_version=1, attempt_id=attempt.name,
                       seal_sha256=attempt_digest(attempt, "no-rollback"),
                       previous_consumers={name: observed[name]["id"]
                                           for name in sorted(REQUIRED_CONSUMERS & observed.keys())}))


def start_intent_digest(attempt):
    intent_digest = attempt_digest(attempt, "start-intent")
    intent = read(attempt / "start-intent.json")
    require(intent["schema_version"] == 1 and intent["attempt_id"] == attempt.name
            and intent["seal_sha256"] == attempt_digest(attempt, "no-rollback"),
            "start intent does not match the active attempt")
    return intent_digest


def start_boundary_evidence(attempt, intent_digest):
    digest = attempt_digest(attempt, "start-boundary")
    boundary = read(attempt / "start-boundary.json")
    require(boundary["schema_version"] == 1 and boundary["attempt_id"] == attempt.name
            and boundary["intent_sha256"] == intent_digest, "start boundary does not match the intent")
    previous = boundary["stopped_consumers"]
    require(previous.keys() <= REQUIRED_CONSUMERS, "invalid stopped consumers")
    for row in previous.values():
        require_match(row["id"], CONTAINER_ID, "invalid stopped container ID")
        require_match(row["started_at"], DOCKER_START_TIME, "invalid stopped container start time")
    return digest, previous


def changed_consumer(previous, row):
    return (row["id"] != previous.get("id")
            or (row["started_at"] != DOCKER_NOT_STARTED and row["started_at"] != previous["started_at"]))


def record_start_boundary(state, attempt_id, deployment_lock_fd):
    """Pin the stopped consumer snapshot used to recognize changes caused by launch."""
    attempt, _ = activated_start_attempt(state, attempt_id, deployment_lock_fd)
    write_start_boundary(attempt, containers(reject_active_oneoffs=True, include_start_time=True))


def write_start_boundary(attempt, observed):
    intent_digest = start_intent_digest(attempt)
    marker = attempt / "start-boundary.json"
    require(not os.path.lexists(marker), "start boundary is create-once; reconcile before another launch")
    previous = {}
    for name, row in observed.items():
        if name in REQUIRED_CONSUMERS:
            require(not row["running"], "previous release consumers are still running")
            previous[name] = dict(id=require_match(row["id"], CONTAINER_ID, "invalid container ID"),
                                  started_at=row["started_at"])
    write(marker, dict(schema_version=1, attempt_id=attempt.name, intent_sha256=intent_digest,
                       stopped_consumers=previous))


def observe_start(state, attempt_id, deployment_lock_fd):
    """Save evidence of a candidate consumer before failure cleanup changes the stack."""
    attempt, candidate = activated_start_attempt(state, attempt_id, deployment_lock_fd)
    save_start_observation(attempt, candidate, containers(include_start_time=True))


def save_start_observation(attempt, candidate, current):
    intent_digest = start_intent_digest(attempt)
    boundary_digest, previous = start_boundary_evidence(attempt, intent_digest)
    marker = attempt / "start-observed.json"
    require(not os.path.lexists(marker), "start observation is create-once")
    observed = {}
    for name, row in current.items():
        if name not in REQUIRED_CONSUMERS or row["image"] != candidate["images"][name]["image"]:
            continue
        if changed_consumer(previous.get(name, {}), row):
            observed[name] = dict(id=require_match(row["id"], CONTAINER_ID, "invalid candidate container ID"),
                                  image=row["image"], started_at=row["started_at"])
    require(observed, "no candidate consumer creation or restart was observed")
    require(attempt_digest(attempt, "start-boundary") == boundary_digest
            and start_intent_digest(attempt) == intent_digest, "start evidence changed during observation")
    write(marker, dict(schema_version=1, attempt_id=attempt.name, boundary_sha256=boundary_digest,
                       consumers=observed))


def forward_start_evidence(attempt):
    require(os.path.lexists(attempt / "start-intent.json"), "failed release has no recorded launch intent")
    intent = start_intent_digest(attempt)
    evidence = dict(intent_sha256=intent)
    previous = {}
    if os.path.lexists(attempt / "start-boundary.json"):
        evidence["boundary_sha256"], previous = start_boundary_evidence(attempt, intent)
    if os.path.lexists(attempt / "start-observed.json"):
        digest = attempt_digest(attempt, "start-observed")
        observation = read(attempt / "start-observed.json")
        require("boundary_sha256" in evidence and observation["schema_version"] == 1
                and observation["attempt_id"] == attempt.name
                and observation["boundary_sha256"] == evidence["boundary_sha256"],
                "start observation does not match the boundary")
        candidate = read(attempt / "candidate.json")["images"]
        consumers = observation["consumers"]
        require(consumers and consumers.keys() <= REQUIRED_CONSUMERS, "invalid observed consumers")
        for name, row in consumers.items():
            require_match(row["id"], CONTAINER_ID, "invalid observed container ID")
            require_match(row["started_at"], DOCKER_START_TIME, "invalid observed start time")
            require(row["image"] == candidate[name]["image"] and changed_consumer(previous.get(name, {}), row),
                    "start observation does not show a candidate consumer change")
        evidence["observation_sha256"] = digest
    return evidence


def stopped_forward_runtime():
    current = containers(reject_active_oneoffs=True, include_start_time=True)
    require({name for name, row in current.items() if row["running"]} == INFRASTRUCTURE_SERVICES,
            "forward stop requires only infrastructure to be running")
    return current


def unique_json_fields(pairs):
    value = dict(pairs)
    require(len(value) == len(pairs), "operator reconciliation has duplicate fields")
    return value


def forward_stop_snapshot(state, args):
    require_deployment_lock(args.deployment_lock_fd)
    require_match(args.failed_attempt, ATTEMPT_ID, "invalid failed attempt ID")
    attempt = active(state)
    require(attempt.name == args.failed_attempt, "failed attempt is not active")
    start = forward_start_evidence(attempt)
    seal = attempt_digest(attempt, "no-rollback")
    scope = storage_binding_digest()
    current = stopped_forward_runtime()
    schema = check_forward_baseline(state, attempt.name, args.failed_sha, allow_pending_smoke=True,
                                    proposing_stop=True)
    require(forward_start_evidence(attempt) == start and stopped_forward_runtime() == current,
            "forward runtime or launch evidence changed during reconciliation")
    snapshot = dict(start=start, schema=schema, containers=current)
    for name in ("forward-smoke-started", "forward-smoke-cleanup-intent"):
        if os.path.lexists(attempt / f"{name}.json"):
            snapshot[f"{name}_sha256"] = attempt_digest(attempt, name)
    proposal = dict(schema_version=1, attempt_id=attempt.name, seal_sha256=seal, binding_sha256=scope,
                    docker_operations_quiesced=False,
                    snapshot_sha256=hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
                    infrastructure={name: current[name]["id"] for name in INFRASTRUCTURE_SERVICES})
    abandoned_result = unconfirmed_forward_result_digest(attempt, sealed_receipt(attempt), current)
    if abandoned_result:
        proposal["abandoned_result_sha256"] = abandoned_result
        proposal["abandon_unconfirmed_result"] = False
        proposal["storage_writes_quiesced"] = False
    if "forward-smoke-started_sha256" in snapshot and not (attempt / "forward-smoke.json").is_file():
        proposal["storage_writes_quiesced"] = False
    return attempt, proposal, snapshot


def record_forward_stop(state, args):
    """Pin the operator's external reconciliation to the actual stopped stack."""
    attempt, proposal, snapshot = forward_stop_snapshot(state, args)
    with os.fdopen(os.open(args.operator_record, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "operator reconciliation must be a regular file")
        raw = stream.read(4097)
    require(len(raw) <= 4096, "operator reconciliation is too large")
    record = json.loads(raw, object_pairs_hook=unique_json_fields)
    confirmations = dict(docker_operations_quiesced=True)
    if "abandon_unconfirmed_result" in proposal:
        confirmations["abandon_unconfirmed_result"] = True
    if "storage_writes_quiesced" in proposal:
        confirmations["storage_writes_quiesced"] = True
    require(isinstance(record, dict) and type(record.get("schema_version")) is int
            and all(record.get(key) is True for key in confirmations)
            and record == dict(proposal, **confirmations),
            "operator reconciliation does not match the attempt, binding or stopped snapshot")
    require(forward_start_evidence(attempt) == snapshot["start"]
            and stopped_forward_runtime() == snapshot["containers"],
            "forward runtime or launch evidence changed during reconciliation")
    receipt = (proposal | snapshot | confirmations
               | dict(operator_sha256=hashlib.sha256(raw).hexdigest()))
    marker = attempt / "forward-stop.json"
    prior_digest = None
    if os.path.lexists(marker):
        prior_digest, prior = read_forward_stop(attempt)
        if prior == dict(receipt, previous_stop_sha256=prior["previous_stop_sha256"]):
            sync_directory(attempt)
            return
    receipt["previous_stop_sha256"] = prior_digest
    digest = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    history = attempt / "forward-stops" / f"{digest}.json"
    if not os.path.lexists(history):
        write(history, receipt)
    require(hashlib.sha256(history.read_bytes()).hexdigest() == digest, "forward stop history differs")
    sync_directory(history.parent)
    sync_directory(attempt)
    require(active(state) == attempt and forward_start_evidence(attempt) == snapshot["start"]
            and stopped_forward_runtime() == snapshot["containers"],
            "forward runtime or launch evidence changed before recording the stop")
    write(marker, dict(receipt_sha256=digest))


def read_forward_stop(attempt):
    require(os.path.lexists(attempt / "forward-stop.json"), "forward stop receipt is required")
    marker = attempt / "forward-stop.json"
    pointer = read(marker)
    digest = pointer["receipt_sha256"]
    return digest, read_forward_stop_receipt(attempt, digest)


def read_forward_stop_receipt(attempt, digest):
    require_match(digest, HEX_SHA256, "invalid forward stop receipt digest")
    raw = (attempt / "forward-stops" / f"{digest}.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == digest, "forward stop history differs")
    return json.loads(raw)


def verify_forward_stop(attempt, schema):
    digest, receipt = read_forward_stop(attempt)
    require_match(receipt["operator_sha256"], HEX_SHA256, "invalid operator record digest")
    current = stopped_forward_runtime()
    abandoned_result = unconfirmed_forward_result_digest(attempt, sealed_receipt(attempt), current)
    require(receipt.get("abandoned_result_sha256") == abandoned_result
            and (not abandoned_result or (receipt.get("abandon_unconfirmed_result") is True
                                          and receipt.get("storage_writes_quiesced") is True)),
            "forward stop does not attest abandonment of the exact unconfirmed result")
    require(receipt["schema_version"] == 1 and receipt["attempt_id"] == attempt.name
            and receipt["seal_sha256"] == attempt_digest(attempt, "no-rollback")
            and receipt["binding_sha256"] == storage_binding_digest()
            and receipt["start"] == forward_start_evidence(attempt)
            and receipt["schema"] == schema and receipt["containers"] == current,
            "forward stop receipt no longer matches the stopped runtime")
    require(read(attempt / "forward-stop.json") == dict(receipt_sha256=digest),
            "forward stop receipt changed during verification")
    sync_directory(attempt)
    return digest


def packaged_schema(image_id):
    return command(
        "docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", image_id,
        "python", "-c", "from twobrain_rec_server.normalization.worker import packaged_schema_head; "
        "print(packaged_schema_head())",
    )


def check_forward_candidate(state, args):
    """Check one built recovery image against the stopped stack, without adopting it."""
    require_match(args.failed_sha, SOURCE_SHA, "invalid failed source SHA")
    require_match(args.source_sha, SOURCE_SHA, "invalid recovery source SHA")
    require(args.source_sha != args.failed_sha, "recovery requires a new source SHA")
    require_match(args.image, SHA256, "recovery image must be pinned")
    command("git", "merge-base", "--is-ancestor", args.failed_sha, args.source_sha)
    schema = check_forward_baseline(state, args.failed_attempt, args.failed_sha)
    media_image = image(args.image, platform(), args.source_sha, target="media-runtime")
    require(packaged_schema(media_image) == schema, "recovery image requires a different database schema")
    require(storage_recovery_state(media_image) == "reconciled", "recovery image did not verify the live storage volume")
    return schema


def stage_forward(state, args):
    """Pin a complete candidate without replacing the unfinished attempt."""
    require_deployment_lock(args.deployment_lock_fd)
    for field, pattern in ((args.attempt_id, ATTEMPT_ID), (args.candidate_id, CANDIDATE_ID),
                           (args.decision_digest, SHA256), (args.full_digest, SHA256),
                           (args.failed_attempt, ATTEMPT_ID)):
        require_match(field, pattern, "invalid forward release evidence identity")
    require_match(args.runtime_image, SHA256, "recovery runtime image must be pinned")
    attempt = state / "attempts" / args.attempt_id
    require(not os.path.lexists(attempt), "deployment attempt is create-once")
    schema = check_forward_candidate(state, args)
    failed = active(state)
    stop_digest = verify_forward_stop(failed, schema)
    baseline = read(failed / "baseline.json")
    failed_candidate = read(failed / "candidate.json")
    target_platform = failed_candidate["platform"]
    # Compose resolves its referenced files from the current checkout even for a git-show input.
    require(not command("git", "diff", "--name-only", "-z", args.failed_sha, args.source_sha, "--", "infra", ".env.example"),
            "forward release changes tracked deployment inputs")
    require(not command("git", "diff", "--name-only", "-z", baseline["source_sha"], args.failed_sha,
                        "--", "infra/env", "infra/minio"),
            "failed release changed referenced infrastructure inputs")
    previous_config = resolved_compose(baseline["source_sha"])
    failed_config = resolved_compose(args.failed_sha)
    fixed_config = resolved_compose(args.source_sha)
    # Reusing the actual infrastructure must not apply new mounts, settings or images.
    for config in (previous_config, failed_config):
        for key in ("networks", "volumes"):
            require(config.get(key) == fixed_config.get(key), "forward release changes storage or network bindings")
        for service in INFRASTRUCTURE_SERVICES:
            require(config["services"][service] == fixed_config["services"][service],
                    "forward release changes infrastructure configuration")
    require(failed_config == fixed_config, "forward release changes Compose configuration")
    service_config = compose_images(fixed_config)
    require(set(service_config) == set(failed_candidate["images"]), "forward release changes the service set")
    observed = containers(reject_active_oneoffs=True)
    require({name for name, row in observed.items() if row["running"]} == INFRASTRUCTURE_SERVICES,
            "runtime changed during forward preparation")
    targets = {"runtime": args.runtime_image, "media-runtime": args.image}
    images = {}
    for service, row in service_config.items():
        if row["target"]:
            pinned = image(targets[row["target"]], target_platform, args.source_sha, target=row["target"])
        else:
            prior = failed_candidate["images"][service]
            require(row["ref"] == prior["ref"] and prior["target"] is None,
                    "forward release changes a third-party image reference")
            pinned = image(observed[service]["image"] if service in INFRASTRUCTURE_SERVICES else prior["image"],
                           target_platform)
        images[service] = dict(row, image=pinned)
    require(check_forward_baseline(state, args.failed_attempt, args.failed_sha) == schema,
            "database schema changed during forward preparation")
    require(containers(reject_active_oneoffs=True) == observed, "runtime changed during forward preparation")
    retain(images)
    require(verify_forward_stop(failed, schema) == stop_digest, "forward stop receipt changed during staging")
    # This file is not a result or an active pointer. The old attempt remains authoritative.
    write(attempt / "forward-stage.json",
          dict(schema_version=1, failed_attempt=failed.name, failed_sha=args.failed_sha,
               seal_sha256=attempt_digest(failed, "no-rollback"), stop_sha256=stop_digest, source_sha=args.source_sha,
               candidate_id=args.candidate_id, decision_digest=args.decision_digest, full_digest=args.full_digest,
               platform=target_platform, schema=schema, images=images,
               infrastructure={name: observed[name] for name in INFRASTRUCTURE_SERVICES},
               compose_sha256=hashlib.sha256(json.dumps(fixed_config, sort_keys=True).encode()).hexdigest()))
    sync_directory(attempt.parent)
    return attempt


def staged_forward_baseline(state, staged, *, checkout_sha=None, expected_active=None):
    """Revalidate the staged record against the still-stopped live stack."""
    failed = state / "attempts" / require_match(staged["failed_attempt"], ATTEMPT_ID, "invalid failed attempt ID")
    require(staged.get("schema_version") == 1
            and attempt_digest(failed, "no-rollback") == staged["seal_sha256"],
            "staged release no longer matches the failed attempt")
    schema = check_forward_baseline(state, failed.name, staged["failed_sha"], checkout_sha=checkout_sha,
                                    expected_active=expected_active)
    require(schema == staged["schema"], "staged database schema changed")
    require(verify_forward_stop(failed, schema) == staged.get("stop_sha256"),
            "staged release no longer matches the forward stop receipt")
    require_match(staged["source_sha"], SOURCE_SHA, "invalid staged source SHA")
    config = resolved_compose(staged["source_sha"])
    require(hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest() == staged["compose_sha256"],
            "staged Compose configuration changed")
    current = containers(reject_active_oneoffs=True)
    running = {name: row for name, row in current.items() if row["running"]}
    require(running == staged["infrastructure"], "staged infrastructure changed")
    services = config["services"]
    bucket = require_match(services["rec-api"]["environment"]["TWOBRAIN_MINIO_BUCKET"], BUCKET,
                           "invalid staged object bucket")
    require(all(services[name]["environment"]["TWOBRAIN_MINIO_BUCKET"] == bucket
                for name in REQUIRED_CONSUMERS | {"rec-minio-init"}), "staged object bucket is inconsistent")
    require(verify_forward_stop(failed, schema) == staged["stop_sha256"],
            "forward stop receipt changed during baseline verification")
    return running, bucket


def backup_contents(root, bucket, rehearsal_copy=None):
    """Fingerprint and sync a complete, private backup without publishing filenames."""
    expected = {"postgres.dump", "schema.sql", "inventory.jsonl", "checksums.sha256",
                "minio-inventory.jsonl", "minio-objects"}
    require(not root.is_symlink() and root.is_dir() and {entry.name for entry in root.iterdir()} == expected,
            "forward backup is incomplete")
    require((root / "minio-objects").is_dir(), "forward backup has no object archive")
    inventory = root / "minio-inventory.jsonl"
    entry = inventory.lstat()
    require(stat.S_ISREG(entry.st_mode) and entry.st_nlink == 1, "forward object inventory is not a regular file")
    object_hashes = {}
    inventory_digest = hashlib.sha256()
    with os.fdopen(os.open(inventory, os.O_RDONLY | os.O_NOFOLLOW), "rb") as lines:
        require(os.path.samestat(entry, os.fstat(lines.fileno())), "forward object inventory changed")
        first = next(lines, b"{}")
        inventory_digest.update(first)
        header = json.loads(first)
        require(isinstance(header, dict) and header.get("schema") == 1 and header.get("bucket") == bucket
                and header.get("versioning") == "disabled" and header.get("incomplete") == 0,
                "invalid forward object inventory")
        for line in lines:
            inventory_digest.update(line)
            row = json.loads(line)
            require(row["key"] not in object_hashes, "duplicate object in forward backup")
            object_hashes[row["key"]] = row["sha256"]
    digest = hashlib.sha256()
    directories = []
    def walk_error(error):
        raise error
    for folder, subdirs, files in os.walk(root, onerror=walk_error):
        directory = Path(folder)
        directories.append(directory)
        subdirs.sort()
        for name in subdirs:
            require(not (directory / name).is_symlink(), "forward backup contains a linked directory")
        require(stat.S_IMODE(directory.stat().st_mode) == 0o700, "forward backup directory is not private")
        digest.update(json.dumps(["directory", directory.relative_to(root).as_posix()]).encode() + b"\n")
        for name in sorted(files):
            path = directory / name
            metadata = path.lstat()
            require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
                    "forward backup contains a non-regular or linked file")
            with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as stream:
                info = os.fstat(stream.fileno())
                require(os.path.samestat(metadata, info) and stat.S_IMODE(info.st_mode) == 0o600
                        and info.st_nlink == 1, "forward backup file is not private")
                content = hashlib.file_digest(stream, "sha256").hexdigest()
                os.fsync(stream.fileno())
                after = os.fstat(stream.fileno())
                require((after.st_size, after.st_mtime_ns) == (info.st_size, info.st_mtime_ns),
                        "forward backup changed while it was verified")
            relative = path.relative_to(root).as_posix()
            if relative.startswith("minio-objects/"):
                require(content == object_hashes.pop(relative.removeprefix("minio-objects/"), None),
                        "forward backup object differs from the pinned source")
            elif relative == "minio-inventory.jsonl":
                require(content == inventory_digest.hexdigest(), "forward object inventory changed")
            if rehearsal_copy is not None and relative in expected - {"minio-objects"}:
                with (rehearsal_copy / relative).open("rb") as stream:
                    require(hashlib.file_digest(stream, "sha256").hexdigest() == content,
                            "rehearsal file differs from the attested backup")
            digest.update(json.dumps(["file", relative, info.st_size, content]).encode() + b"\n")
    require(not object_hashes, "forward backup is missing archived objects")
    for directory in reversed(directories):
        sync_directory(directory)
    sync_directory(root.parent)
    return digest.hexdigest()


def backup_forward(state, args):
    """Make a fresh backup of the exact staged stores, leaving the active pointer unchanged."""
    require_deployment_lock(args.deployment_lock_fd)
    require_match(args.attempt_id, ATTEMPT_ID, "invalid forward attempt ID")
    attempt = state / "attempts" / args.attempt_id
    receipt = attempt / "forward-backup.json"
    require(not os.path.lexists(receipt), "forward backup receipt is create-once")
    stage_digest = attempt_digest(attempt, "forward-stage")
    staged = read(attempt / "forward-stage.json")
    running, bucket = staged_forward_baseline(state, staged)
    backup = args.backup_directory
    require(re.fullmatch(r"/[A-Za-z0-9._/-]+", str(backup)) and backup == backup.resolve() and backup.parent.is_dir()
            and not backup.is_relative_to(state) and not os.path.lexists(backup),
            "forward backup destination must be a new canonical directory outside release state")
    mc_image = require_match(staged["images"]["rec-minio-init"]["image"], SHA256, "backup client image must be pinned")
    image(mc_image, staged["platform"])
    pg_id, minio_id = (require_match(running[name]["id"], CONTAINER_ID, "invalid backup store container")
                       for name in ("rec-postgres", "rec-minio"))
    output = command("sh", "infra/scripts/backup-rec-stack.sh", "--execute", "--pinned-stores", pg_id, minio_id, bucket,
                     env={**os.environ, "TWOBRAIN_BACKUP_DIR": str(backup), "GRAF_RELEASE_MC_IMAGE": mc_image})
    lines = output.splitlines()
    require(lines.count("backup_result=pass") == 1 and lines.count(f"backup_reference={backup}") == 1,
            "backup command did not confirm this destination")
    command("python3", "infra/scripts/rec-db-verify.py", str(backup), "--inventory")
    contents = backup_contents(backup, bucket)
    require(attempt_digest(attempt, "forward-stage") == stage_digest, "staged release changed during backup")
    require(staged_forward_baseline(state, staged) == (running, bucket), "storage changed during backup")
    write(receipt, dict(schema_version=1, attempt_id=attempt.name, stage_sha256=stage_digest,
                        backup_reference=str(backup), bucket=bucket, contents_sha256=contents))
    return receipt


def verify_forward_archive(attempt, backup, stage_digest, rehearsal_copy=None):
    receipt_digest = attempt_digest(attempt, "forward-backup")
    receipt = read(attempt / "forward-backup.json")
    require(backup.is_absolute() and backup == backup.resolve() and receipt.get("schema_version") == 1
            and receipt.get("attempt_id") == attempt.name and receipt.get("stage_sha256") == stage_digest
            and receipt.get("backup_reference") == str(backup), "forward backup receipt does not match")
    bucket = require_match(receipt["bucket"], BUCKET, "invalid forward backup bucket")
    require(backup_contents(backup, bucket, rehearsal_copy) == receipt["contents_sha256"],
            "forward backup archive does not match its receipt")
    require(attempt_digest(attempt, "forward-stage") == stage_digest
            and attempt_digest(attempt, "forward-backup") == receipt_digest,
            "forward evidence changed during archive verification")
    return bucket, receipt_digest


def check_forward_backup(state, args):
    """Revalidate the staged archive and return its pinned rehearsal client."""
    require_deployment_lock(args.deployment_lock_fd)
    require_match(args.attempt_id, ATTEMPT_ID, "invalid forward attempt ID")
    attempt = state / "attempts" / args.attempt_id
    stage_digest = attempt_digest(attempt, "forward-stage")
    staged = read(attempt / "forward-stage.json")
    verify_forward_archive(attempt, args.backup_directory, stage_digest, args.rehearsal_copy)
    mc_image = require_match(staged["images"]["rec-minio-init"]["image"], SHA256, "backup client image must be pinned")
    image(mc_image, staged["platform"])
    return mc_image


def forward_approval_identity(args):
    return dict(source_sha=require_match(args.source_sha, SOURCE_SHA, "invalid recovery source SHA"),
                candidate_id=require_match(args.candidate_id, CANDIDATE_ID, "invalid recovery candidate ID"),
                decision_digest=require_match(args.decision_digest, SHA256, "invalid release decision digest"),
                full_digest=require_match(args.full_digest, SHA256, "invalid Full CI digest"))


def verify_forward_claim(state, args, checkout_sha=None):
    """Check approval and the live baseline without changing either attempt."""
    require_deployment_lock(args.deployment_lock_fd)
    identity = forward_approval_identity(args)
    attempt = state / "attempts" / require_match(args.attempt_id, ATTEMPT_ID, "invalid forward attempt ID")
    failed = state / "attempts" / require_match(args.failed_attempt, ATTEMPT_ID, "invalid failed attempt ID")
    current = active(state)
    require(attempt != failed and current in (failed, attempt) and not os.path.lexists(attempt / "result.json"),
            "forward predecessor is not active or the candidate already has a result")
    stage_digest = attempt_digest(attempt, "forward-stage")
    staged = read(attempt / "forward-stage.json")
    require(staged["failed_attempt"] == failed.name and all(staged[key] == value for key, value in identity.items()),
            "forward approval differs from staging")
    source = identity["source_sha"]
    require(source != staged["failed_sha"], "recovery requires a new source SHA")
    command("git", "merge-base", "--is-ancestor", staged["failed_sha"], source)
    require(checkout_sha in (None, staged["failed_sha"]), "forward preflight requires the failed checkout")
    running, bucket = staged_forward_baseline(state, staged, checkout_sha=checkout_sha or source,
                                              expected_active=current.name)
    prior = sealed_receipt(failed)
    archive_bucket, archive_digest = verify_forward_archive(attempt, args.backup_directory, stage_digest)
    require(archive_bucket == bucket, "forward backup bucket changed")

    prior_candidate = read(failed / "candidate.json")
    config = compose_config(source)
    pinned = staged["images"]
    require(pinned.keys() == config.keys() == prior_candidate["images"].keys(),
            "forward release service set changed")
    target_platform = staged["platform"]
    require(target_platform == prior_candidate["platform"], "forward release platform changed")
    app_images = {}
    for service, row in config.items():
        entry = pinned[service]
        iid = require_match(entry["image"], SHA256, "forward image is not pinned")
        require(entry == dict(row, image=iid), "forward image does not match the service")
        target = row["target"]
        if target is None:
            expected = running[service] if service in running else prior_candidate["images"][service]
            require(iid == expected["image"], "forward infrastructure image changed")
            image(iid, target_platform)
        else:
            require(app_images.setdefault(target, iid) == iid, "forward build target uses different images")
            image(iid, target_platform, source, target=target)
    schema = staged["schema"]
    require(set(app_images) == set(TARGETS) and all(packaged_schema(iid) == schema for iid in app_images.values()),
            "forward image requires a different database schema")
    require(storage_recovery_state(app_images["media-runtime"]) == "reconciled",
            "forward image did not verify the live storage volume")

    baseline = dict(prior_candidate, containers=running)
    candidate = dict(schema_version=1, source_sha=source, platform=target_platform, images=pinned)
    records = {"baseline": baseline, "candidate": candidate, "identity": identity, "override": override(pinned)}
    return attempt, current, records, staged, prior, bucket, stage_digest, archive_digest


def check_forward_claim(state, args):
    """Check the initial handoff only; interrupted claims need their own replay."""
    attempt, current, records, staged, _, bucket, stage_digest, archive_digest = verify_forward_claim(
        state, args, args.checkout_sha)
    adoption_markers = [f"{name}.json" for name in (*records, "start-intent")] + [NO_ROLLBACK]
    require(current.name == staged["failed_attempt"]
            and not any(os.path.lexists(attempt / name) for name in adoption_markers),
            "forward preflight requires a staged attempt before adoption")
    require(verify_forward_archive(attempt, args.backup_directory, stage_digest) == (bucket, archive_digest),
            "forward evidence changed during preflight")
    require(staged_forward_baseline(state, staged, checkout_sha=args.checkout_sha, expected_active=current.name)
            == (records["baseline"]["containers"], bucket), "storage changed during forward preflight")


def claim_forward(state, args):
    """Claim the stopped stack for an already approved candidate; never start services."""
    attempt, current, records, staged, prior, bucket, stage_digest, archive_digest = verify_forward_claim(state, args)
    confirming = current == attempt
    source = records["identity"]["source_sha"]
    schema = staged["schema"]
    for name, value in records.items():
        record = attempt / f"{name}.json"
        if confirming or os.path.lexists(record):
            require(read(record) == value, "interrupted forward claim has different records")
        else:
            write(record, value)
    marker = attempt / NO_ROLLBACK
    seal = dict(schema_version=3, previous_schema=schema, candidate_schema=schema,
                backup_reference=str(args.backup_directory), binding_sha256=prior["binding_sha256"],
                stores_sha256=prior["stores_sha256"], baseline_sha256=attempt_digest(attempt, "baseline"),
                candidate_sha256=attempt_digest(attempt, "candidate"), identity_sha256=attempt_digest(attempt, "identity"),
                forward=dict(previous_attempt=staged["failed_attempt"],
                             original_attempt=prior.get("forward", {}).get("original_attempt", staged["failed_attempt"]),
                             previous_seal_sha256=staged["seal_sha256"], stage_sha256=stage_digest,
                             previous_stop_sha256=staged["stop_sha256"], backup_sha256=archive_digest))
    if confirming or os.path.lexists(marker):
        require(read(marker) == seal, "interrupted forward claim has a different seal")
    else:
        write(marker, seal)
    if not confirming:
        for directory in (attempt, attempt.parent, state):
            sync_directory(directory)
    require(staged_forward_baseline(state, staged, checkout_sha=source, expected_active=current.name)
            == (records["baseline"]["containers"], bucket),
            "storage changed during forward claim")
    require(sealed_receipt(attempt) == seal, "forward seal changed during claim")
    require(verify_forward_archive(attempt, args.backup_directory, stage_digest) == (bucket, archive_digest),
            "forward evidence changed during claim")
    if confirming:
        sync_directory(state)
    else:
        write(state / "active.json", dict(attempt=attempt.name))
    return attempt


def forward_launch_configuration(attempt, staged, *, compose=None):
    """Return the only Compose overlay allowed at first launch, without secrets."""
    expected = resolved_compose(staged["source_sha"], timeout=20)
    require(hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest() == staged["compose_sha256"],
            "staged Compose configuration changed before launch")
    launch = validate_override(attempt / "override.json")
    require(launch == override(staged["images"]), "forward launch images differ from staging")
    launch["services"]["rec-api"]["environment"] = {NORMALIZATION_ENABLED: "false", NORMALIZATION_DISPATCH: "false"}
    launch["services"][MEDIA_WORKER]["environment"] = {NORMALIZATION_DISPATCH: "false"}
    for name, updates in launch["services"].items():
        service = expected["services"][name]
        service.update(image=updates["image"], pull_policy=updates["pull_policy"])
        if "environment" in updates:
            service["environment"].update(updates["environment"])
    overlay = json.dumps(launch, sort_keys=True)
    actual = json.loads(command(*(compose or FORWARD_COMPOSE), "config", "--format", "json", input=overlay, timeout=20))
    require(actual == expected, "forward launch changes unapproved Compose configuration")
    return overlay, actual


def arm_forward_start(state, args):
    """Accept the first launch boundary, under the caller's continuous release lock."""
    require_deployment_lock(args.deployment_lock_fd)
    proposed = state / "attempts" / require_match(args.attempt_id, ATTEMPT_ID, "invalid forward attempt ID")
    require(not any(os.path.lexists(proposed / f"{name}.json")
                    for name in ("start-intent", "start-boundary", "start-observed")),
            "forward launch was already armed or its journal is incomplete; reconcile before another launch")
    attempt = claim_forward(state, args)
    seal = sealed_receipt(attempt)
    predecessor = state / "attempts" / seal["forward"]["previous_attempt"]
    staged = read(attempt / "forward-stage.json")
    require(attempt_digest(attempt, "forward-stage") == seal["forward"]["stage_sha256"],
            "forward staging changed before launch")
    overlay, _ = forward_launch_configuration(attempt, staged)
    schema = check_forward_baseline(state, predecessor.name, staged["failed_sha"],
                                    checkout_sha=args.source_sha, expected_active=attempt.name)
    stop_digest = verify_forward_stop(predecessor, schema)
    receipt_digest, receipt = read_forward_stop(predecessor)
    stopped = stopped_forward_runtime()
    require(schema == seal["candidate_schema"]
            and stop_digest == receipt_digest == seal["forward"]["previous_stop_sha256"]
            and stopped == receipt["containers"], "forward stopped runtime changed before launch intent")
    write_start_intent(attempt, stopped)
    write_start_boundary(attempt, stopped)
    require(active(state) == attempt and sealed_receipt(attempt) == seal and stopped_forward_runtime() == stopped,
            "forward runtime changed while recording launch intent; reconcile before another launch")
    return attempt, overlay


def same_container(current, recorded):
    return all(current.get(key) == recorded[key] for key in ("id", "image", "running"))


def forward_running(attempt, names, *, allow_restart=False):
    current = containers(reject_active_oneoffs=True, include_start_time=True, timeout=5)
    baseline = read(attempt / "baseline.json")["containers"]
    require({name for name, row in current.items() if row["running"]} == names | INFRASTRUCTURE_SERVICES,
            "forward runtime does not have exactly the expected running services")
    require(all(same_container(current[name], baseline[name]) if allow_restart else current[name] == baseline[name]
                for name in INFRASTRUCTURE_SERVICES), "forward launch changed infrastructure containers")
    candidate = read(attempt / "candidate.json")["images"]
    require(all(current[name]["image"] == candidate[name]["image"] for name in names),
            "forward runtime image differs from the candidate")
    return current


def stop_forward_consumers(attempt, lock_fd):
    """Stop exact project container IDs; only the operator can attest Docker quiescence."""
    require_deployment_lock(lock_fd)
    try:
        save_start_observation(attempt, read(attempt / "candidate.json"),
                               containers(include_start_time=True, timeout=5))
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired):
        print("forward_start_observation=unconfirmed", file=sys.stderr)
    stop_failed = False
    for container in project_container_ids(timeout=5):
        try:
            require_match(container, CONTAINER_ID, "invalid forward container ID")
            row, = json.loads(command("docker", "inspect", container, timeout=5))
            require(row["Id"] == container, "forward cleanup container identity changed")
            labels, status = row["Config"]["Labels"], row["State"]
            if (labels.get("com.docker.compose.project") == PROJECT
                    and labels.get("com.docker.compose.service") in REQUIRED_CONSUMERS
                    and labels.get("com.docker.compose.oneoff", "false").lower() != "true"
                    and any(status.get(key) for key in ("Running", "Paused", "Restarting"))):
                command("docker", "stop", "--time", "10", container, pass_fds=(lock_fd,), timeout=20)
        except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired):
            stop_failed = True
    forward_running(attempt, set())
    require(not stop_failed, "forward consumer stop was not acknowledged")


def forward_probe(observed, name, lock_fd, *argv):
    container = require_match(observed[name]["id"], CONTAINER_ID, "invalid forward probe container ID")
    return command("docker", "exec", container, *argv, pass_fds=(lock_fd,), timeout=45)


def verify_forward_role(observed, name, lock_fd, role):
    output = forward_probe(observed, name, lock_fd, "env", f"TWOBRAIN_EXPECTED_DATABASE_ROLE={role}",
                           "python", "/app/scripts/verify_runtime_database_identity.py")
    expected = {
        "runtime_database_identity_result=pass", f"runtime_database_role={role}",
        "scheduler_function_access=" + ("allowed" if role == "twobrain_rec_media" else "denied"),
        "legacy_maintenance_access=" + ("allowed" if role == "twobrain_rec_maintenance" else "denied"),
    }
    require(len(output.splitlines()) == len(expected) and set(output.splitlines()) == expected,
            f"{name} database role proof is invalid")


def forward_inspect(observed, name, *, healthy):
    container = require_match(observed[name]["id"], CONTAINER_ID, "invalid forward inspection container ID")
    row, = json.loads(command("docker", "inspect", container, timeout=10))
    status = row["State"]
    require(row["Id"] == container and row["Image"] == observed[name]["image"]
            and status["Status"] == "running" and not status["Paused"] and not status["Restarting"]
            and status["StartedAt"] == observed[name].get("started_at", status["StartedAt"])
            and (not healthy or status.get("Health", {}).get("Status") == "healthy")
            and (name in INFRASTRUCTURE_SERVICES or row["RestartCount"] == 0),
            f"{name} container is not ready")
    return row


def verify_forward_env(row, expected):
    env = row["Config"]["Env"]
    require(all([item for item in env if item.split("=", 1)[0] == key] == [f"{key}={value}"]
                for key, value in expected.items()), "forward runtime environment does not match its contract")


def verify_forward_workers(observed, lock_fd):
    temporal = forward_inspect(observed, "rec-temporal", healthy=True)
    require(set(temporal["NetworkSettings"]["Networks"]) == {"twobrain-rec-private", "twobrain-rec-media-private"},
            "forward Temporal network boundary is invalid")
    forward_inspect(observed, "rec-processing-worker", healthy=True)
    forward_inspect(observed, "rec-maintenance", healthy=False)
    media = forward_inspect(observed, MEDIA_WORKER, healthy=True)
    host = media["HostConfig"]
    gid = require_match(os.environ.get("TWOBRAIN_RUNTIME_SECRET_GID") or "1001",
                        re.compile(r"[1-9][0-9]{3,9}"), "invalid forward runtime secret group")
    require(media["Config"]["User"] == "twobrain"
            and set(media["NetworkSettings"]["Networks"]) == {"twobrain-rec-media-private"}
            and all(host[key] == value for key, value in dict(GroupAdd=[gid], ReadonlyRootfs=True,
                    NanoCpus=1_000_000_000, Memory=1_073_741_824, PidsLimit=128,
                    CapDrop=["ALL"], SecurityOpt=["no-new-privileges:true"]).items()),
            "forward media worker runtime boundary is invalid")
    verify_forward_env(media, {
        NORMALIZATION_DISPATCH: "false",
        "TWOBRAIN_PLAYBACK_NORMALIZATION_TASK_QUEUE": "twobrain-rec-playback-normalization",
        "TWOBRAIN_PLAYBACK_NORMALIZATION_WORKER_CONCURRENCY": "1",
        "TWOBRAIN_MINIO_ACCESS_KEY_FILE": "/run/secrets/twobrain_minio_media_access_key",
        "TWOBRAIN_MINIO_SECRET_KEY_FILE": "/run/secrets/twobrain_minio_media_secret_key",
        "TWOBRAIN_WEB_RUNTIME_ENABLED": "false",
    })
    for service, role in (("rec-processing-worker", "twobrain_rec_app"),
                          ("rec-maintenance", "twobrain_rec_maintenance"), (MEDIA_WORKER, "twobrain_rec_media")):
        verify_forward_role(observed, service, lock_fd, role)
    for service, script, argv in (
        ("rec-processing-worker", "verify_processing_worker_ready.py", ()),
        (MEDIA_WORKER, "verify_playback_normalization_worker_ready.py", ("--control",)),
    ):
        receipt = json.loads(forward_probe(observed, service, lock_fd, "python", f"/app/scripts/{script}", *argv),
                             object_pairs_hook=unique_json_fields)
        expected = dict(result="pass", workflow_poller="ready", activity_poller="ready")
        if service == MEDIA_WORKER:
            expected.update(mode="control", profile_version="review_m4a_aac_lc_48k_mono_64k_v1",
                            validation_version="playback_validator_v1")
        require(isinstance(receipt, dict) and all(receipt.get(key) == value for key, value in expected.items()),
                f"{service} queue readiness proof is invalid")


def verify_forward_api(observed, lock_fd):
    api = forward_inspect(observed, "rec-api", healthy=True)
    require(api["HostConfig"].get("IpcMode") == "private",
            "forward API requires private container memory for smoke material")
    verify_forward_env(api, {NORMALIZATION_ENABLED: "false", NORMALIZATION_DISPATCH: "false"})
    verify_forward_role(observed, "rec-api", lock_fd, "twobrain_rec_app")
    output = forward_probe(observed, "rec-api", lock_fd, "python", "-c",
                           "from http.client import HTTPConnection\n"
                           "connection = HTTPConnection('127.0.0.1', 8080, timeout=8)\n"
                           "connection.request('GET', '/api/v1/health/ready')\n"
                           "response = connection.getresponse()\n"
                           "if response.status != 200: raise SystemExit(1)\n"
                           "body = response.read(1025)\n"
                           "if len(body) > 1024: raise SystemExit(1)\n"
                           "print(body.decode())")
    require(json.loads(output, object_pairs_hook=unique_json_fields) == {"status": "ready"},
            "forward API readiness proof is invalid")


def approved_forward_channel(args):
    """Bind already published macOS bytes to this recovery decision."""
    with os.fdopen(os.open(args.public_channel, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "public channel approval must be a regular file")
        raw = stream.read(4097)
    require(len(raw) <= 4096 and "sha256:" + hashlib.sha256(raw).hexdigest() == args.public_channel_digest,
            "public channel approval digest is invalid")
    record = json.loads(raw, object_pairs_hook=unique_json_fields)
    validate_forward_channel(record)
    require(all(record[key] == value for key, value in dict(source_sha=args.source_sha, candidate_id=args.candidate_id,
                decision_digest=args.decision_digest).items()), "public channel approval does not match the release decision")
    return record


def validate_forward_channel(record):
    identity = {"schema_version", "source_sha", "candidate_id", "decision_digest"}
    fields = {"origin", "version", "pkg_sha256", "pkg_bytes", "appcast_sha256", "archive_sha256", "archive_bytes"}
    require(isinstance(record, dict) and record.keys() == identity | fields
            and type(record["schema_version"]) is int and record["schema_version"] == 1, "invalid public channel record")
    for key, pattern in (("source_sha", SOURCE_SHA), ("candidate_id", CANDIDATE_ID), ("decision_digest", SHA256)):
        require_match(record[key], pattern, "invalid public channel decision identity")
    origin = require_match(record["origin"], re.compile(r"https://[a-zA-Z0-9.-]+(?::[1-9][0-9]{0,4})?"),
                           "public channel requires a bare HTTPS origin")
    require(urlsplit(origin).port != 0
            and origin == os.environ.get("TWOBRAIN_PUBLIC_BASE_URL", "https://rec.2brain.pro").rstrip("/"),
            "public channel origin differs from the configured public address")
    require_match(record["version"], re.compile(r"[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]{1,5}"),
                  "public macOS version is invalid")
    for field in ("pkg_sha256", "appcast_sha256", "archive_sha256"):
        require_match(record[field], HEX_SHA256, "public asset digest is invalid")
    for field in ("pkg_bytes", "archive_bytes"):
        require(type(record[field]) is int and 0 < record[field] <= 1024**3, "public asset size is invalid")


def forward_public_get(origin, path, limit, *, digest=None, immutable=False):
    """Bound a direct TLS request; never follow redirects or save installers."""
    def expired(_signum, _frame):
        raise ValueError("public response deadline exceeded")

    # This release command owns the main thread; socket timeouts alone do not bound slow headers.
    require(signal.getitimer(signal.ITIMER_REAL) == (0, 0), "another release deadline is already active")
    previous_handler = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, PUBLIC_GET_DEADLINE)
        return read_forward_public_response(origin, path, limit, digest, immutable)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def read_forward_public_response(origin, path, limit, digest, immutable):
    base = urlsplit(origin)
    content, size, sha = bytearray(), 0, hashlib.sha256()
    with closing(HTTPSConnection(base.hostname, base.port, timeout=8)) as connection:
        connection.request("GET", path, headers={"Accept-Encoding": "identity"})
        with connection.getresponse() as response:
            require(response.status == 200 and response.getheader("Content-Encoding") in (None, "identity"),
                    "public recovery endpoint did not return a direct HTTP 200")
            length = response.getheader("Content-Length")
            if length is not None:
                require(length.isascii() and length.isdigit() and int(length) <= limit
                        and response.getheader("Transfer-Encoding") is None,
                        "public response exceeds its approved size")
            if immutable:
                policy = {value.strip().lower() for value in (response.getheader("Cache-Control") or "").split(",")}
                require({"public", "max-age=31536000", "immutable"} <= policy
                        and not policy & {"private", "no-store", "no-cache"}, "public package cache policy differs")
            while True:
                chunk = response.read1(min(65536, limit - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                require(size <= limit, "public response exceeds its approved size")
                if digest is None:
                    content.extend(chunk)
                else:
                    sha.update(chunk)
            require(length is None or size == int(length), "public response ended before its declared size")
    if digest is not None:
        require(size == limit and sha.hexdigest() == digest, "public asset differs from its approved bytes")
    return bytes(content)


def verify_forward_public(channel):
    origin = channel["origin"]
    for route, status in (("live", "ok"), ("ready", "ready")):
        body = forward_public_get(origin, f"/api/v1/health/{route}", 1024)
        require(json.loads(body, object_pairs_hook=unique_json_fields) == {"status": status},
                f"public {route} check failed")
    prefix = "/static/public/downloads/"
    package = f'{prefix}graf.pkg?v={channel["pkg_sha256"][:12]}'
    class DownloadLinks(HTMLParser):
        approved = False

        def handle_starttag(self, tag, attrs):
            hrefs = [value for key, value in attrs if key == "href"]
            require(tag != "base" or not hrefs, "public download page changes the link base")
            if tag == "a":
                require(package not in hrefs or hrefs == [package], "public package link is ambiguous")
                self.approved |= hrefs == [package]

    links = DownloadLinks()
    links.feed(forward_public_get(origin, "/download", 1024**2).decode("utf-8"))
    links.close()
    require(links.approved, "public page does not link the approved macOS package")
    forward_public_get(origin, package, channel["pkg_bytes"], digest=channel["pkg_sha256"], immutable=True)
    feed = forward_public_get(origin, f"{prefix}graf-appcast.xml", 1024**2)
    require(hashlib.sha256(feed).hexdigest() == channel["appcast_sha256"]
            and b"<!DOCTYPE" not in feed and b"<!ENTITY" not in feed, "public Sparkle feed differs from approval")
    enclosure = ElementTree.fromstring(feed).find("./channel/item/enclosure")
    archive = f'{prefix}GRAF-{channel["version"]}.zip'
    require(enclosure is not None and enclosure.get("url") == origin + archive
            and enclosure.get("length") == str(channel["archive_bytes"])
            and enclosure.get("{http://www.andymatuschak.org/xml-namespaces/sparkle}edSignature"),
            "public Sparkle archive link differs from approval")
    forward_public_get(origin, archive, channel["archive_bytes"], digest=channel["archive_sha256"])


def verify_forward_public_process(channel, lock_fd):
    # The parent deadline also bounds native DNS calls inside the verifier.
    command(sys.executable, str(Path(__file__).resolve()), "verify-public-channel",
            input=json.dumps(channel), pass_fds=(lock_fd,), timeout=PUBLIC_PROOF_DEADLINE)


def check_forward_smoke(state, lock_fd, attempt_id, run_id, origin, api, media, maintenance):
    require_deployment_lock(lock_fd)
    attempt = active(state)
    require(attempt.name == attempt_id and not os.path.lexists(attempt / "result.json"),
            "forward smoke requires the unfinished active attempt")
    seal = sealed_receipt(attempt)
    require("forward" in seal, "forward smoke requires an adopted recovery attempt")
    start_boundary_evidence(attempt, start_intent_digest(attempt))
    require(read(attempt / "forward-smoke-intent.json") == {"run_id": run_id, "origin": origin},
            "forward smoke does not match the recorded intent")
    started = attempt / "forward-smoke-started.json"
    require(not any(os.path.lexists(path) for path in (started, attempt / "forward-smoke.json")),
            "forward smoke was already started")
    observed = forward_running(attempt, REQUIRED_CONSUMERS)
    require((api, media, maintenance) == tuple(observed[name]["id"]
            for name in ("rec-api", MEDIA_WORKER, "rec-maintenance")), "forward smoke container IDs changed")
    write(started, {"run_id": run_id})


def forward_smoke_result(raw, run_id):
    require(len(raw) <= 8192, "forward smoke proof is too large")
    proof = json.loads(raw, object_pairs_hook=unique_json_fields)
    require(isinstance(proof, dict) and proof.keys() == {"run_id", "upload", "auth_cleanup", "cleanup"}
            and proof["run_id"] == run_id, "forward smoke run does not match")
    upload = proof["upload"]
    require(isinstance(upload, dict) and upload.get("meeting_status") == "ingested_pending_processing"
            and type(upload.get("uploaded_parts")) is int and upload["uploaded_parts"] == 3,
            "forward smoke upload was not finalized")
    for field in ("meeting_id", "session_id", "media_revision_id"):
        require_match(upload.get(field), re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"),
                      "forward smoke upload identity is invalid")
    for key, field in (("auth_cleanup", "auth_cleanup_result"), ("cleanup", "cleanup_result")):
        cleanup = proof[key]
        require(isinstance(cleanup, dict) and cleanup.get("run_id") == run_id
                and cleanup.get(field) == "pass", "forward smoke cleanup was not confirmed")
    for field in ("database_records_removed", "object_keys_removed"):
        require(type(proof["cleanup"].get(field)) is int and proof["cleanup"][field] > 0,
                "forward smoke cleanup removed no finalized upload artifacts")
    return forward_smoke_receipt(run_id)


def forward_smoke_receipt(run_id):
    return {"run_id": run_id, "upload": "finalized", "auth_cleanup": "pass", "artifact_cleanup": "pass"}


def verify_forward_smoke(attempt, observed, channel, lock_fd):
    run_id = f"forward-{uuid4().hex}"
    origin = channel["origin"]
    write(attempt / "forward-smoke-intent.json", {"run_id": run_id, "origin": origin})
    # Bound the whole shell process group, with a short grace period for its EXIT cleanup.
    raw = command("timeout", "--kill-after=30s", "180s",
                  "infra/scripts/run-production-smoke.sh", "--forward", str(lock_fd), attempt.name, run_id, origin,
                  *(observed[name]["id"] for name in ("rec-api", MEDIA_WORKER, "rec-maintenance")),
                  pass_fds=(lock_fd,), timeout=220)
    require(read(attempt / "forward-smoke-started.json") == {"run_id": run_id},
            "forward smoke start was not recorded")
    return forward_smoke_result(raw, run_id)


def direct_forward_compose():
    # The Docker CLI starts Compose as a grandchild and may close extra FDs.
    plugin = Path(command("docker", "info", "--format",
                          '{{range .ClientInfo.Plugins}}{{if eq .Name "compose"}}{{.Path}}{{end}}{{end}}', timeout=20))
    require(plugin.is_absolute() and plugin.name == "docker-compose" and os.access(plugin, os.X_OK),
            "Docker Compose plugin is unavailable")
    return (str(plugin), *FORWARD_COMPOSE[2:])


def verify_forward_smoke_cleanup(attempt, run_id):
    marker = attempt / "forward-smoke-cleanup.json"
    require(marker.is_file(), "forward smoke cleanup is unknown; reconcile the previous run after Docker quiescence")
    started = attempt_digest(attempt, "forward-smoke-started")
    intent = read(attempt / "forward-smoke-cleanup-intent.json")
    stop = read_forward_stop_receipt(attempt, intent["stop_sha256"])
    require(stop.get("docker_operations_quiesced") is True and stop.get("storage_writes_quiesced") is True
            and stop.get("forward-smoke-started_sha256") == started
            and stop["attempt_id"] == attempt.name and stop["seal_sha256"] == attempt_digest(attempt, "no-rollback")
            and intent["run_id"] == run_id and intent["started_sha256"] == started
            and read(marker) == dict(run_id=run_id, cleanup="pass",
                                     intent_sha256=attempt_digest(attempt, "forward-smoke-cleanup-intent")),
            "forward smoke cleanup does not match the exact run")
    sync_directory(attempt)


def reconcile_forward_smoke(state, args):
    """Clear an interrupted synthetic run without starting any release consumer."""
    attempt, proposal, stopped = forward_stop_snapshot(state, args)
    stop_digest = verify_forward_stop(attempt, stopped["schema"])
    _, stop = read_forward_stop(attempt)
    seal = sealed_receipt(attempt)
    require("forward" in seal, "smoke cleanup requires an adopted forward attempt")
    run_id = require_match(read(attempt / "forward-smoke-started.json")["run_id"],
                           re.compile(r"forward-[0-9a-f]{32}"), "invalid forward smoke run")
    require(read(attempt / "forward-smoke-intent.json")["run_id"] == run_id,
            "forward smoke run does not match the recorded intent")
    require(not os.path.lexists(attempt / "forward-smoke.json"), "forward smoke already has a complete receipt")
    if os.path.lexists(attempt / "forward-smoke-cleanup.json"):
        verify_forward_smoke_cleanup(attempt, run_id)
        return
    require(stop.get("docker_operations_quiesced") is True and stop.get("storage_writes_quiesced") is True
            and stop["snapshot_sha256"] == proposal["snapshot_sha256"], "fresh operator stop receipt is required")
    stage = read(attempt / "forward-stage.json")
    require(attempt_digest(attempt, "forward-stage") == seal["forward"]["stage_sha256"],
            "forward staging changed before smoke cleanup")
    compose = direct_forward_compose()
    _, config = forward_launch_configuration(attempt, stage, compose=compose)
    maintenance = config["services"]["rec-maintenance"]
    image(maintenance["image"], stage["platform"], args.failed_sha, target="runtime")
    # Only the pinned maintenance service is executable; its networks must already exist.
    maintenance.pop("build")
    maintenance.pop("depends_on", None)
    maintenance["restart"] = "no"
    config["services"] = {"rec-maintenance": maintenance}
    config["networks"] = {name: dict(name=config["networks"][name]["name"], external=True)
                          for name in maintenance["networks"]}
    config["volumes"] = {mount["source"]: dict(name=config["volumes"][mount["source"]]["name"], external=True)
                         for mount in maintenance["volumes"] if mount["type"] == "volume"}
    config["secrets"] = {secret["source"]: config["secrets"][secret["source"]] for secret in maintenance["secrets"]}
    intent_path = attempt / "forward-smoke-cleanup-intent.json"
    require(stopped_forward_runtime() == stopped["containers"] and active(state) == attempt,
            "forward runtime changed before smoke cleanup")
    lock_fd = args.deployment_lock_fd
    require_deployment_lock(lock_fd)
    write(intent_path, dict(run_id=run_id, stop_sha256=stop_digest,
                            started_sha256=attempt_digest(attempt, "forward-smoke-started")))
    # After an interrupted command the new intent changes the stop snapshot; get a fresh attestation.
    raw = command(compose[0], "-f", "-", "run", "--no-deps", "--pull", "never", "--rm", "-T",
                  "--name", f"graf-cleanup-{run_id}-{stop_digest[:12]}", "--entrypoint", "sh", "rec-maintenance", "-ec",
                  "TWOBRAIN_EXPECTED_DATABASE_ROLE=twobrain_rec_maintenance "
                  "python /app/scripts/verify_runtime_database_identity.py >/dev/null; "
                  "exec python /app/scripts/cleanup_smoke_artifacts.py --execute --reconcile-interrupted --run-id \"$1\"",
                  "_", run_id, input=json.dumps(config), pass_fds=(lock_fd,), timeout=180)
    require(len(raw) <= 8192, "forward smoke cleanup proof is too large")
    result = json.loads(raw, object_pairs_hook=unique_json_fields)
    require(isinstance(result, dict) and result.get("run_id") == run_id
            and result.get("cleanup_result") == "pass" and result.get("residue_records") == [],
            "forward smoke cleanup did not prove an empty synthetic workspace")
    require(active(state) == attempt and read_forward_stop(attempt)[0] == stop_digest
            and stopped_forward_runtime() == stopped["containers"]
            and check_forward_baseline(state, attempt.name, args.failed_sha, allow_pending_smoke=True) == stopped["schema"],
            "forward runtime changed during smoke cleanup")
    write(attempt / "forward-smoke-cleanup.json", dict(run_id=run_id, cleanup="pass",
                                                      intent_sha256=attempt_digest(attempt, "forward-smoke-cleanup-intent")))


def forward_result_record(attempt, observed, channel_digest):
    require_match(channel_digest, SHA256, "invalid forward channel digest")
    smoke = read(attempt / "forward-smoke.json")
    run_id = require_match(smoke["run_id"], re.compile(r"forward-[0-9a-f]{32}"), "invalid forward smoke run")
    require(smoke == forward_smoke_receipt(run_id)
            and read(attempt / "forward-smoke-started.json") == {"run_id": run_id}
            and read(attempt / "forward-smoke-intent.json")["run_id"] == run_id,
            "forward result is missing exact smoke evidence")
    start = forward_start_evidence(attempt)
    require("boundary_sha256" in start, "forward result is missing the launch boundary")
    return dict(result="deployed", forward=dict(
        schema_version=1, attempt_id=attempt.name, seal_sha256=attempt_digest(attempt, "no-rollback"),
        start=start, smoke={name: attempt_digest(attempt, name)
                            for name in ("forward-smoke-intent", "forward-smoke-started", "forward-smoke")},
        channel_sha256=channel_digest,
        containers={name: observed[name] for name in REQUIRED_DEPLOYED_SERVICES},
    ))


def verify_forward_result_record(attempt, seal):
    require("forward" in seal, "result does not belong to a forward recovery")
    require(attempt_digest(attempt, "forward-stage") == seal["forward"]["stage_sha256"]
            and attempt_digest(attempt, "forward-backup") == seal["forward"]["backup_sha256"],
            "forward result staging or backup receipt differs")
    record = read(attempt / "result.json")
    evidence = record["forward"]
    observed = evidence["containers"]
    require(observed.keys() == REQUIRED_DEPLOYED_SERVICES, "forward result does not identify the running stack")
    baseline = read(attempt / "baseline.json")["containers"]
    candidate = read(attempt / "candidate.json")["images"]
    for name, row in observed.items():
        require_match(row["id"], CONTAINER_ID, "invalid forward result container ID")
        require(row["running"] is True and row["image"] == candidate[name]["image"],
                "forward result does not pin the candidate image")
        if name in INFRASTRUCTURE_SERVICES:
            require(row == baseline[name], "forward result changes infrastructure")
        else:
            require_match(row["started_at"], DOCKER_START_TIME, "invalid forward result container start time")
    require(record == forward_result_record(attempt, observed, evidence["channel_sha256"]),
            "forward result does not match its launch and smoke evidence")
    return record


def unconfirmed_forward_result_digest(attempt, seal, stopped=None):
    if not os.path.lexists(attempt / "result.json"):
        return None
    require("forward" in seal and not os.path.lexists(attempt / "forward-result-confirmed.json"),
            "failed attempt already has a result")
    record = verify_forward_result_record(attempt, seal)
    if stopped is not None:
        require(all(same_container(stopped[name], record["forward"]["containers"][name])
                    for name in INFRASTRUCTURE_SERVICES), "unconfirmed result infrastructure containers changed")
    return attempt_digest(attempt, "result")


def acknowledge_forward_result(attempt, record):
    require(read(attempt / "result.json") == record, "forward result changed before acknowledgement")
    sync_directory(attempt)
    expected = dict(result_sha256=attempt_digest(attempt, "result"))
    marker = attempt / "forward-result-confirmed.json"
    if os.path.lexists(marker):
        require(read(marker) == expected, "forward result acknowledgement differs")
    else:
        write(marker, expected)


def verify_forward_ready_storage(observed, seal):
    require(observed_storage(observed, timeout=15) == (seal["stores_sha256"], seal["candidate_schema"])
            and storage_binding_digest() == seal["binding_sha256"]
            and storage_recovery_state(observed[MEDIA_WORKER]["image"], timeout=20) == "reconciled",
            "forward runtime changed storage identity or schema")


def verify_forward_result_approval(attempt, args, seal, record):
    require(read(attempt / "identity.json") == forward_approval_identity(args)
            and seal["forward"]["previous_attempt"] == args.failed_attempt
            and record["forward"]["channel_sha256"] == args.public_channel_digest
            and read(attempt / "forward-backup.json")["backup_reference"] == str(args.backup_directory),
            "forward result does not match the approved recovery")


def verify_forward_release_approval(args):
    identity = forward_approval_identity(args)

    def approved_bytes(path, digest):
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
            require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "release approval must be a regular file")
            raw = stream.read(1024**2 + 1)
        require(len(raw) <= 1024**2 and "sha256:" + hashlib.sha256(raw).hexdigest() == digest,
                "release approval bytes differ from the approved digest")
        value = json.loads(raw, object_pairs_hook=unique_json_fields)
        require(isinstance(value, dict), "invalid release approval record")
        return value

    decision = approved_bytes(args.release_decision, identity["decision_digest"])
    evidence = approved_bytes(args.full_evidence, identity["full_digest"])
    require(decision.get("status") == "go" and decision.get("full_evidence_digest") == identity["full_digest"]
            and decision.get("source_sha") == evidence.get("requested_sha") == identity["source_sha"]
            and decision.get("candidate_id") == evidence.get("candidate_id") == identity["candidate_id"]
            and evidence.get("lane") == "full" and evidence.get("authoritative_full") is True,
            "forward release lacks an exact go decision and authoritative Full CI")
    validator = command("git", "show", f"{identity['source_sha']}:scripts/validate-ci-evidence.py", timeout=10)
    namespace = {"__name__": "graf_forward_ci_evidence"}
    exec(compile(validator, "validate-ci-evidence.py", "exec"), namespace)
    require(not namespace["validate"](evidence), "forward authoritative Full CI evidence was refused")


def check_forward_execution(state, args):
    """Verify the permitted transition before moving the clean remote checkout."""
    require_deployment_lock(args.deployment_lock_fd)
    require_exact_source(args.checkout_sha)
    verify_forward_release_approval(args)
    approved_forward_channel(args)
    attempt = state / "attempts" / require_match(args.attempt_id, ATTEMPT_ID, "invalid forward attempt ID")
    if os.path.lexists(attempt / "result.json"):
        require(active(state) == attempt and args.checkout_sha == args.source_sha,
                "forward result requires its active exact checkout")
        seal = sealed_receipt(attempt)
        verify_forward_result_approval(attempt, args, seal, verify_forward_result_record(attempt, seal))
        return
    require(not any(os.path.lexists(attempt / f"{name}.json")
                    for name in ("start-intent", "start-boundary", "start-observed")),
            "forward launch was already armed; reconcile before another launch")
    verify_forward_claim(state, args, None if args.checkout_sha == args.source_sha else args.checkout_sha)


def confirm_forward_result(state, attempt, args, channel):
    lock_fd = args.deployment_lock_fd
    require_deployment_lock(lock_fd)
    require(active(state) == attempt, "forward result is not the active attempt")
    require_exact_source(args.source_sha)
    seal = sealed_receipt(attempt)
    record = verify_forward_result_record(attempt, seal)
    verify_forward_result_approval(attempt, args, seal, record)
    if os.path.lexists(attempt / "forward-stop.json"):
        _, stop = read_forward_stop(attempt)
        require(not stop.get("abandoned_result_sha256"), "forward result was abandoned after verified stop")
    observed = forward_running(attempt, REQUIRED_CONSUMERS)
    require({name: observed[name] for name in REQUIRED_DEPLOYED_SERVICES} == record["forward"]["containers"],
            "running forward release differs from its result")
    verify_forward_workers(observed, lock_fd)
    verify_forward_api(observed, lock_fd)
    verify_forward_public_process(channel, lock_fd)
    verify_forward_ready_storage(observed, seal)
    require(active(state) == attempt and sealed_receipt(attempt) == seal
            and verify_forward_result_record(attempt, seal) == record
            and forward_running(attempt, REQUIRED_CONSUMERS) == observed, "forward result changed during confirmation")
    acknowledge_forward_result(attempt, record)
    return attempt


def start_forward(state, args):
    """Start once, or revalidate a recorded result without starting anything."""
    lock_fd = args.deployment_lock_fd
    require_deployment_lock(lock_fd)
    channel = approved_forward_channel(args)
    proposed = state / "attempts" / require_match(args.attempt_id, ATTEMPT_ID, "invalid forward attempt ID")
    if os.path.lexists(proposed / "result.json"):
        return confirm_forward_result(state, proposed, args, channel)
    compose = direct_forward_compose()
    attempt, overlay = arm_forward_start(state, args)
    seal = sealed_receipt(attempt)
    staged = read(attempt / "forward-stage.json")
    require(attempt_digest(attempt, "forward-stage") == seal["forward"]["stage_sha256"],
            "forward staging changed after recording launch intent")
    workers = REQUIRED_CONSUMERS - {"rec-api"}
    previous = set()
    observed = forward_running(attempt, previous)
    _, stopped = start_boundary_evidence(attempt, start_intent_digest(attempt))
    require(stopped == {name: {"id": row["id"], "started_at": row["started_at"]}
                        for name, row in observed.items() if name in REQUIRED_CONSUMERS},
            "forward stopped consumers changed before launch")
    launched = False
    try:
        for services in (workers, {"rec-api"}):
            require(forward_launch_configuration(attempt, staged, compose=compose)[0] == overlay, "forward launch override changed")
            direct_ids = command(*compose, "ps", "--no-trunc", "-q", *sorted(INFRASTRUCTURE_SERVICES),
                                 input=overlay, timeout=10).splitlines()
            require(set(direct_ids) == {observed[name]["id"] for name in INFRASTRUCTURE_SERVICES},
                    "direct Compose does not see the verified infrastructure")
            require(forward_running(attempt, previous) == observed, "forward runtime changed before launch")
            require_deployment_lock(lock_fd)
            launched = True
            command(*compose, "up", "--no-deps", "--no-build", "--pull", "never", "-d", "--wait",
                    "--wait-timeout", "240", *sorted(services), input=overlay, pass_fds=(lock_fd,), timeout=300)
            after = forward_running(attempt, previous | services)
            require(all(after[name] == observed[name] for name in previous),
                    "verified forward workers changed during API startup")
            previous |= services
            observed = after
            ready = verify_forward_workers if services == workers else verify_forward_api
            ready(observed, lock_fd)
        verify_forward_public_process(channel, lock_fd)
        smoke = verify_forward_smoke(attempt, observed, channel, lock_fd)
        write(attempt / "forward-smoke.json", smoke)
        verify_forward_workers(observed, lock_fd)
        verify_forward_api(observed, lock_fd)
        verify_forward_ready_storage(observed, seal)
        require(active(state) == attempt and sealed_receipt(attempt) == seal
                and forward_running(attempt, previous) == observed, "forward runtime changed during readiness")
        record = forward_result_record(attempt, observed, args.public_channel_digest)
        write(attempt / "result.json", record, keep_unconfirmed_result=True)
        acknowledge_forward_result(attempt, record)
    except BaseException:
        if not launched:
            raise
        if os.path.lexists(attempt / "result.json"):
            print("forward_result=confirmation_required", file=sys.stderr)
            raise
        try:
            stop_forward_consumers(attempt, lock_fd)
            print("forward_consumers=stopped_observed", file=sys.stderr)
        except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired):
            print("forward_consumers=stop_unconfirmed", file=sys.stderr)
        print("forward_docker_quiescence=operator_reconciliation_required", file=sys.stderr)
        raise
    return attempt


def verify_finished_runtime(attempt, result, baseline):
    current = verify(attempt, RESULTS[result])
    required = {name for name, row in baseline["containers"].items() if row["running"]}
    if result == "restored":
        required.discard(MEDIA_WORKER)  # Existing safe-processing rollback deliberately disables media.
    else:
        required.update(REQUIRED_DEPLOYED_SERVICES)
    require(required <= {name for name, row in current.items() if row["running"]},
            "recovered runtime is incomplete")


def finish(state, result, attempt_id):
    """Write the one terminal result of this attempt, and only after verification."""
    require(result in RESULTS, "unknown deployment outcome")
    attempt = active(state)
    require(attempt.name == attempt_id, "cannot finish another deployment attempt")
    require(not (attempt / "result.json").exists(), "deployment result is create-once")
    if os.path.lexists(attempt / NO_ROLLBACK):
        require(result == "deployed", "activated deployment requires forward recovery")
        require("forward" not in sealed_receipt(attempt), "forward claim has no runtime completion path")
    baseline = read(attempt / "baseline.json")
    if result == "unchanged":
        require(containers() == baseline["containers"], "runtime changed during preparation")
    else:
        verify_finished_runtime(attempt, result, baseline)
    write(attempt / "result.json", dict(result=result))
    # Keep active.json: only this durable result permits the next locked attempt.


def current_override():
    """The pinned override of the runtime that is live now, or None before the first deploy."""
    state = state_dir()
    if not os.path.lexists(state / "active.json"):
        return None  # First transition: the existing standalone Compose contract still applies.
    attempt = active(state)
    side = completed_side(attempt)
    data = read(attempt / SIDES[side]["record"])
    require(data["source_sha"] == command("git", "rev-parse", "HEAD"),
            "standalone source differs from deployed images")
    verify(attempt, side)
    path = attempt / SIDES[side]["override"]
    validate_override(path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("verify-public-channel")
    lock_args = commands.add_parser("check-deployment-lock")
    lock_args.add_argument("--deployment-lock-fd", type=int, required=True)
    smoke_args = commands.add_parser("check-forward-smoke")
    smoke_args.add_argument("deployment_lock_fd", type=int)
    for field in ("attempt_id", "run_id", "origin", "api", "media", "maintenance"):
        smoke_args.add_argument(field)
    prepare_args = commands.add_parser("prepare")
    for field in ("source-sha", "previous-sha", "candidate-id", "decision-digest", "full-digest"):
        prepare_args.add_argument("--" + field, required=True)
    prepare_args.add_argument("--attempt-id", required=True)
    preflight_args = commands.add_parser("check-predecessor")
    preflight_args.add_argument("--previous-sha", required=True)
    storage_args = commands.add_parser("storage-state")
    storage_args.add_argument("--image", required=True)
    recovery_args = commands.add_parser("check-forward-baseline")
    recovery_args.add_argument("--failed-attempt", required=True)
    recovery_args.add_argument("--failed-sha", required=True)
    forward_args = commands.add_parser("check-forward-candidate")
    for field in ("failed-attempt", "failed-sha", "source-sha", "image"):
        forward_args.add_argument("--" + field, required=True)
    claim_check = commands.add_parser("check-forward-claim")
    for field in ("failed-attempt", "source-sha", "checkout-sha", "attempt-id", "candidate-id",
                  "decision-digest", "full-digest"):
        claim_check.add_argument("--" + field, required=True)
    claim_check.add_argument("--deployment-lock-fd", type=int, required=True)
    claim_check.add_argument("--backup-directory", type=Path, required=True)
    for operation in ("check-forward-execution", "start-forward", "confirm-forward"):
        forward_execute = commands.add_parser(operation)
        for field in ("failed-attempt", "source-sha", "attempt-id", "candidate-id",
                      "decision-digest", "full-digest", "public-channel-digest"):
            forward_execute.add_argument("--" + field, required=True)
        for field in ("backup-directory", "public-channel", "release-decision", "full-evidence"):
            forward_execute.add_argument("--" + field, type=Path, required=True)
        forward_execute.add_argument("--deployment-lock-fd", type=int, required=True)
        if operation == "check-forward-execution":
            forward_execute.add_argument("--checkout-sha", required=True)
    stage_args = commands.add_parser("stage-forward")
    for field in ("failed-attempt", "failed-sha", "source-sha", "image", "runtime-image",
                  "attempt-id", "candidate-id", "decision-digest", "full-digest"):
        stage_args.add_argument("--" + field, required=True)
    stage_args.add_argument("--deployment-lock-fd", type=int, required=True)
    for operation in ("check-forward-stop", "record-forward-stop", "reconcile-forward-smoke"):
        stop_args = commands.add_parser(operation)
        stop_args.add_argument("--failed-attempt", required=True)
        stop_args.add_argument("--failed-sha", required=True)
        stop_args.add_argument("--deployment-lock-fd", type=int, required=True)
        if operation == "record-forward-stop":
            stop_args.add_argument("--operator-record", type=Path, required=True)
    for operation in ("backup-forward", "check-forward-backup"):
        backup_args = commands.add_parser(operation)
        backup_args.add_argument("--attempt-id", required=True)
        backup_args.add_argument("--deployment-lock-fd", type=int, required=True)
        backup_args.add_argument("--backup-directory", type=Path, required=True)
        if operation == "check-forward-backup":
            backup_args.add_argument("--rehearsal-copy", type=Path, required=True)
    verify_args = commands.add_parser("verify")
    verify_args.add_argument("side", choices=tuple(SIDES))
    verify_args.add_argument("services", nargs="*")
    finish_args = commands.add_parser("finish")
    finish_args.add_argument("result", choices=tuple(RESULTS))
    finish_args.add_argument("--attempt-id", required=True)
    seal_args = commands.add_parser("forbid-rollback")
    seal_args.add_argument("--attempt-id", required=True)
    seal_args.add_argument("--previous-schema", required=True)
    seal_args.add_argument("--candidate-schema", required=True)
    seal_args.add_argument("--backup-reference", type=Path, required=True)
    for operation in ("record-start-intent", "record-start-boundary", "observe-start"):
        start_args = commands.add_parser(operation)
        start_args.add_argument("--attempt-id", required=True)
        start_args.add_argument("--deployment-lock-fd", type=int, required=True)
    image_args = commands.add_parser("image")
    image_args.add_argument("side", choices=tuple(SIDES))
    image_args.add_argument("service")
    override_args = commands.add_parser("validate-override")
    override_args.add_argument("path", type=Path)
    current_args = commands.add_parser("current-override")
    current_args.add_argument("--service")
    args = parser.parse_args()
    try:
        if args.operation == "verify-public-channel":
            raw = sys.stdin.buffer.read(4097)
            require(len(raw) <= 4096, "public channel record is too large")
            channel = json.loads(raw, object_pairs_hook=unique_json_fields)
            validate_forward_channel(channel)
            verify_forward_public(channel)
        elif args.operation == "check-deployment-lock":
            require_deployment_lock(args.deployment_lock_fd)
        elif args.operation == "check-forward-smoke":
            check_forward_smoke(state_dir(), args.deployment_lock_fd, args.attempt_id, args.run_id, args.origin,
                                args.api, args.media, args.maintenance)
        elif args.operation == "prepare":
            prepare(args)
        elif args.operation == "check-predecessor":
            require_match(args.previous_sha, SOURCE_SHA, "invalid source SHA")
            recorded_images(state_dir(), args.previous_sha)
        elif args.operation == "storage-state":
            print(storage_recovery_state(args.image))
        elif args.operation == "check-forward-baseline":
            print(check_forward_baseline(state_dir(), args.failed_attempt, args.failed_sha))
        elif args.operation == "check-forward-candidate":
            print(check_forward_candidate(state_dir(), args))
        elif args.operation == "check-forward-claim":
            require_match(args.checkout_sha, SOURCE_SHA, "invalid recovery checkout SHA")
            check_forward_claim(state_dir(), args)
            print("forward_claim_verified")
        elif args.operation == "check-forward-execution":
            check_forward_execution(state_dir(), args)
            print("forward_execution_verified")
        elif args.operation in ("start-forward", "confirm-forward"):
            require(os.environ.get("TWOBRAIN_PRODUCTION_RELEASE_GATE") == "1",
                    "forward start requires the common release gate")

            interrupted = False

            def terminate(_signum, _frame):
                nonlocal interrupted
                if not interrupted:
                    interrupted = True
                    raise InterruptedError("forward launch interrupted")

            for interrupt in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
                signal.signal(interrupt, terminate)
            require_deployment_lock(args.deployment_lock_fd)
            require_exact_source(args.source_sha)
            verify_forward_release_approval(args)
            state = state_dir()
            if args.operation == "confirm-forward":
                attempt = state / "attempts" / require_match(args.attempt_id, ATTEMPT_ID, "invalid forward attempt ID")
                confirm_forward_result(state, attempt, args, approved_forward_channel(args))
                print("forward_confirm_result=pass")
            else:
                start_forward(state, args)
                print("forward_execute_result=pass")
        elif args.operation == "stage-forward":
            print(stage_forward(state_dir(), args))
        elif args.operation == "check-forward-stop":
            print(json.dumps(forward_stop_snapshot(state_dir(), args)[1], sort_keys=True))
        elif args.operation == "record-forward-stop":
            record_forward_stop(state_dir(), args)
        elif args.operation == "reconcile-forward-smoke":
            reconcile_forward_smoke(state_dir(), args)
            print("forward_smoke_cleanup_result=pass")
        elif args.operation == "backup-forward":
            print(backup_forward(state_dir(), args))
        elif args.operation == "check-forward-backup":
            print(check_forward_backup(state_dir(), args))
        elif args.operation == "record-start-intent":
            record_start_intent(state_dir(), args.attempt_id, args.deployment_lock_fd)
        elif args.operation == "record-start-boundary":
            record_start_boundary(state_dir(), args.attempt_id, args.deployment_lock_fd)
        elif args.operation == "observe-start":
            observe_start(state_dir(), args.attempt_id, args.deployment_lock_fd)
        elif args.operation == "validate-override":
            validate_override(args.path)
        elif args.operation == "current-override":
            path = current_override()
            if path is None:
                print("")
            elif args.service:
                print(pinned_image(path, args.service))
            else:
                print(path)
        else:
            state = state_dir()
            attempt = active(state)
            if args.operation == "verify":
                verify(attempt, args.side, args.services)
            elif args.operation == "finish":
                finish(state, args.result, args.attempt_id)
            elif args.operation == "forbid-rollback":
                forbid_rollback(attempt, args)
            else:
                print(pinned_image(attempt / SIDES[args.side]["override"], args.service))
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        detail = "operation timed out; reconcile runtime before retry" if isinstance(error, subprocess.TimeoutExpired) else error
        print(f"release-images: {args.operation} refused: {detail}; "
              "no unverified image is published and any recorded baseline is retained", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
