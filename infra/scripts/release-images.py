#!/usr/bin/env python3
"""Prepare two local release images and preserve exact rollback IDs under the deploy lock."""
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


def require(value, message):
    if not value:
        raise ValueError(message)


def command(*args, input=None):
    # Compose configuration can contain secret locations: parse it in memory, never log it.
    result = subprocess.run(args, input=input, text=True, capture_output=True)
    require(result.returncode == 0, f"{args[0]} {args[1]} failed")
    return result.stdout.strip()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError:
        # A result is never accepted after a failed persistence acknowledgement.
        if path.name == "result.json" and not Path(temporary).exists():
            path.unlink(missing_ok=True)
        raise
    finally:
        Path(temporary).unlink(missing_ok=True)


def state_dir():
    return Path(command("git", "rev-parse", "--git-path", "graf-release-images")).resolve()


def active(state):
    name = read(state / "active.json")["attempt"]
    require(re.fullmatch(r"[0-9a-f]{32}", name), "invalid attempt identity")
    return state / "attempts" / name


def platform():
    system, arch = command("docker", "info", "--format", "{{.OSType}}/{{.Architecture}}").split("/")
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(arch, arch)
    require(system == "linux" and arch in {"amd64", "arm64"}, "unsupported Docker platform")
    return f"{system}/{arch}"


def image(ref, target_platform, source=None):
    info = json.loads(command("docker", "image", "inspect", ref))[0]
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", info["Id"]), "invalid image ID")
    require(not ref.startswith("sha256:") or info["Id"] == ref, "image ID mismatch")
    require(f"{info['Os']}/{info['Architecture']}" == target_platform, "image platform mismatch")
    if source is not None:
        require(info["Config"].get("Labels", {}).get(SOURCE_LABEL) == source
                and f"GRAF_DEV_SOURCE_SHA={source}" in info["Config"].get("Env", []), "image source mismatch")
    return info["Id"]


