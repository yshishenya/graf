#!/usr/bin/env bash
set -euo pipefail

# Metadata-only release-candidate boundary. Freeze is immutable; decide writes
# a separate create-once attestation and never mutates the frozen input.
root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
usage() {
  cat >&2 <<'EOF'
usage:
  release-candidate.sh freeze --sha <exact-HEAD-40-hex> --features <id,id,...> --operator <name> [--train <train.json>] [--output <path>] [--dry-run]
  release-candidate.sh train-freeze --source-sha <post-merge-40-hex> --base-sha <base-40-hex> --prs <number,...> --features <id,id,...> --operator <name> [--synthetic-merge-sha <40-hex>] [--merge-groups <id,...>] [--pr-receipts <ref,...>] [--merge-group-receipts <ref,...>] [--changelog-digest <sha256:...>] [--rollback-target <ref>] [--output <path>] [--dry-run]
  release-candidate.sh train-validate <train.json> [--current]
  release-candidate.sh train-attest <train.json> --candidate <candidate.json> --evidence <full-evidence.json> [--output <path>]
  release-candidate.sh status <candidate.json>
  release-candidate.sh validate <candidate.json> [--current]
  release-candidate.sh decide <candidate.json> --evidence <full-evidence.json> --calver <YYYY.MM.DD.N> [--tag <tag>] [--output <path>]
  release-candidate.sh attest <decision.json> --release-url <url> --release-sha <exact-HEAD-40-hex> --operator <name> [--output <path>]
EOF
}

