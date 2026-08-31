#!/usr/bin/env bash
set -euo pipefail

# Metadata-only release-candidate boundary. Freeze is immutable; decide writes
# a separate create-once attestation and never mutates the frozen input.
root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
usage() {
  cat >&2 <<'EOF'
usage:
  release-candidate.sh freeze --sha <40-hex> --features <id,id,...> --operator <name> [--output <path>] [--dry-run]
  release-candidate.sh status <candidate.json>
  release-candidate.sh validate <candidate.json> [--current]
  release-candidate.sh decide <candidate.json> --evidence <full-evidence.json> --calver <YYYY.MM.DD.N> [--tag <tag>] [--output <path>]
EOF
}

[[ $# -ge 1 ]] || { usage; exit 2; }
command="$1"; shift

python3 - "$root_dir" "$command" "$@" <<'PY'
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

root = pathlib.Path(sys.argv[1]).resolve()
op = sys.argv[2]
args = sys.argv[3:]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CANDIDATE_RE = re.compile(r"^rc-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$")
CALVER_RE = re.compile(r"^v?[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$")
TAG_RE = re.compile(r"^v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$")
REQUIRED = (
    "schema_version", "candidate_id", "source_sha", "included_feature_ids",
    "changelog_digest", "frozen_at", "frozen_by", "status", "full_run_id",
    "full_evidence_digest", "calver", "tag", "github_release_url",
    "rollback_target", "known_limitations", "decision", "decision_reason",
)
SCHEMA_PATH = root / "infra/release/candidate.schema.json"

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

def current_sha():
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except subprocess.CalledProcessError as exc:
        die(f"cannot resolve current HEAD: {exc}")

def require_current(data):
    if data["source_sha"] != current_sha():
        die(f"candidate source SHA {data['source_sha']} differs from current HEAD; candidate is stale")
    if data["changelog_digest"] != digest(root / "CHANGELOG.md"):
        die("candidate changelog digest differs from current CHANGELOG.md; candidate is stale")

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
        require_current(data)
    print("release-candidate: OK" if op == "validate" else json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0)

if op == "freeze":
    values = {"sha": None, "features": None, "operator": None, "output": None, "dry_run": False}
    i = 0
    while i < len(args):
        item = args[i]
        if item == "--sha":
            i += 1; values["sha"] = args[i] if i < len(args) else None
        elif item in {"--features", "--feature-id"}:
            i += 1; values["features"] = args[i] if i < len(args) else None
        elif item == "--operator":
            i += 1; values["operator"] = args[i] if i < len(args) else None
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
    output = pathlib.Path(values["output"] or (root / "docs/releases/candidates" / f"rc-{sha[:12]}.json"))
    candidate = {
        "schema_version": 1,
        "candidate_id": f"rc-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{sha[:12]}",
        "source_sha": sha, "included_feature_ids": sorted(feature_ids, key=int),
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
        write_create_once(output, text)
    raise SystemExit(0)

if op == "decide":
    if not args:
        die("decide expects candidate path")
    values = {"candidate": args[0], "evidence": None, "calver": None, "tag": None, "output": None}
    i = 1
    while i < len(args):
        item = args[i]
        if item in {"--evidence", "--calver", "--tag", "--output"}:
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
    require_current(candidate)
    if candidate["status"] != "frozen":
        die("only a frozen candidate can receive a decision")
    lock_path = candidate_path.with_suffix(candidate_path.suffix + ".decision.lock")
    lock_handle = lock_path.open("a+", encoding="utf-8")
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    # The candidate itself is immutable, so a canonical identity sidecar is the
    # single writer/identity guard. Custom output paths cannot create a second
    # decision in another directory.
    identity_path = candidate_path.with_name(f".{candidate_path.name}.decision-identity.json")
    if identity_path.exists():
        identity = load(identity_path)
        if identity.get("candidate_id") != candidate["candidate_id"]:
            die(f"decision identity sidecar belongs to another candidate: {identity_path}")
        die(f"candidate already has an immutable decision identity {identity_path}")
    for existing in candidate_path.parent.glob("*.json"):
        if existing == candidate_path:
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
    evidence_path = pathlib.Path(values["evidence"]).resolve()
    evidence = load(evidence_path)
    errors = []
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
    decision = "go" if not errors else "no-go"
    calver = values["calver"]
    if decision == "go":
        if not calver:
            die("go requires --calver YYYY.MM.DD.N")
        calver = validate_calver(calver)
        versions = changelog_calvers()
        if versions and calver not in versions:
            die(f"CalVer {calver} is not bound to a release section in CHANGELOG.md")
        tag = values["tag"] or calver
        if not TAG_RE.fullmatch(tag):
            die("tag must be vYYYY.MM.DD.N")
        if tag != calver:
            die("tag must equal the normalized CalVer")
    else:
        calver = None; tag = None
    output = pathlib.Path(values["output"] or str(candidate_path)[:-5] + ".decision.json")
    record = dict(candidate)
    record.update({
        "status": decision,
        "full_run_id": evidence.get("run_id") if isinstance(evidence.get("run_id"), str) else None,
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
    write_create_once(identity_path, identity)
    write_create_once(output, text)
    print(text, end="")
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    lock_handle.close()
    raise SystemExit(0)

die(f"unknown command {op}")
PY
