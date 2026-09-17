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
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SOURCE_LABEL = "org.2brain.graf.dev.source-sha"
PROJECT = "twobrain-rec"
MEDIA_WORKER = "rec-media-worker"
# docker build targets that produce the application images.
TARGETS = ("runtime", "media-runtime")
# docker info reports uname architectures, docker image inspect reports Go ones.
ARCHITECTURES = {"x86_64": "amd64", "aarch64": "arm64"}

SOURCE_SHA = re.compile(r"[0-9a-f]{40}")
ATTEMPT_ID = re.compile(r"[0-9a-f]{32}")
SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
SERVICE = re.compile(r"rec-[a-z0-9-]+")
IMAGE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@-]*")
CANDIDATE_ID = re.compile(r"rc-[A-Za-z0-9-]{1,100}")

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


def command(*args, input=None):
    # Compose configuration can contain secret locations: parse it in memory, never log it.
    result = subprocess.run(args, input=input, text=True, capture_output=True)
    require(result.returncode == 0, f"{args[0]} {args[1]} failed")
    return result.stdout.strip()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    """Persist JSON atomically.

    A reader never sees a partial file. A ``result.json`` that could not be
    acknowledged durably is removed again, so an unacknowledged result is never
    read as a finished deployment. Other files keep what replaced them.
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
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError:
        if replaced and path.name == "result.json":
            path.unlink(missing_ok=True)
        raise
    finally:
        Path(temporary).unlink(missing_ok=True)


def state_dir():
    return Path(command("git", "rev-parse", "--git-path", "graf-release-images")).resolve()


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


def image(ref, target_platform, source=None):
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
    return info["Id"]


def compose_config(source):
    """The release services as resolved from that exact commit, without a checkout."""
    text = command("git", "show", f"{source}:infra/docker-compose.yml")
    config = json.loads(command("docker", "compose", "--project-directory", str(Path.cwd() / "infra"),
                                "--profile", "operations", "-f", "-", "config", "--format", "json", input=text))
    require(config.get("name") == PROJECT, "unexpected Compose project")
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


def containers():
    """Every non-one-off container of this Compose project, keyed by service."""
    ids = command("docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}").splitlines()
    if not ids:
        return {}
    observed = {}
    for row in json.loads(command("docker", "inspect", *ids)):
        labels = row["Config"].get("Labels", {})
        require(labels.get("com.docker.compose.project") == PROJECT, "container project mismatch")
        if labels.get("com.docker.compose.oneoff", "false").lower() == "true":
            continue
        name = labels.get("com.docker.compose.service")
        require(name and name not in observed, "missing/ambiguous container service")
        observed[name] = dict(id=row["Id"], image=row["Image"], running=row["State"]["Running"])
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


def recorded_images(state, previous_sha):
    """Images recorded by the completed attempt whose runtime this deploy replaces.

    Only a finished attempt may be replaced, and its record may supply an image ID
    only when it describes exactly this previous source SHA.
    """
    if not (state / "active.json").exists():
        return {}
    prior = active(state)
    result_file = prior / "result.json"
    require(result_file.is_file(), "unfinished deployment requires explicit recovery; baseline retained")
    result = read(result_file).get("result")
    require(result in RESULTS, "unknown deployment outcome")
    data = read(prior / SIDES[RESULTS[result]]["record"])
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


def finish(state, result, attempt_id):
    """Write the one terminal result of this attempt, and only after verification."""
    require(result in RESULTS, "unknown deployment outcome")
    attempt = active(state)
    require(attempt.name == attempt_id, "cannot finish another deployment attempt")
    require(not (attempt / "result.json").exists(), "deployment result is create-once")
    baseline = read(attempt / "baseline.json")
    if result == "unchanged":
        require(containers() == baseline["containers"], "runtime changed during preparation")
    else:
        current = verify(attempt, RESULTS[result])
        required = {name for name, row in baseline["containers"].items() if row["running"]}
        if result == "restored":
            required.discard(MEDIA_WORKER)  # Existing safe-processing rollback deliberately disables media.
        else:
            required.add(MEDIA_WORKER)
        require(required <= {name for name, row in current.items() if row["running"]},
                "recovered runtime is incomplete")
    write(attempt / "result.json", dict(result=result))
    # Keep active.json: only this durable result permits the next locked attempt.


def current_override():
    """The pinned override of the runtime that is live now, or None before the first deploy."""
    state = state_dir()
    if not (state / "active.json").exists():
        return None  # First transition: the existing standalone Compose contract still applies.
    attempt = active(state)
    # An attempt without a result has no live release to describe; reading it must fail.
    result = read(attempt / "result.json")["result"]
    require(result in RESULTS, "unfinished deployment requires recovery")
    side = RESULTS[result]
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
    prepare_args = commands.add_parser("prepare")
    for field in ("source-sha", "previous-sha", "candidate-id", "decision-digest", "full-digest"):
        prepare_args.add_argument("--" + field, required=True)
    prepare_args.add_argument("--attempt-id", required=True)
    verify_args = commands.add_parser("verify")
    verify_args.add_argument("side", choices=tuple(SIDES))
    verify_args.add_argument("services", nargs="*")
    finish_args = commands.add_parser("finish")
    finish_args.add_argument("result", choices=tuple(RESULTS))
    finish_args.add_argument("--attempt-id", required=True)
    image_args = commands.add_parser("image")
    image_args.add_argument("side", choices=tuple(SIDES))
    image_args.add_argument("service")
    override_args = commands.add_parser("validate-override")
    override_args.add_argument("path", type=Path)
    current_args = commands.add_parser("current-override")
    current_args.add_argument("--service")
    args = parser.parse_args()
    try:
        if args.operation == "prepare":
            prepare(args)
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
            else:
                print(pinned_image(attempt / SIDES[args.side]["override"], args.service))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"release-images: {args.operation} refused: {error}; "
              "no unverified image is published and any recorded baseline is retained", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