[[ $# -ge 1 ]] || { usage; exit 2; }
command="$1"; shift

python3 - "$root_dir" "$command" "$@" <<'PY'
import datetime as dt
import atexit
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

# Metadata-only release operations must never materialize bytecode in the
# source tree: the cleanliness gate treats generated files as source drift.
sys.dont_write_bytecode = True

root = pathlib.Path(sys.argv[1]).resolve()
op = sys.argv[2]
args = sys.argv[3:]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CANDIDATE_RE = re.compile(r"^rc-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$")
DECISION_LOCK_RE = re.compile(
    r"^\.dev/release/decisions/\.rc-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}\.decision\.lock$"
)
CALVER_RE = re.compile(r"^v?[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$")
TAG_RE = re.compile(r"^v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$")
REQUIRED = (
    "schema_version", "candidate_id", "source_sha", "train_id", "included_feature_ids",
    "changelog_digest", "frozen_at", "frozen_by", "status", "full_run_id",
    "full_evidence_digest", "calver", "tag", "github_release_url",
    "rollback_target", "known_limitations", "decision", "decision_reason",
)
SCHEMA_PATH = root / "infra/release/candidate.schema.json"
CANDIDATE_DIR = root / ".dev" / "release" / "candidates"
DECISION_DIR = root / ".dev" / "release" / "decisions"

def die(message):
    raise SystemExit(f"release-candidate: {message}")

def validate_calver(value, field="calver"):
    if not isinstance(value, str) or not CALVER_RE.fullmatch(value):
        die(f"invalid {field}")
    normalized = "v" + value.lstrip("v")
    year, month, day, _ = normalized[1:].split(".")
    try:
        dt.date(int(year), int(month), int(day))
    except ValueError:
        die(f"invalid {field}: date does not exist")
    return normalized

def load(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        die(f"invalid JSON {path}: {exc}")

def digest(path):
    try:
        return "sha256:" + hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    except OSError as exc:
        die(f"cannot read {path}: {exc}")

def _json_type(value, expected):
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True

def _schema_condition(value, condition):
    # The candidate schema only uses conditions over object properties.  Keep
    # this intentionally small and dependency-free; unsupported keywords fail
    # closed in the normal validator below.
    if not isinstance(value, dict):
        return False
    properties = condition.get("properties", {})
    return all(
        key in value and not _schema_errors(value[key], subschema, "$." + key)
        for key, subschema in properties.items()
    )

def _schema_errors(value, schema, path="$"):
    errors = []
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: does not equal const")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value is not in enum")
    expected = schema.get("type")
    if expected is not None:
        types = expected if isinstance(expected, list) else [expected]
        if not any(_json_type(value, item) for item in types):
            errors.append(f"{path}: expected type {expected}")
            return errors
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required property {key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            errors.extend(f"{path}: unknown property {key}" for key in sorted(set(value) - set(properties)))
        for key, subschema in properties.items():
            if key in value:
                errors.extend(_schema_errors(value[key], subschema, path + "." + key))
    elif isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            errors.append(f"{path}: items are not unique")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(_schema_errors(item, schema["items"], f"{path}[{index}]"))
    elif isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than maxLength")
        if "pattern" in schema:
            try:
                matched = re.search(schema["pattern"], value)
            except re.error as exc:
                errors.append(f"{path}: invalid schema pattern: {exc}")
                matched = True
            if not matched:
                errors.append(f"{path}: does not match pattern")
        if schema.get("format") == "date-time":
            try:
                dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{path}: invalid date-time")
    for branch in schema.get("allOf", []):
        if "if" in branch:
            if _schema_condition(value, branch["if"]) and "then" in branch:
                errors.extend(_schema_errors(value, branch["then"], path))
            elif not _schema_condition(value, branch["if"]) and "else" in branch:
                errors.extend(_schema_errors(value, branch["else"], path))
        else:
            errors.extend(_schema_errors(value, branch, path))
    return errors

def validate_schema(data):
    schema = load(SCHEMA_PATH)
    errors = _schema_errors(data, schema)
    if errors:
        die("candidate schema validation failed: " + "; ".join(errors))

def validate_candidate(data):
    if not isinstance(data, dict):
        die("candidate must be a JSON object")
    validate_schema(data)
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        die("missing fields: " + ", ".join(missing))
    if data["schema_version"] != 1:
        die("schema_version must be 1")
    if not isinstance(data["candidate_id"], str) or not CANDIDATE_RE.fullmatch(data["candidate_id"]):
        die("invalid candidate_id")
    if not isinstance(data["source_sha"], str) or not SHA_RE.fullmatch(data["source_sha"]):
        die("invalid source_sha")
    if data["train_id"] is not None and (not isinstance(data["train_id"], str) or not re.fullmatch(r"train-[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", data["train_id"])):
        die("invalid train_id")
    ids = data["included_feature_ids"]
    if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids) or any(not isinstance(x, str) or not re.fullmatch(r"[0-9]{3,}", x) for x in ids):
        die("included_feature_ids must contain unique numeric strings")
    if not isinstance(data["changelog_digest"], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", data["changelog_digest"]):
        die("invalid changelog_digest")
    if data["status"] not in {"frozen", "go", "no-go", "invalidated"}:
        die("invalid status")
    if not isinstance(data["frozen_by"], str) or not data["frozen_by"].strip():
        die("frozen_by is required")
    if not isinstance(data["rollback_target"], str) or not data["rollback_target"].strip():
        die("rollback_target is required")
    if not isinstance(data["known_limitations"], list) or any(not isinstance(x, str) or not x.strip() for x in data["known_limitations"]):
        die("known_limitations must be a list of non-empty strings")
    for key in ("full_run_id", "full_evidence_digest", "calver", "tag", "github_release_url", "decision"):
        if data[key] is not None and not isinstance(data[key], str):
            die(f"{key} must be string or null")
    if data["full_evidence_digest"] is not None and not re.fullmatch(r"sha256:[0-9a-f]{64}", data["full_evidence_digest"]):
        die("invalid full_evidence_digest")
    if data["calver"] is not None:
        validate_calver(data["calver"])
    if data["tag"] is not None and not TAG_RE.fullmatch(data["tag"]):
        die("invalid tag")
    if data["github_release_url"] is not None and not re.fullmatch(r"https://github\.com/[^/]+/[^/]+/releases/tag/v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+", data["github_release_url"]):
        die("invalid github_release_url")
    if data["decision"] not in {None, "go", "no-go"}:
        die("invalid decision")
    if not isinstance(data["decision_reason"], str) or not data["decision_reason"].strip():
        die("decision_reason is required")
    decision_fields = ("full_run_id", "full_evidence_digest", "calver", "tag", "github_release_url", "decision")
    if data["status"] == "frozen" and any(data[key] is not None for key in decision_fields):
        die("frozen candidate cannot contain a decision")
    if data["status"] == "go" and not all(data[key] for key in ("full_run_id", "full_evidence_digest", "calver", "tag")):
        die("go candidate requires full evidence, CalVer and tag")
    if data["status"] == "go" and data["decision"] != "go":
        die("go candidate requires decision=go")
    if data["status"] in {"no-go", "invalidated"} and data["decision"] != "no-go":
        die(f"{data['status']} candidate requires decision=no-go")

def validate_train(data):
    """Validate the generic train contract without importing third-party code."""
    validator_path = root / "scripts/validate-release-train.py"
    schema_path = root / "infra/release/train.schema.json"
    if not validator_path.is_file() or not schema_path.is_file():
        die("release-train validator or schema is missing")
    spec = importlib.util.spec_from_file_location("release_train_validator", validator_path)
    if spec is None or spec.loader is None:
        die("cannot load release-train validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    errors = module.validate(data)
    if errors:
        die("train manifest validation failed: " + "; ".join(errors))

def parse_csv(value, field):
    if value is None:
        return []
    items = [item.strip() for item in value.split(",") if item.strip()]
    if len(items) != len(set(items)):
        die(f"{field} must not contain duplicates")
    return items

def parse_positive_ints(value, field):
    items = parse_csv(value, field)
    if not items:
        return []
    if any(not re.fullmatch(r"[1-9][0-9]*", item) for item in items):
        die(f"{field} must contain positive numeric values")
    return [int(item) for item in items]

def train_current(data, path, exempt_paths=()):
    require_metadata_identity(path, data.get("train_id"), "train")
    if data["source_sha"] != current_sha():
        die(f"train source SHA {data['source_sha']} differs from current HEAD; train is stale")
    if data["changelog_digest"] != digest(root / "CHANGELOG.md"):
        die("train changelog digest differs from current CHANGELOG.md; train is stale")
    require_clean_source((path, metadata_identity_path(path), *exempt_paths))

def current_sha():
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except subprocess.CalledProcessError as exc:
        die(f"cannot resolve current HEAD: {exc}")

def origin_master_sha():
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--verify", "origin/master^{commit}"],
            text=True,
        ).strip().lower()
    except (OSError, subprocess.CalledProcessError) as exc:
        die(f"cannot resolve origin/master; fetch the release branch before train freeze: {exc}")

def require_current(data, record_path=None, exempt_paths=()):
    if record_path is not None:
        require_metadata_identity(record_path, data.get("candidate_id"), "candidate")
    if data["source_sha"] != current_sha():
        die(f"candidate source SHA {data['source_sha']} differs from current HEAD; candidate is stale")
    if data["changelog_digest"] != digest(root / "CHANGELOG.md"):
        die("candidate changelog digest differs from current CHANGELOG.md; candidate is stale")
    if record_path is not None:
        exempt_paths = (*exempt_paths, metadata_identity_path(record_path))
    require_clean_source(exempt_paths)

def metadata_identity_path(path):
    path = pathlib.Path(path).resolve()
    return path.with_name("." + path.name + ".identity.json")

def require_metadata_identity(path, expected_id, kind):
    """Reject edits to ignored immutable release metadata.

    `.dev` is intentionally ignored, so Git status cannot prove that a
    candidate or train still contains the bytes that were frozen.  The
    create-once sidecar is the local immutable digest anchor for `--current`
    checks; a missing or mismatching sidecar fails closed.
    """
    path = pathlib.Path(path).resolve()
    identity_path = metadata_identity_path(path)
    if not identity_path.is_file():
        die(f"{kind} immutable metadata identity is missing: {identity_path}")
    identity = load(identity_path)
    if identity.get("record_id") != expected_id or identity.get("path") != str(path):
        die(f"{kind} immutable metadata identity does not match {path}")
    expected_digest = identity.get("digest")
    if not isinstance(expected_digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", expected_digest):
        die(f"{kind} immutable metadata identity has an invalid digest")
    if expected_digest != digest(path):
        die(f"{kind} metadata drift detected: {path}")

def github_origin_repo():
    try:
        remote = subprocess.check_output(
            ["git", "-C", str(root), "remote", "get-url", "origin"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        die(f"cannot resolve GitHub origin: {exc}")
    match = re.search(r"github\.com[:/]([^/\s:]+)/([^/\s]+?)(?:\.git)?$", remote)
    if not match:
        die("origin must be a GitHub repository")
    return match.group(1), match.group(2)

def verify_github_full_run(evidence, evidence_path, expected_sha, expected_candidate_id):
    """Bind authoritative evidence to the successful GitHub release-full run."""
    run_match = re.fullmatch(r"github-full-(\d+)", str(evidence.get("run_id", "")))
    if not run_match:
        die("authoritative Full CI run_id must be github-full-<GitHub run id>")
    owner, repo = github_origin_repo()
    repository = f"{owner}/{repo}"
    run_id = run_match.group(1)
    try:
        run = json.loads(subprocess.check_output(
            ["gh", "api", f"repos/{repository}/actions/runs/{run_id}"], text=True
        ))
        artifacts = json.loads(subprocess.check_output(
            ["gh", "api", f"repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100"],
            text=True,
        ))
    except (OSError, subprocess.CalledProcessError, UnicodeError, json.JSONDecodeError) as exc:
        die(f"cannot verify authoritative GitHub Full CI run: {exc}")
    if (
        run.get("name") != "release-full"
        or run.get("event") != "workflow_dispatch"
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or str(run.get("head_sha", "")).lower() != expected_sha
        or run.get("path") != ".github/workflows/release-full.yml"
    ):
        die("authoritative evidence is not bound to a successful exact-SHA GitHub release-full run")
    expected_artifact = f"graf-full-ci-{expected_candidate_id}"
    values = artifacts.get("artifacts", []) if isinstance(artifacts, dict) else []
    matching_artifacts = [item for item in values if (
        isinstance(item, dict)
        and item.get("name") == expected_artifact
        and item.get("expired") is False
        and str(item.get("workflow_run", {}).get("id")) == run_id
    )]
    if len(matching_artifacts) != 1:
        die(f"GitHub run does not contain live authoritative artifact {expected_artifact}")
    try:
        with tempfile.TemporaryDirectory(prefix="graf-release-full-") as temporary:
            subprocess.run(
                ["gh", "run", "download", run_id, "--repo", repository,
                 "--name", expected_artifact, "--dir", temporary],
                check=True, stdout=subprocess.DEVNULL,
            )
            downloaded = list(pathlib.Path(temporary).rglob(f"authoritative-{expected_candidate_id}.json"))
            if len(downloaded) != 1 or downloaded[0].read_bytes() != pathlib.Path(evidence_path).read_bytes():
                die("local authoritative evidence does not match the GitHub release-full artifact")
    except (OSError, subprocess.CalledProcessError) as exc:
        die(f"cannot download authoritative GitHub Full CI artifact: {exc}")

def verify_github_release(release_url, expected_tag, expected_sha):
    """Resolve the published GitHub Release and tag to the approved commit."""
    match = re.fullmatch(
        r"https://github\.com/([^/]+)/([^/]+)/releases/tag/(v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+)",
        release_url,
    )
    if not match or match.group(3) != expected_tag:
        die("release URL must be the GitHub Release URL for the decision tag")
    owner, repo = github_origin_repo()
    if (match.group(1), match.group(2)) != (owner, repo):
        die("release URL repository does not match git origin")
    repository = f"{owner}/{repo}"
    try:
        release = json.loads(subprocess.check_output(
            ["gh", "api", f"repos/{repository}/releases/tags/{expected_tag}"], text=True
        ))
        ref = json.loads(subprocess.check_output(
            ["gh", "api", f"repos/{repository}/git/ref/tags/{expected_tag}"], text=True
        ))
    except (OSError, subprocess.CalledProcessError, UnicodeError, json.JSONDecodeError) as exc:
        die(f"cannot verify published GitHub Release/tag: {exc}")
    if release.get("draft") or release.get("prerelease") or release.get("tag_name") != expected_tag:
        die("GitHub Release is missing, draft, prerelease, or has a different tag")
    title = release.get("name")
    body = release.get("body")
    if not isinstance(title, str) or not title.strip() or not title.startswith(expected_tag):
        die("GitHub Release title must start with the stable release tag")
    if not isinstance(body, str) or not body.strip():
        die("GitHub Release notes are empty")
    note = body.lower()
    required_note_groups = (
        ("измен", "добав", "fixed", "changed"),
        ("провер", "validation", "test", "ci"),
        ("совместим", "миграц", "compatib", "migration"),
        ("огранич", "known limitation", "limitation"),
    )
    if any(not any(marker in note for marker in group) for group in required_note_groups):
        die("GitHub Release notes must include changes, validation, compatibility/migration and limitations")
    if not re.search(r"(?:#\d+|https://github\.com/[^/]+/[^/]+/(?:issues|pull)/\d+)", body):
        die("GitHub Release notes must link related GitHub issues or PRs")
    tag_object = ref.get("object") if isinstance(ref, dict) else None
    if not isinstance(tag_object, dict) or not isinstance(tag_object.get("sha"), str):
        die("GitHub tag reference is malformed")
    resolved_sha = tag_object["sha"]
    if tag_object.get("type") == "tag":
        try:
            tag_data = json.loads(subprocess.check_output(
                ["gh", "api", f"repos/{repository}/git/tags/{resolved_sha}"], text=True
            ))
        except (OSError, subprocess.CalledProcessError, UnicodeError, json.JSONDecodeError) as exc:
            die(f"cannot resolve annotated GitHub tag: {exc}")
        resolved_sha = tag_data.get("object", {}).get("sha")
    if resolved_sha != expected_sha:
        die("published GitHub tag does not resolve to the approved candidate SHA")

def require_clean_source(exempt_paths=()):
    """Reject source-tree drift while allowing explicitly named evidence files."""
    try:
        output = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        die(f"cannot inspect worktree cleanliness: {exc}")
    # Do not treat the whole ignored `.dev/` tree as an exemption.  Release
    # metadata is intentionally kept there, but an arbitrary manifest/config
    # written after freeze must still invalidate the candidate.  Callers name
    # the exact files that are being produced by the current operation.
    allowed = {pathlib.Path(path).resolve() for path in exempt_paths}
    dirty = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        relative = line[3:].strip().split(" -> ", 1)[-1]
        path = (root / relative).resolve()
        # The per-candidate decision lock is created before the current-tree
        # check and is the one transient metadata path that cannot be passed
        # as an output exemption by the caller.  Allow only its exact
        # generated shape; arbitrary `.dev` files remain source drift.
        if path in allowed or DECISION_LOCK_RE.fullmatch(relative):
            continue
        dirty.append(relative)
    if dirty:
        die("source tree is dirty after candidate freeze: " + ", ".join(dirty))

def changelog_calvers():
    try:
        text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError as exc:
        die(f"cannot read CHANGELOG.md: {exc}")
    return {
        "v" + value.lstrip("v")
        for value in re.findall(
            r"^## \[(v?[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+)\]",
            text,
            re.MULTILINE,
        )
    }

def changelog_top_calver():
    try:
        text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError as exc:
        die(f"cannot read CHANGELOG.md: {exc}")
    unreleased = re.search(r"^## \[Unreleased\].*?(?=^## \[|\Z)", text, re.MULTILINE | re.DOTALL)
    remainder = text[unreleased.end():] if unreleased else text
    match = re.search(r"^## \[(v?[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+)\]", remainder, re.MULTILINE)
    return "v" + match.group(1).lstrip("v") if match else None

def tag_is_fresh(tag):
    if subprocess.run(["git", "-C", str(root), "show-ref", "--verify", "--quiet", f"refs/tags/{tag}"]).returncode == 0:
        return False
    try:
        remote = subprocess.run(["git", "-C", str(root), "ls-remote", "--tags", "origin", f"refs/tags/{tag}"],
                                check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return True
    return not bool(remote.stdout.strip())

def feature_exists(feature_id):
    specs = root / "specs"
    if not specs.is_dir():
        return False
    return any(
        path.is_dir() and re.fullmatch(rf"{re.escape(feature_id)}(?:-.+)?", path.name)
        for path in specs.iterdir()
    )

def changelog_feature_ids():
    try:
        text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError as exc:
        die(f"cannot read CHANGELOG.md: {exc}")
    # Only the first prepared release section is part of the candidate. A
    # historical mention must never make an unlisted feature look released.
    match = re.search(r"^## \[Unreleased\].*?(?=^## \[|\Z)", text, re.MULTILINE | re.DOTALL)
    top = match.group(0) if match else text
    first_release = re.search(r"^## \[v?[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+\].*?(?=^## \[|\Z)", text, re.MULTILINE | re.DOTALL)
    if first_release:
        top = first_release.group(0)
    markers = re.findall(r"<!--\s*Release features:\s*(.*?)-->", top, re.IGNORECASE | re.DOTALL)
    if markers:
        return {
            value
            for marker in markers
            for value in re.findall(r"\bF(\d+)\b", marker)
        }
    return set(re.findall(
        r"(?:Фича|Feature|feature_id|feature:)\s*[:#]?\s*`?(\d+)\b",
        top,
        re.IGNORECASE,
    ))

def require_git_commit_relationship(base_sha, synthetic_sha, source_sha):
    for label, value in (("base", base_sha), ("synthetic merge", synthetic_sha), ("source", source_sha)):
        try:
            subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{value}^{{commit}}"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            die(f"train {label} SHA does not resolve to a local commit")
    for descendant_label, descendant in (("synthetic merge", synthetic_sha), ("source", source_sha)):
        if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", base_sha, descendant]).returncode == 0:
            return
    die("train base SHA must be an ancestor of the synthetic merge or source commit")

def decision_identity_path(candidate_id):
    return DECISION_DIR / f".{candidate_id}.decision-identity.json"

def publication_identity_path(candidate_id):
    return DECISION_DIR / f".{candidate_id}.publication-identity.json"

def acquire_decision_lock(candidate_id):
    lock_path = DECISION_DIR / f".{candidate_id}.decision.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = lock_path.open("a+", encoding="utf-8")
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    # Keep the lock inode stable so concurrent operators cannot split the lock
    # by racing an unlink. atexit covers every die()/exception path.
    released = False
    def release():
        nonlocal released
        if released:
            return
        released = True
        with contextlib.suppress(OSError):
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        with contextlib.suppress(OSError):
            lock_handle.close()
    atexit.register(release)
    return release

def write_create_once(path, text):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        die(f"refusing to overwrite existing immutable record {path}")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise

if op in {"status", "validate"}:
    if len(args) not in (1, 2) or (len(args) == 2 and args[1] != "--current"):
        die("status/validate expects <candidate.json> [--current]")
    path = pathlib.Path(args[0]).resolve()
    data = load(path)
    validate_candidate(data)
    if op == "validate" and len(args) == 2:
        require_current(data, pathlib.Path(args[0]).resolve(), exempt_paths=(pathlib.Path(args[0]).resolve(),))
    print("release-candidate: OK" if op == "validate" else json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0)

if op == "train-validate":
    if not args:
        die("train-validate expects a train manifest path")
    if len(args) > 2 or (len(args) == 2 and args[1] != "--current"):
        die("train-validate expects <train.json> [--current]")
    train_path = pathlib.Path(args[0]).resolve()
    train = load(train_path)
    validate_train(train)
    if len(args) == 2:
        train_current(train, train_path)
    print("release-train: OK" if len(args) == 2 else json.dumps(train, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0)

if op == "train-freeze":
    values = {
        "source_sha": None,
        "base_sha": None,
        "synthetic_merge_sha": None,
        "prs": None,
        "features": None,
        "merge_groups": None,
        "pr_receipts": None,
        "merge_group_receipts": None,
        "changelog_digest": None,
        "rollback_target": "previous-successful-release",
        "operator": None,
        "output": None,
        "dry_run": False,
    }
    aliases = {
        "--source-sha": "source_sha",
        "--base-sha": "base_sha",
        "--synthetic-merge-sha": "synthetic_merge_sha",
        "--prs": "prs",
        "--included-prs": "prs",
        "--features": "features",
        "--merge-groups": "merge_groups",
        "--pr-receipts": "pr_receipts",
        "--merge-group-receipts": "merge_group_receipts",
        "--changelog-digest": "changelog_digest",
        "--rollback-target": "rollback_target",
        "--operator": "operator",
        "--output": "output",
    }
    i = 0
    while i < len(args):
        item = args[i]
        if item == "--dry-run":
            values["dry_run"] = True
        elif item in aliases:
            i += 1
            if i >= len(args):
                die(f"{item} requires a value")
            values[aliases[item]] = args[i]
        else:
            die(f"unknown train-freeze option {item}")
        i += 1
    source_sha = (values["source_sha"] or "").lower()
    base_sha = (values["base_sha"] or "").lower()
    synthetic_value = values["synthetic_merge_sha"]
    synthetic_sha = synthetic_value.lower() if isinstance(synthetic_value, str) else None
    if not SHA_RE.fullmatch(source_sha):
        die("train-freeze requires --source-sha with an exact 40-character SHA")
    if not SHA_RE.fullmatch(base_sha):
        die("train-freeze requires --base-sha with an exact 40-character SHA")
    if not SHA_RE.fullmatch(synthetic_sha or ""):
        die("train-freeze requires --synthetic-merge-sha with an exact 40-character SHA")
    if synthetic_sha == source_sha:
        die("source SHA must remain distinct from synthetic merge SHA")
    if not values["operator"] or not str(values["operator"]).strip():
        die("train-freeze requires --operator")
    prs = parse_positive_ints(values["prs"], "--prs")
    features = parse_csv(values["features"], "--features")
    if not prs:
        die("train-freeze requires at least one included PR")
    if not features or any(not re.fullmatch(r"[0-9]{3,}", item) for item in features):
        die("--features must contain unique numeric IDs")
    merge_groups = parse_csv(values["merge_groups"], "--merge-groups")
    receipts = parse_csv(values["pr_receipts"], "--pr-receipts")
    merge_receipts = parse_csv(values["merge_group_receipts"], "--merge-group-receipts")
    if len(receipts) != len(prs):
        die("--pr-receipts must provide one receipt reference for every included PR")
    if len(merge_receipts) != len(merge_groups):
        die("--merge-group-receipts must provide one receipt reference for every merge group")
    if any(not re.fullmatch(r"[A-Za-z0-9._:-]{1,512}", item) for item in receipts + merge_receipts):
        die("receipt references must be bounded metadata identifiers")
    if any(not re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", item) for item in merge_groups):
        die("merge-group IDs must be bounded metadata identifiers")
    if current_sha() != source_sha:
        die("HEAD differs from requested post-merge source SHA")
    if origin_master_sha() != source_sha:
        die("train source SHA must match origin/master")
    require_git_commit_relationship(base_sha, synthetic_sha, source_sha)
    try:
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"], text=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        die(f"cannot inspect worktree cleanliness: {exc}")
    if status:
        die("worktree must be clean before train freeze")
    changelog_digest = values["changelog_digest"] or digest(root / "CHANGELOG.md")
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", changelog_digest):
        die("--changelog-digest must be sha256:<64 hex>")
    if changelog_digest != digest(root / "CHANGELOG.md"):
        die("changelog digest does not match current CHANGELOG.md")
    train_id = "train-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + source_sha[:12]
    train = {
        "schema_version": 1,
        "train_id": train_id,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "operator": str(values["operator"]).strip(),
        "source_sha": source_sha,
        "base_sha": base_sha,
        "synthetic_merge_sha": synthetic_sha,
        "included_prs": prs,
        "feature_ids": sorted(features, key=int),
        "merge_group_ids": merge_groups,
        "pr_receipts": receipts,
        "merge_group_receipts": merge_receipts,
        "changelog_digest": changelog_digest,
        "authoritative_full_ci_receipt": None,
        "decision": "pending",
        "rollback_target": str(values["rollback_target"]).strip(),
    }
    validate_train(train)
    output = pathlib.Path(values["output"] or (root / ".dev/release/trains" / f"{train_id}.json"))
    text = json.dumps(train, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if not values["dry_run"]:
        identity_path = metadata_identity_path(output)
        if identity_path.exists():
            die(f"refusing to overwrite existing immutable metadata identity {identity_path}")
        write_create_once(output, text)
        try:
            write_create_once(identity_path, json.dumps(
                {"record_id": train["train_id"], "path": str(output.resolve()), "digest": digest(output)},
                ensure_ascii=False, indent=2, sort_keys=True,
            ) + "\n")
        except BaseException:
            with contextlib.suppress(OSError):
                output.unlink()
            raise
    raise SystemExit(0)

if op == "train-attest":
    if not args:
        die("train-attest expects train manifest path")
    values = {"train": args[0], "candidate": None, "evidence": None, "output": None}
    i = 1
    while i < len(args):
        item = args[i]
        if item in {"--candidate", "--evidence", "--output"}:
            i += 1
            if i >= len(args):
                die(f"{item} requires a value")
            values[item[2:]] = args[i]
        else:
            die(f"unknown train-attest option {item}")
        i += 1
    if not values["candidate"] or not values["evidence"]:
        die("train-attest requires --candidate and --evidence")
    train_path = pathlib.Path(values["train"]).resolve()
    train = load(train_path)
    validate_train(train)
    train_attestation_identity = DECISION_DIR / f".{train['train_id']}.train-attestation-identity.json"
    train_attestation_lock = acquire_decision_lock(train["train_id"])
    if train_attestation_identity.exists():
        die(f"train already has an immutable attestation identity {train_attestation_identity}")
    if train.get("decision") != "pending":
        die("train-attest accepts only a pending train manifest")
    candidate_path = pathlib.Path(values["candidate"]).resolve()
    candidate = load(candidate_path)
    validate_candidate(candidate)
    if candidate.get("train_id") != train.get("train_id"):
        die("candidate train_id does not match train manifest")
    if candidate.get("source_sha") != train.get("source_sha"):
        die("candidate source SHA does not match train source SHA")
    evidence_path = pathlib.Path(values["evidence"]).resolve()
    canonical_evidence_path = (root / ".dev" / "ci-evidence" / f"authoritative-{candidate['candidate_id']}.json").resolve()
    if evidence_path != canonical_evidence_path:
        die("train attestation requires the candidate's canonical authoritative Full CI evidence path")
    train_current(train, train_path, (candidate_path, evidence_path))
    evidence = load(evidence_path)
    validator = root / "scripts/validate-ci-evidence.py"
    spec = importlib.util.spec_from_file_location("ci_evidence", validator)
    if spec is None or spec.loader is None:
        die("CI evidence validator is missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    errors = module.validate(evidence)
    if evidence.get("candidate_id") != candidate.get("candidate_id"):
        errors.append("evidence candidate_id differs from candidate")
    if evidence.get("requested_sha") != train.get("source_sha"):
        errors.append("evidence requested_sha differs from train source SHA")
    if evidence.get("lane") != "full" or evidence.get("status") != "passed" or evidence.get("authoritative_full") is not True:
        errors.append("train-attest requires passed authoritative Full CI evidence")
    if errors:
        die("cannot attest train: " + "; ".join(errors))
    verify_github_full_run(evidence, evidence_path, train["source_sha"], candidate["candidate_id"])
    output = pathlib.Path(values["output"] or (train_path.parent / f"{train['train_id']}-go.json"))
    receipt = {
        "run_id": evidence["run_id"],
        "receipt_digest": digest(evidence_path),
        "target_sha": evidence["requested_sha"],
        "status": "passed",
        "lane": "full",
    }
    record = dict(train)
    record["authoritative_full_ci_receipt"] = receipt
    record["decision"] = "go"
    validate_train(record)
    if output.exists():
        die(f"refusing to overwrite existing immutable record {output}")
    text = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    identity_path = metadata_identity_path(output)
    if identity_path.exists() or train_attestation_identity.exists():
        die(f"refusing to overwrite existing immutable metadata identity {identity_path}")
    write_create_once(output, text)
    try:
        write_create_once(train_attestation_identity, json.dumps(
            {"record_id": record["train_id"], "path": str(output.resolve()), "digest": digest(output)},
            ensure_ascii=False, indent=2, sort_keys=True,
        ) + "\n")
        write_create_once(identity_path, json.dumps(
            {"record_id": record["train_id"], "path": str(output.resolve()), "digest": digest(output)},
            ensure_ascii=False, indent=2, sort_keys=True,
        ) + "\n")
    except BaseException:
        with contextlib.suppress(OSError):
            output.unlink()
        with contextlib.suppress(OSError):
            train_attestation_identity.unlink()
        raise
    print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0)

if op == "freeze":
    values = {"sha": None, "features": None, "operator": None, "train": None, "output": None, "dry_run": False}
    i = 0
    while i < len(args):
        item = args[i]
        if item == "--sha":
            i += 1; values["sha"] = args[i] if i < len(args) else None
        elif item in {"--features", "--feature-id"}:
            i += 1; values["features"] = args[i] if i < len(args) else None
        elif item == "--operator":
            i += 1; values["operator"] = args[i] if i < len(args) else None
        elif item == "--train":
            i += 1; values["train"] = args[i] if i < len(args) else None
        elif item == "--output":
            i += 1; values["output"] = args[i] if i < len(args) else None
        elif item == "--dry-run":
            values["dry_run"] = True
        else:
            die(f"unknown freeze option {item}")
        i += 1
    sha = (values["sha"] or "").lower()
    if not SHA_RE.fullmatch(sha):
        die("exact 40-character SHA is required")
    if not values["features"] or not values["operator"]:
        die("features and operator are required")
    feature_ids = values["features"].replace(" ", "").split(",")
    if any(not re.fullmatch(r"[0-9]{3,}", item) for item in feature_ids) or len(set(feature_ids)) != len(feature_ids):
        die("features must be a comma-separated list of unique numeric IDs")
    if current_sha() != sha:
        die("HEAD differs from requested SHA")
    status = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"], text=True, capture_output=True, check=True).stdout
    if status:
        die("worktree must be clean before freeze")
    missing_features = [feature_id for feature_id in feature_ids if not feature_exists(feature_id)]
    if missing_features:
        die("cannot freeze nonexistent feature IDs: " + ", ".join(missing_features))
    changelog_features = changelog_feature_ids()
    if set(feature_ids) != changelog_features:
        die(
            "included feature IDs must exactly match the prepared CHANGELOG.md; "
            f"missing={sorted(changelog_features - set(feature_ids), key=int)}, "
            f"extra={sorted(set(feature_ids) - changelog_features, key=int)}"
        )
    train_id = None
    if values["train"]:
        train_path = pathlib.Path(values["train"]).resolve()
        train = load(train_path)
        validate_train(train)
        train_current(train, train_path)
        if train.get("decision") != "pending":
            die("candidate freeze requires a pending train manifest")
        if train.get("source_sha") != sha:
            die("train source SHA differs from candidate SHA")
        train_features = sorted(train.get("feature_ids", []), key=int)
        if train_features != sorted(feature_ids, key=int):
            die("candidate feature IDs must exactly match the release train feature set")
        train_id = train["train_id"]
    candidate_identity = json.dumps(
        {"source_sha": sha, "features": sorted(feature_ids, key=int), "train_id": train_id,
         "changelog_digest": digest(root / "CHANGELOG.md")},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    candidate_stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate_id = f"rc-{candidate_stamp}-{hashlib.sha256(candidate_identity).hexdigest()[:12]}"
    output = pathlib.Path(values["output"] or (CANDIDATE_DIR / f"{candidate_id}.json"))
    candidate = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "source_sha": sha, "train_id": train_id,
        "included_feature_ids": sorted(feature_ids, key=int),
        "changelog_digest": digest(root / "CHANGELOG.md"),
        "frozen_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "frozen_by": values["operator"], "status": "frozen", "full_run_id": None,
        "full_evidence_digest": None, "calver": None, "tag": None, "github_release_url": None,
        "rollback_target": "previous-successful-release",
        "known_limitations": ["Full CI and publication are separate release-operator gates."],
        "decision": None, "decision_reason": "Candidate metadata frozen; Full CI has not run.",
    }
    validate_candidate(candidate)
    text = json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if not values["dry_run"]:
        identity_path = metadata_identity_path(output)
        if identity_path.exists():
            die(f"refusing to overwrite existing immutable metadata identity {identity_path}")
        write_create_once(output, text)
        try:
            write_create_once(identity_path, json.dumps(
                {"record_id": candidate["candidate_id"], "path": str(output.resolve()), "digest": digest(output)},
                ensure_ascii=False, indent=2, sort_keys=True,
            ) + "\n")
        except BaseException:
            with contextlib.suppress(OSError):
                output.unlink()
            raise
    raise SystemExit(0)

if op == "decide":
    if not args:
        die("decide expects candidate path")
    values = {"candidate": args[0], "evidence": None, "calver": None, "tag": None, "train": None, "output": None}
    i = 1
    while i < len(args):
        item = args[i]
        if item in {"--evidence", "--calver", "--tag", "--train", "--output"}:
            i += 1
            if i >= len(args):
                die(f"{item} requires a value")
            values[item[2:]] = args[i]
        else:
            die(f"unknown decide option {item}")
        i += 1
    candidate_path = pathlib.Path(values["candidate"]).resolve()
    candidate = load(candidate_path)
    validate_candidate(candidate)
    if candidate["status"] != "frozen":
        die("only a frozen candidate can receive a decision")
    release_decision_lock = acquire_decision_lock(candidate["candidate_id"])
    # The candidate itself is immutable, so a canonical identity sidecar is the
    # single writer/identity guard. Custom output paths cannot create a second
    # decision in another directory.
    identity_path = decision_identity_path(candidate["candidate_id"])
    if identity_path.exists():
        identity = load(identity_path)
        if identity.get("record_id", identity.get("candidate_id")) != candidate["candidate_id"]:
            die(f"decision identity sidecar belongs to another candidate: {identity_path}")
        die(f"candidate already has an immutable decision identity {identity_path}")
    for existing in DECISION_DIR.glob(f"*{candidate['candidate_id']}*.json"):
        if existing == identity_path:
            continue
        try:
            existing_data = json.loads(existing.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if (isinstance(existing_data, dict)
                and existing_data.get("candidate_id") == candidate["candidate_id"]
                and existing_data.get("decision") in {"go", "no-go"}):
            die(f"candidate already has an immutable decision record {existing}")
    if not values["evidence"]:
        die("--evidence is required")
    train = None
    if candidate.get("train_id") is not None:
        if not values["train"]:
            die("candidate linked to a release train requires --train")
        train_path = pathlib.Path(values["train"]).resolve()
        train = load(train_path)
        validate_train(train)
        train_current(train, train_path)
        if train.get("train_id") != candidate["train_id"]:
            die("train manifest does not match candidate train_id")
        if train.get("source_sha") != candidate["source_sha"]:
            die("train source SHA differs from candidate source SHA")
        if sorted(train.get("feature_ids", []), key=int) != sorted(candidate["included_feature_ids"], key=int):
            die("candidate feature IDs must remain bound to the linked release train")
        receipt = train.get("authoritative_full_ci_receipt")
        if train.get("decision") != "go" or not isinstance(receipt, dict):
            die("linked train must have a go decision with authoritative Full CI receipt")
    evidence_path = pathlib.Path(values["evidence"]).resolve()
    canonical_evidence_path = (root / ".dev" / "ci-evidence" / f"authoritative-{candidate['candidate_id']}.json").resolve()
    if evidence_path != canonical_evidence_path:
        die("release decision requires the candidate's canonical authoritative Full CI evidence path")
    evidence = load(evidence_path)
    errors = []
    if not isinstance(evidence, dict):
        errors.append("evidence must be a JSON object")
    else:
        validator = root / "scripts/validate-ci-evidence.py"
        if validator.is_file():
            spec = importlib.util.spec_from_file_location("ci_evidence", validator)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            errors = module.validate(evidence)
        else:
            errors = ["CI evidence validator is missing"]
        if evidence.get("requested_sha") != candidate["source_sha"]:
            errors.append("evidence requested_sha differs from candidate source_sha")
        if evidence.get("candidate_id") != candidate["candidate_id"]:
            errors.append("evidence candidate_id differs from candidate_id")
        if evidence.get("lane") != "full":
            errors.append("release decision requires lane=full evidence")
        if evidence.get("authoritative_full") is not True:
            errors.append("release decision requires authoritative_full=true evidence")
        if train is not None:
            receipt = train["authoritative_full_ci_receipt"]
            if receipt.get("run_id") != evidence.get("run_id"):
                errors.append("train Full CI receipt run_id differs from evidence")
            if receipt.get("target_sha") != evidence.get("requested_sha"):
                errors.append("train Full CI receipt target differs from evidence")
            if receipt.get("receipt_digest") != digest(evidence_path):
                errors.append("train Full CI receipt digest differs from evidence")
    # Full CI can finish while the operator is preparing the decision.  The
    # candidate must still describe the exact checkout at the point of go/no-go.
    if not errors:
        require_current(
            candidate,
            candidate_path,
            exempt_paths=(
                candidate_path,
                evidence_path,
                DECISION_DIR / f".{candidate['candidate_id']}.decision.lock",
            ),
        )
    decision = "go" if not errors else "no-go"
    calver = values["calver"]
    if decision == "go":
        verify_github_full_run(evidence, evidence_path, candidate["source_sha"], candidate["candidate_id"])
        if not calver:
            die("go requires --calver YYYY.MM.DD.N")
        calver = validate_calver(calver)
        top_calver = changelog_top_calver()
        if calver != top_calver:
            die(f"CalVer {calver} is not bound to a release section in CHANGELOG.md")
        tag = values["tag"] or calver
        if not TAG_RE.fullmatch(tag):
            die("tag must be vYYYY.MM.DD.N")
        if tag != calver:
            die("tag must equal the normalized CalVer")
        if not tag_is_fresh(tag):
            die(f"release tag {tag} already exists locally or on origin")
    else:
        calver = None; tag = None
    output = pathlib.Path(values["output"] or (DECISION_DIR / f"{candidate['candidate_id']}.decision.json"))
    if output.resolve() == candidate_path.resolve():
        die("decision output must be separate from the immutable candidate")
    if decision == "go":
        require_clean_source((candidate_path, metadata_identity_path(candidate_path), evidence_path, output))
    record = dict(candidate)
    record.update({
        "status": decision,
        "full_run_id": evidence.get("run_id") if isinstance(evidence, dict) and isinstance(evidence.get("run_id"), str) else None,
        "full_evidence_digest": digest(evidence_path), "calver": calver, "tag": tag,
        "github_release_url": None, "decision": decision,
        "decision_reason": "Authoritative Full CI passed for frozen candidate." if decision == "go" else "No-go: " + "; ".join(errors),
    })
    validate_candidate(record)
    text = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    identity = json.dumps(
        {"candidate_id": candidate["candidate_id"], "decision": decision, "output": str(output)},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    # Preflight the user-selected destination before creating the canonical
    # identity, avoiding a stranded identity when --output is already present.
    if output.exists():
        die(f"refusing to overwrite existing immutable record {output}")
    output_identity_path = metadata_identity_path(output)
    if output_identity_path.exists():
        die(f"refusing to overwrite existing immutable metadata identity {output_identity_path}")
    try:
        write_create_once(output, text)
        identity_record = {
            "record_id": candidate["candidate_id"],
            "candidate_id": candidate["candidate_id"],
            "path": str(output.resolve()),
            "digest": digest(output),
        }
        identity_text = json.dumps(identity_record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        write_create_once(identity_path, identity_text)
        write_create_once(output_identity_path, identity_text)
    except BaseException:
        with contextlib.suppress(OSError):
            output.unlink()
            identity_path.unlink()
            output_identity_path.unlink()
        raise
    print(text, end="")
    release_decision_lock()
    raise SystemExit(0)

if op == "attest":
    if not args:
        die("attest expects decision path")
    values = {"decision": args[0], "release_url": None, "release_sha": None, "operator": None, "output": None}
    i = 1
    while i < len(args):
        item = args[i]
        if item in {"--release-url", "--release-sha", "--operator", "--output"}:
            i += 1
            if i >= len(args):
                die(f"{item} requires a value")
            values[item[2:].replace("-", "_")] = args[i]
        else:
            die(f"unknown attest option {item}")
        i += 1
    decision_path = pathlib.Path(values["decision"]).resolve()
    decision = load(decision_path)
    validate_candidate(decision)
    if decision["status"] != "go" or decision["decision"] != "go":
        die("publication attestation requires a go decision")
    if not values["release_url"] or not values["release_sha"] or not values["operator"]:
        die("release URL, release SHA and operator are required")
    release_sha = values["release_sha"].lower()
    if not SHA_RE.fullmatch(release_sha) or release_sha != decision["source_sha"]:
        die("release SHA must be the exact candidate source SHA")
    release_url = values["release_url"]
    verify_github_release(release_url, decision["tag"], release_sha)
    release_dir = DECISION_DIR.parent / "attestations"
    output = pathlib.Path(values["output"] or (release_dir / f"{decision['candidate_id']}.publication.json"))
    if output.resolve() == decision_path.resolve():
        die("publication attestation must be separate from the decision")
    release_identity = publication_identity_path(decision["candidate_id"])
    release_identity.parent.mkdir(parents=True, exist_ok=True)
    release_lock = acquire_decision_lock(decision["candidate_id"])
    if release_identity.exists():
        die(f"candidate already has an immutable publication identity {release_identity}")
    if output.exists():
        die(f"refusing to overwrite existing immutable record {output}")
    require_current(decision)
    record = {
        "schema_version": 1,
        "attestation_id": f"pa-{decision['candidate_id']}",
        "candidate_id": decision["candidate_id"],
        "decision_digest": digest(decision_path),
        "source_sha": decision["source_sha"],
        "tag": decision["tag"],
        "github_release_url": release_url,
        "release_target_sha": release_sha,
        "attested_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "attested_by": values["operator"],
    }
    text = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    identity = json.dumps(
        {"candidate_id": decision["candidate_id"], "attestation_id": record["attestation_id"], "output": str(output)},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    write_create_once(release_identity, identity)
    try:
        write_create_once(output, text)
    except BaseException:
        with contextlib.suppress(OSError):
            release_identity.unlink()
        raise
    print(text, end="")
    release_lock()
    raise SystemExit(0)

die(f"unknown command {op}")
PY