def compose_config(source):
    text = command("git", "show", f"{source}:infra/docker-compose.yml")
    config = json.loads(command("docker", "compose", "--project-directory", str(Path.cwd() / "infra"),
                                "--profile", "operations", "-f", "-", "config", "--format", "json", input=text))
    require(config.get("name") == PROJECT, "unexpected Compose project")
    services = {}
    for name, service in config["services"].items():
        require(re.fullmatch(r"rec-[a-z0-9-]+", name), "invalid Compose service")
        build = service.get("build")
        target = None
        if build:
            require(set(build) <= {"context", "dockerfile", "target"}
                    and Path(build["context"]).resolve() == Path.cwd().resolve()
                    and build.get("dockerfile") == "infra/server/Dockerfile", "unsupported release build configuration")
            target = build.get("target", "runtime")
            require(target in {"runtime", "media-runtime"}, "unknown release target")
        ref = service.get("image") or f"{PROJECT}-{name}"
        require(isinstance(ref, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@-]*", ref), "invalid image ref")
        services[name] = dict(ref=ref, target=target)
    require(services and any(s["target"] for s in services.values()), "missing application services")
    return services


def containers():
    ids = command("docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}").splitlines()
    if not ids:
        return {}
    result = {}
    for row in json.loads(command("docker", "inspect", *ids)):
        labels = row["Config"].get("Labels", {})
        require(labels.get("com.docker.compose.project") == PROJECT, "container project mismatch")
        if labels.get("com.docker.compose.oneoff", "false").lower() == "true":
            continue
        name = labels.get("com.docker.compose.service")
        require(name and name not in result, "missing/ambiguous container service")
        result[name] = dict(id=row["Id"], image=row["Image"], running=row["State"]["Running"])
    return result


def override(images):
    return {"services": {name: {"image": row["image"], "pull_policy": "never"} for name, row in images.items()}}


def validate_override(path):
    value = read(path)
    require(set(value) == {"services"} and value["services"], "invalid image override")
    for name, row in value["services"].items():
        require(re.fullmatch(r"rec-[a-z0-9-]+", name) and set(row) == {"image", "pull_policy"}
                and re.fullmatch(r"sha256:[0-9a-f]{64}", row["image"])
                and row["pull_policy"] == "never", "unsafe image override")
    return value


def retain(images):
    for identity in {row["image"] for row in images.values()}:
        command("docker", "image", "tag", identity, f"graf-release/retained:{identity[7:]}")


def prepare(args):
    require(re.fullmatch(r"[0-9a-f]{40}", args.source_sha)
            and re.fullmatch(r"[0-9a-f]{40}", args.previous_sha), "invalid source SHA")
    require(re.fullmatch(r"rc-[A-Za-z0-9-]{1,100}", args.candidate_id), "invalid candidate ID")
    require(re.fullmatch(r"[0-9a-f]{32}", args.attempt_id), "invalid attempt ID")
    require(all(re.fullmatch(r"sha256:[0-9a-f]{64}", value)
                for value in [args.decision_digest, args.full_digest]), "invalid release evidence identity")
    require(command("git", "rev-parse", "HEAD") == args.source_sha, "checkout source mismatch")
    require(not command("git", "status", "--porcelain", "--untracked-files=all"), "dirty release source")
    state = state_dir()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    prior = None
    if (state / "active.json").exists():
        prior = active(state)
        require((prior / "result.json").is_file(), "unfinished deployment requires explicit recovery; baseline retained")
        require(read(prior / "result.json")["result"] in {"deployed", "unchanged", "restored"}, "unknown deployment outcome")
    target_platform = platform()
    old, new = compose_config(args.previous_sha), compose_config(args.source_sha)
    observed = containers()
    require(observed.get("rec-api", {}).get("running") is True, "previous API is not running")
    prior_images = {}
    if prior:
        prior_result = read(prior / "result.json")
        prior_data = read(prior / ("candidate.json" if prior_result["result"] == "deployed" else "baseline.json"))
        if prior_data["source_sha"] == args.previous_sha:
            prior_images = prior_data["images"]
    previous = {}
    for service, row in old.items():
        ref = observed.get(service, {}).get("image") or prior_images.get(service, {}).get("image") or row["ref"]
        previous[service] = dict(row, image=image(ref, target_platform))
    attempt = state / "attempts" / args.attempt_id
    require(not attempt.exists(), "deployment attempt is create-once")
    baseline = dict(schema_version=1, source_sha=args.previous_sha, platform=target_platform,
                    images=previous, containers=observed)
    write(attempt / "baseline.json", baseline)
    write(attempt / "previous.json", override(previous))
    write(attempt / "identity.json", dict(source_sha=args.source_sha, candidate_id=args.candidate_id,
                                          decision_digest=args.decision_digest, full_digest=args.full_digest))
    # Keep the helper across the existing rollback's source reset.
    helper = attempt / "release-images.py"
    with helper.open("xb") as handle:
        handle.write(Path(__file__).read_bytes())
        handle.flush()
        os.fsync(handle.fileno())
    # The deploy lock serializes attempts. A completed predecessor alone may be replaced.
    write(state / "active.json", dict(attempt=attempt.name))
    retain(previous)
    cache = state / "images" / f"{args.source_sha}-{target_platform.replace('/', '-')}.json"
    cached = read(cache) if cache.exists() else None
    if cached:
        require(cached.get("source_sha") == args.source_sha and cached.get("platform") == target_platform,
                "cached image identity mismatch")
        require(set(cached["targets"]) == {"runtime", "media-runtime"}, "incomplete cached targets")
        targets = {name: image(ref, target_platform, args.source_sha) for name, ref in cached["targets"].items()}
    else:
        targets = {}
        for target in ("runtime", "media-runtime"):
            iidfile = attempt / f"{target}.iid"
            command("docker", "build", "--platform", target_platform, "--target", target,
                    "--build-arg", f"GRAF_DEV_SOURCE_SHA={args.source_sha}", "--iidfile", str(iidfile),
                    "-f", "infra/server/Dockerfile", ".")
            targets[target] = image(iidfile.read_text().strip(), target_platform, args.source_sha)
        retain({name: {"image": identity} for name, identity in targets.items()})
    candidate = {}
    for service, row in new.items():
        if row["target"]:
            ref = targets[row["target"]]
        elif service in previous and row["ref"] == previous[service]["ref"]:
            ref = previous[service]["image"]
        else:
            command("docker", "pull", "--platform", target_platform, row["ref"])
            ref = row["ref"]
        candidate[service] = dict(row, image=image(ref, target_platform, args.source_sha if row["target"] else None))
    retain(candidate)
    require(command("git", "rev-parse", "HEAD") == args.source_sha
            and not command("git", "status", "--porcelain", "--untracked-files=all"), "release source changed during preparation")
    if cached is None:
        write(cache, dict(source_sha=args.source_sha, platform=target_platform, targets=targets))
    write(attempt / "candidate.json", dict(schema_version=1, source_sha=args.source_sha,
                                           platform=target_platform, images=candidate))
    write(attempt / "override.json", override(candidate))
    print(attempt)


def verify(attempt, side, services=()):
    data = read(attempt / ("candidate.json" if side == "candidate" else "baseline.json"))
    require(data["platform"] == platform(), "Docker platform changed")
    current = containers()
    names = set(services) or {name for name, row in current.items() if row["running"]}
    require(names, "no runtime containers observed")
    for name in names:
        require(name in data["images"] and current.get(name, {}).get("running") is True
                and current[name]["image"] == data["images"][name]["image"], "runtime image mismatch")
    return current


def finish(state, result, attempt_id):
    attempt = active(state)
    require(attempt.name == attempt_id, "cannot finish another deployment attempt")
    require(not (attempt / "result.json").exists(), "deployment result is create-once")
    baseline = read(attempt / "baseline.json")
    if result == "unchanged":
        require(containers() == baseline["containers"], "runtime changed during preparation")
    else:
        side = "candidate" if result == "deployed" else "previous"
        current = verify(attempt, side)
        required = {name for name, row in baseline["containers"].items() if row["running"]}
        if result == "restored":
            required.discard("rec-media-worker")  # Existing safe-processing rollback deliberately disables media.
        else:
            required.add("rec-media-worker")
        require(required <= {name for name, row in current.items() if row["running"]}, "recovered runtime is incomplete")
    write(attempt / "result.json", dict(result=result))
    # Keep active.json: only this durable result permits the next locked attempt.


def current_override():
    state = state_dir()
    if not (state / "active.json").exists():
        return None  # First transition: the existing standalone Compose contract still applies.
    attempt = active(state)
    result = read(attempt / "result.json")["result"]
    require(result in {"deployed", "unchanged", "restored"}, "unfinished deployment requires recovery")
    candidate = result == "deployed"
    data = read(attempt / ("candidate.json" if candidate else "baseline.json"))
    require(data["source_sha"] == command("git", "rev-parse", "HEAD"), "standalone source differs from deployed images")
    verify(attempt, "candidate" if candidate else "previous")
    path = attempt / ("override.json" if candidate else "previous.json")
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
    verify_args.add_argument("side", choices=("candidate", "previous"))
    verify_args.add_argument("services", nargs="*")
    finish_args = commands.add_parser("finish")
    finish_args.add_argument("result", choices=("deployed", "unchanged", "restored"))
    finish_args.add_argument("--attempt-id", required=True)
    image_args = commands.add_parser("image")
    image_args.add_argument("side", choices=("candidate", "previous"))
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
            print((validate_override(path)["services"][args.service]["image"] if args.service else path) if path else "")
        else:
            state = state_dir()
            attempt = active(state)
            if args.operation == "verify":
                verify(attempt, args.side, args.services)
            elif args.operation == "finish":
                finish(state, args.result, args.attempt_id)
            else:
                path = attempt / ("override.json" if args.side == "candidate" else "previous.json")
                print(validate_override(path)["services"][args.service]["image"])
    except (OSError, ValueError, KeyError, TypeError):
        print("release-images: preparation/identity/state check failed; active baseline retained", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
