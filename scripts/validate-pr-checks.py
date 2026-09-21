#!/usr/bin/env python3
"""Verify one current PR check set, including immutable GitHub artifact identity."""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


metadata = module("validate-pr-metadata")
receipts = module("validate-ci-receipt")
changelog = module("validate-changelog-fragments")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def utc(value):
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None and result.utcoffset() == dt.timedelta(0), "timestamp must be UTC")
    return result


def historical(pr, policy):
    require(isinstance(policy, dict) and set(policy) == {
        "schema_version", "repository", "foundation_pr", "foundation_sha", "activated_at",
    }, "missing or ambiguous PR policy boundary")
    require(policy["schema_version"] == 1 and type(policy["foundation_pr"]) is int
            and policy["foundation_pr"] > 0
            and re.fullmatch(r"[0-9a-f]{40}", policy["foundation_sha"] or ""), "invalid foundation identity")
    activated = utc(policy["activated_at"])
    require(activated <= dt.datetime.now(dt.timezone.utc), "policy activation is in the future")
    return pr.get("merged") is True and utc(pr["merged_at"]) < activated


class PendingProof(ValueError):
    """An identified source run has not reached a terminal outcome."""


def run_identity(repository, workflow, pr, run):
    event = "pull_request_target" if workflow == "pr-metadata" else "pull_request"
    require(run.get("name") == workflow and run.get("path") == f".github/workflows/{workflow}.yml"
            and run.get("event") == event and run.get("head_sha") == pr["head"]["sha"]
            and run.get("repository", {}).get("full_name") == repository,
            f"{workflow}: wrong workflow/event/repository/head")
    require(all(type(run.get(key)) is int and run[key] > 0 for key in ("id", "run_attempt")),
            "invalid run/attempt")


def completed(run):
    if run.get("status") in {"queued", "in_progress", "pending", "waiting", "requested"} and run.get("conclusion") is None:
        raise PendingProof("latest code run is still pending")
    require(run.get("status") == "completed" and run.get("conclusion") == "success",
            "latest code run or gate is not successful")


def job_result(run, name, conclusion="success"):
    matches = [job for job in run.get("jobs", []) if job.get("name") == name]
    require(len(matches) == 1 and matches[0].get("conclusion") == conclusion,
            f"{name}: missing, duplicate or unsuccessful job")


def proof_identity(pr, repository, base, workflow, run, proof):
    run_identity(repository, workflow, pr, run)
    require(isinstance(proof, dict) and str(proof.get("run_id")) == str(run["id"])
            and proof.get("run_attempt") == run["run_attempt"], f"{workflow}: mixed run/attempt")
    require(proof.get("target_sha") == pr["head"]["sha"] and proof.get("base_sha") == base,
            f"{workflow}: stale or mixed head/base")


def scope_identity(pr, repository, base, workflow, run, proof):
    proof_identity(pr, repository, base, workflow, run, proof)
    require(proof.get("repository") == repository and proof.get("event_name") == "pull_request"
            and proof.get("pull_request_numbers") == [pr["number"]]
            and type(proof.get("text_only")) is bool and type(proof.get("native_required")) is bool
            and re.fullmatch(r"[0-9a-f]{64}", proof.get("paths_digest", "")), "unverified text-only/native scope")
    job_result(run, "Determine code scope" if workflow == "governance-fast" else "Determine native scope")


def validate_source(pr, repository, base, workflow, run, proof):
    proof_identity(pr, repository, base, workflow, run, proof)
    completed(run)
    job_result(run, workflow)
    if workflow == "governance-fast":
        require(not receipts.validate(proof), "invalid code receipt")
        require(proof["status"] == "passed" and proof["workflow"] == workflow
                and proof["event_name"] == "pull_request" and proof["pull_request_numbers"] == [pr["number"]]
                and proof["workflow_url"] == f"https://github.com/{repository}/actions/runs/{run['id']}",
                "code receipt identity mismatch")
    else:
        require(workflow == "macos-pr", "unknown source component")
        scope_identity(pr, repository, base, workflow, run, proof)
        require(proof["text_only"] is False, "text result cannot be native source proof")
        job_result(run, "Swift build and tests", "success" if proof["native_required"] else "skipped")


def reference(run, proof):
    return {"run_id": str(run["id"]), "run_attempt": run["run_attempt"],
            "proof_digest": "sha256:" + hashlib.sha256(json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


def validate_bundle(pr, repository, policy, base, bundles):
    """Validate downloaded facts; callers obtain them from GitHub, not user files."""
    current = metadata.metadata_snapshot(pr, repository)
    require(policy["repository"] == repository, "policy repository mismatch")
    old = historical(pr, policy)
    require(set(bundles) == ({"governance-fast"} if old else {"governance-fast", "macos-pr", "pr-metadata"}),
            "incomplete PR check set")
    refs = {}
    for workflow, (run, proof) in bundles.items():
        if workflow != "pr-metadata":
            validate_source(pr, repository, base, workflow, run, proof)
        else:
            proof_identity(pr, repository, base, workflow, run, proof)
            completed(run)
            job_result(run, workflow)
            require(proof.get("result") == "pass" and proof.get("schema_version") == 1
                    and run.get("head_sha") == current["target_sha"]
                    and re.fullmatch(r"[0-9a-f]{40}", proof.get("policy_sha", "")), "untrusted metadata policy")
            metadata._git("merge-base", "--is-ancestor", policy["foundation_sha"], proof["policy_sha"])
            metadata._git("merge-base", "--is-ancestor", proof["policy_sha"], "origin/master")
            stable = ("repository", "pr_number", "target_sha", "base_ref", "head_repository", "commits", "metadata_digest")
            require(all(proof.get(key) == current[key] for key in stable), "stale current PR metadata")
            if proof.get("merged") is True:
                require(pr["merged"] and proof.get("merge_commit_sha") == pr["merge_commit_sha"], "metadata merge mismatch")
            else:
                require(proof.get("merged") is False and proof.get("state") == "open"
                        and proof.get("api_base_sha") == base, "metadata was checked against another base")
        refs[workflow] = reference(run, proof)
    require(not metadata._validate_diff(pr, current["target_sha"], base), "current PR description is invalid")
    return dict(schema_version=1, repository=repository, pr_number=pr["number"],
                target_sha=current["target_sha"], base_sha=base, merge_commit_sha=current["merge_commit_sha"], policy="combined" if old else "separate",
                metadata_digest=current["metadata_digest"], checks=refs)


def api(repository, endpoint, *, pages_key=None):
    args = ["gh", "api", f"repos/{repository}/{endpoint}"]
    if pages_key is not None:
        args += ["--paginate", "--slurp"]
    value = json.loads(subprocess.check_output(args, stderr=subprocess.DEVNULL))
    return [row for page in value for row in (page[pages_key] if pages_key else page)] if pages_key is not None else value


# Downloads are reused only inside one verification; outside one, every call
# reads GitHub again so a stale archive can never be trusted.
_ACTIVE_CACHE = None


@contextlib.contextmanager
def artifact_cache():
    global _ACTIVE_CACHE
    previous = _ACTIVE_CACHE
    _ACTIVE_CACHE = {}
    try:
        yield
    finally:
        _ACTIVE_CACHE = previous


def download_artifact(repository, run, workflow, *, optional=False):
    names = {"governance-fast": f"graf-governance-fast-evidence-{run['id']}-{run['run_attempt']}",
             "code-scope": f"graf-code-scope-{run['id']}-{run['run_attempt']}",
             "macos-pr": f"graf-native-scope-{run['id']}-{run['run_attempt']}",
             "pr-metadata": f"graf-pr-metadata-{run['id']}-{run['run_attempt']}"}
    rows = api(repository, f"actions/runs/{run['id']}/artifacts?per_page=100", pages_key="artifacts")
    matches = [row for row in rows if row.get("name") == names[workflow]]
    if not matches and workflow == "governance-fast":
        # Pre-cutover receipts keep their old name and still need exact attempt validation.
        matches = [row for row in rows if row.get("name") == "graf-governance-fast-evidence"]
    if not matches and optional:
        return None
    require(len(matches) == 1 and matches[0].get("expired") is False, f"{workflow}: missing/expired artifact")
    row = matches[0]
    require(utc(row["expires_at"]) > dt.datetime.now(dt.timezone.utc), "expired artifact timestamp")
    require(row.get("workflow_run", {}).get("id") == run["id"], "artifact run mismatch")
    data = subprocess.check_output(["gh", "api", f"repos/{repository}/actions/artifacts/{row['id']}/zip"], stderr=subprocess.DEVNULL)
    require(len(data) <= 20_000_000, "oversized proof archive")
    filename = {"governance-fast": f"receipt-{run['id']}.json", "code-scope": "code-scope.json", "macos-pr": "native-scope.json", "pr-metadata": "pr-metadata.json"}[workflow]
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = [item for item in archive.infolist() if Path(item.filename).name == filename]
        require(len(files) == 1 and files[0].file_size <= 1_000_000, "missing/oversized/ambiguous proof")
        return json.loads(archive.read(files[0]))


def artifact(repository, run, workflow, *, optional=False):
    """Return one workflow proof archive, downloading each archive at most once.

    A release train verifies every included pull request, and each one needs up
    to four independent archives.  Downloading them one after another spent most
    of the release wall time waiting on the network, so `prefetch_artifacts`
    fetches them at the same time and this function serves the cached result to
    the sequential validation that follows.

    The cache exists only while one verification runs: `verify` and `reuse` open
    it, so a later verification always re-reads GitHub state instead of trusting
    a download made earlier in the same process.
    """
    key = (run["id"], workflow)
    cache = _ACTIVE_CACHE
    if cache is not None and key in cache:
        value = cache[key]
        if isinstance(value, BaseException):
            raise value
        return value
    value = download_artifact(repository, run, workflow, optional=optional)
    if cache is not None:
        cache[key] = value
    return value


def prefetch_artifacts(repository, jobs):
    """Download independent proof archives at the same time.

    `jobs` holds (run, workflow) pairs.  A failed download is cached and
    re-raised by `artifact`, so verification still fails with the same message
    it produced while downloads were sequential.  Archives are fetched strictly
    except the optional scope archive, which may legitimately be absent.
    """
    cache = _ACTIVE_CACHE
    if cache is None:
        return
    pending = {}
    for run, workflow in jobs:
        key = (run["id"], workflow)
        if key not in cache:
            pending[key] = (run, workflow)
    if not pending:
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(pending))) as pool:
        futures = {
            pool.submit(download_artifact, repository, run, workflow,
                        optional=workflow == "code-scope"): key
            for key, (run, workflow) in pending.items()
        }
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                cache[key] = future.result()
            except BaseException as error:  # re-raised by artifact()
                cache[key] = error


def workflow_runs(repository, workflow, pr):
    event = "pull_request_target" if workflow == "pr-metadata" else "pull_request"
    query = f"actions/workflows/{workflow}.yml/runs?event={event}&per_page=100"
    query += f"&head_sha={pr['head']['sha']}"
    runs = api(repository, query, pages_key="workflow_runs")
    for run in sorted(runs, key=lambda row: (utc(row["run_started_at"]), row["id"]), reverse=True):
        numbers = [item.get("number") for item in run.get("pull_requests", [])]
        if numbers and pr["number"] not in numbers:
            continue
        run_identity(repository, workflow, pr, run)
        run["jobs"] = api(repository, f"actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs?per_page=100", pages_key="jobs")
        yield run


def run_scope(repository, workflow, pr, base, run):
    kind = "code-scope" if workflow == "governance-fast" else "macos-pr"
    scope = artifact(repository, run, kind, optional=True)
    if scope is not None:
        scope_identity(pr, repository, base, workflow, run, scope)
    return scope


def current_run(repository, workflow, pr, base):
    for run in workflow_runs(repository, workflow, pr):
        scope = run_scope(repository, workflow, pr, base, run) if workflow != "pr-metadata" else None
        if scope is not None and scope["text_only"]:
            # The scope is already immutable; never wait for another text gate.
            continue
        completed(run)
        proof = scope if workflow == "macos-pr" else artifact(repository, run, workflow)
        proof_identity(pr, repository, base, workflow, run, proof)
        if workflow == "pr-metadata":
            require(proof.get("pr_number") == pr["number"] and proof.get("repository") == repository,
                    "metadata PR identity mismatch")
        else:
            validate_source(pr, repository, base, workflow, run, proof)
        return run, proof
    raise ValueError(f"{workflow}: no current proof")


def current_gate(repository, workflow, pr, base):
    for run in workflow_runs(repository, workflow, pr):
        completed(run)
        job_result(run, workflow)
        scope = run_scope(repository, workflow, pr, base, run) if workflow != "pr-metadata" else None
        if scope is not None and scope["text_only"]:
            return run, scope
        proof = scope if workflow == "macos-pr" else artifact(repository, run, workflow)
        proof_identity(pr, repository, base, workflow, run, proof)
        if workflow == "pr-metadata":
            require(proof.get("pr_number") == pr["number"] and proof.get("repository") == repository
                    and proof.get("result") == "pass", "metadata gate identity mismatch")
        else:
            validate_source(pr, repository, base, workflow, run, proof)
        return run, proof
    raise ValueError(f"{workflow}: no current required gate")


_RELEASE_PREP_FRAGMENT = re.compile(
    r"changes/releases/(v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*)/F[0-9]+\.yaml"
)
_RELEASE_PREP_UNRELEASED_FRAGMENT = re.compile(r"changes/unreleased/F([0-9]+)\.yaml")
_RELEASE_PREP_ARCHIVED_FRAGMENT = re.compile(
    r"changes/releases/(v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*)/F([0-9]+)\.yaml"
)
_RELEASE_PREP_SUBJECT = re.compile(r"(?:release|релиз|выпуск|заметк)", re.IGNORECASE)
_CLOSEOUT_SUBJECT = re.compile(r"^docs\(closeout\):\s+", re.IGNORECASE)
_CLOSEOUT_TASK = re.compile(r"^specs/[0-9]{3,}-[^/]+/tasks\.md$")
_RELEASE_HEADING = re.compile(r"^## \[([0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*)\].*$", re.MULTILINE)
_RELEASE_MARKER = re.compile(r"^<!-- Release features:.*-->$", re.MULTILINE)
_TOP_LEVEL_FIELD = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):", re.MULTILINE)
_RELEASE_PROSE_FIELDS = {"summary", "compatibility", "known_limitations", "release_notes"}
_CALVER = re.compile(r"^v?([0-9]{4})\.([0-9]{2})\.([0-9]{2})\.([1-9][0-9]*)$")
_CREDENTIAL_TOKEN = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b",
    re.IGNORECASE,
)


def _calver_key(value):
    match = _CALVER.fullmatch(value)
    return tuple(int(part) for part in match.groups()) if match else None


def _sensitive_release_text(text):
    return (
        any(token.lower() in text.lower() for token in changelog.FORBIDDEN)
        or changelog.CREDENTIAL_ASSIGNMENT_RE.search(text)
        or _CREDENTIAL_TOKEN.search(text)
    )


def _valid_release_fragment(text, path, version, expected_feature=None):
    fields = _TOP_LEVEL_FIELD.findall(text)
    if len(fields) != len(changelog.REQUIRED) or set(fields) != set(changelog.REQUIRED):
        return None
    if any(not changelog._has_value_or_block(text, field) for field in changelog.REQUIRED):
        return None
    if not re.search(r"[А-Яа-яЁё]", changelog._field_payload(text, "summary")):
        return None
    if not re.search(r"[А-Яа-яЁё]", changelog._field_payload(text, "release_notes")):
        return None
    feature = re.search(r"^feature_id[ \t]*:[ \t]*(\d+)[ \t]*$", text, re.MULTILINE)
    path_feature = re.search(r"/F([0-9]+)\.yaml$", path)
    if not feature or not path_feature or feature.group(1) != path_feature.group(1):
        return None
    if expected_feature is not None and feature.group(1) != expected_feature:
        return None
    path_version = re.fullmatch(r"changes/releases/(v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*)/F[0-9]+\.yaml", path)
    if not path_version or version != path_version.group(1):
        return None
    if _sensitive_release_text(text):
        return None
    return feature.group(1)


def metadata_only_release_prep(commit, published_version=None):
    """Accept the operator's notes-only follow-up without hiding code changes."""
    try:
        parents = metadata._git("rev-list", "--parents", "--max-count=1", commit).split()
        if len(parents) != 2:
            return False
        subject = subprocess.check_output(
            ["git", "show", "-s", "--format=%s", commit],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        if not _RELEASE_PREP_SUBJECT.search(subject):
            return False
        rows = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", "-M", parents[1], commit],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").splitlines()
    except (UnicodeDecodeError, subprocess.CalledProcessError):
        return False
    rename_rows = []
    for row in rows:
        fields = row.split("\t")
        if len(fields) == 3 and fields[0] == "R100":
            rename_rows.append((fields[1], fields[2]))
    if rename_rows:
        if len(rows) != len(rename_rows) + 1 or not any(
            row.split("\t") == ["M", "CHANGELOG.md"] for row in rows
        ):
            return False
        parent = parents[1]

        def blob(revision, path):
            return subprocess.check_output(
                ["git", "show", f"{revision}:{path}"], stderr=subprocess.DEVNULL,
            ).decode("utf-8")

        try:
            before_changelog = blob(parent, "CHANGELOG.md")
            after_changelog = blob(commit, "CHANGELOG.md")
            before_heading = _RELEASE_HEADING.search(before_changelog)
            after_heading = _RELEASE_HEADING.search(after_changelog)
            before_headings = _RELEASE_HEADING.findall(before_changelog)
            after_headings = _RELEASE_HEADING.findall(after_changelog)
            if (
                before_heading is None
                or after_heading is None
                or len(after_headings) != len(before_headings) + 1
                or after_headings[1:] != before_headings
                or after_heading.start() != after_changelog.find(f"## [{after_headings[0]}]")
            ):
                return False
            latest = after_headings[0]
            if published_version is not None:
                published_key = _calver_key(published_version)
                latest_key = _calver_key(f"v{latest}")
                if published_key is None or latest_key is None or latest_key <= published_key:
                    return False
            section_start = after_heading.start()
            next_heading = _RELEASE_HEADING.search(after_changelog, section_start + 1)
            section_end = next_heading.start() if next_heading else len(after_changelog)
            if (
                after_changelog[:section_start] != before_changelog[:before_heading.start()]
                or after_changelog[section_end:] != before_changelog[before_heading.start():]
            ):
                return False
            section = after_changelog[section_start:section_end]
            marker_lines = _RELEASE_MARKER.findall(section)
            if len(marker_lines) != 1 or not re.search(r"[А-Яа-яЁё]", section):
                return False
            changed = subprocess.check_output(
                ["git", "diff", "--unified=0", parent, commit, "--", "CHANGELOG.md"],
                stderr=subprocess.DEVNULL,
            ).decode("utf-8")
        except (UnicodeDecodeError, ValueError, subprocess.CalledProcessError):
            return False

        fragment_ids = set()
        versions = set()
        for old_path, new_path in rename_rows:
            old_match = _RELEASE_PREP_UNRELEASED_FRAGMENT.fullmatch(old_path)
            new_match = _RELEASE_PREP_ARCHIVED_FRAGMENT.fullmatch(new_path)
            if old_match is None or new_match is None:
                return False
            if new_match.group(2) != old_match.group(1):
                return False
            versions.add(new_match.group(1))
            try:
                before, after = blob(parent, old_path), blob(commit, new_path)
            except (UnicodeDecodeError, subprocess.CalledProcessError):
                return False
            if before != after:
                return False
            feature_id = _valid_release_fragment(
                after, new_path, f"v{latest}", expected_feature=old_match.group(1)
            )
            if feature_id is None:
                return False
            fragment_ids.add(feature_id)
            changed += subprocess.check_output(
                ["git", "diff", "--unified=0", parent, commit, "--", old_path, new_path],
                stderr=subprocess.DEVNULL,
            ).decode("utf-8")

        marker_ids = {
            feature_id
            for marker in marker_lines
            for feature_id in re.findall(r"\bF([0-9]+)\b", marker)
        }
        if not fragment_ids or versions != {f"v{latest}"} or marker_ids != fragment_ids:
            return False
        return not any(
            _sensitive_release_text(line[1:])
            for line in changed.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
    paths = []
    fragments = []
    for row in rows:
        fields = row.split("\t")
        if len(fields) != 2 or fields[0] != "M":
            return False
        path = fields[1]
        paths.append(path)
        match = _RELEASE_PREP_FRAGMENT.fullmatch(path)
        if match:
            fragments.append(match)
    versions = {match.group(1) for match in fragments}
    if not (
        paths.count("CHANGELOG.md") == 1
        and len(fragments) == len(paths) - 1
        and bool(fragments)
        and len(versions) == 1
    ):
        return False
    parent = parents[1]

    def blob(revision, path):
        return subprocess.check_output(
            ["git", "show", f"{revision}:{path}"], stderr=subprocess.DEVNULL,
        ).decode("utf-8")

    try:
        before_changelog, after_changelog = blob(parent, "CHANGELOG.md"), blob(commit, "CHANGELOG.md")
        before_headings = _RELEASE_HEADING.findall(before_changelog)
        after_headings = _RELEASE_HEADING.findall(after_changelog)
        before_heading_lines = [match.group(0) for match in _RELEASE_HEADING.finditer(before_changelog)]
        after_heading_lines = [match.group(0) for match in _RELEASE_HEADING.finditer(after_changelog)]
        if not before_headings or before_headings != after_headings or before_heading_lines != after_heading_lines:
            return False
        latest = after_headings[0]
        if published_version is not None:
            published_key = _calver_key(published_version)
            latest_key = _calver_key(f"v{latest}")
            if published_key is None or latest_key is None or latest_key <= published_key:
                return False
        section_start = after_changelog.index(f"## [{latest}]")
        next_heading = _RELEASE_HEADING.search(after_changelog, section_start + 1)
        section_end = next_heading.start() if next_heading else len(after_changelog)
        before_start = before_changelog.index(f"## [{latest}]")
        before_next = _RELEASE_HEADING.search(before_changelog, before_start + 1)
        before_end = before_next.start() if before_next else len(before_changelog)
        if (before_changelog[:before_start], before_changelog[before_end:]) != (
            after_changelog[:section_start], after_changelog[section_end:]
        ):
            return False
        if _RELEASE_MARKER.findall(before_changelog[before_start:before_end]) != _RELEASE_MARKER.findall(
            after_changelog[section_start:section_end]
        ):
            return False
        changed = subprocess.check_output(
            ["git", "diff", "--unified=0", parent, commit, "--", "CHANGELOG.md"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8")
    except (UnicodeDecodeError, ValueError, subprocess.CalledProcessError):
        return False
    fragment_ids = set()
    for match in fragments:
        path = match.string
        try:
            before, after = blob(parent, path), blob(commit, path)
        except (UnicodeDecodeError, subprocess.CalledProcessError):
            return False
        before_fields = _TOP_LEVEL_FIELD.findall(before)
        if (len(before_fields) != len(changelog.REQUIRED)
                or set(before_fields) != set(changelog.REQUIRED)):
            return False
        feature_id = _valid_release_fragment(after, path, f"v{latest}")
        if feature_id is None:
            return False
        after_fields = _TOP_LEVEL_FIELD.findall(after)
        for field in set(after_fields) - _RELEASE_PROSE_FIELDS:
            if changelog._field_payload(before, field) != changelog._field_payload(after, field):
                return False
        fragment_ids.add(feature_id)
        if match.group(1) != f"v{latest}":
            return False
        try:
            changed += subprocess.check_output(
                ["git", "diff", "--unified=0", parent, commit, "--", path],
                stderr=subprocess.DEVNULL,
            ).decode("utf-8")
        except (UnicodeDecodeError, subprocess.CalledProcessError):
            return False

    marker_lines = _RELEASE_MARKER.findall(after_changelog[section_start:section_end])
    marker_ids = {
        feature_id
        for marker in marker_lines
        for feature_id in re.findall(r"\bF([0-9]+)\b", marker)
    }
    if not marker_ids or not fragment_ids <= marker_ids:
        return False
    for feature_id in marker_ids:
        path = f"changes/releases/v{latest}/F{feature_id}.yaml"
        try:
            text = blob(commit, path)
        except (UnicodeDecodeError, subprocess.CalledProcessError):
            return False
        if _valid_release_fragment(text, path, f"v{latest}", feature_id) is None:
            return False
    added_lines = [line[1:] for line in changed.splitlines() if line.startswith("+") and not line.startswith("+++")]
    return not any(_sensitive_release_text(line) for line in added_lines)


def metadata_only_closeout(commit):
    """Accept one task-only docs closeout without treating it as product code."""
    try:
        parents = metadata._git("rev-list", "--parents", "--max-count=1", commit).split()
        if len(parents) != 2:
            return False
        subject = subprocess.check_output(
            ["git", "show", "-s", "--format=%s", commit], stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        if not _CLOSEOUT_SUBJECT.match(subject):
            return False
        rows = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", parents[1], commit],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").splitlines()
    except (UnicodeDecodeError, subprocess.CalledProcessError):
        return False
    if not rows or any(
        len(fields := row.split("\t")) != 2
        or fields[0] != "M"
        or not _CLOSEOUT_TASK.fullmatch(fields[1])
        for row in rows
    ):
        return False
    try:
        changed = subprocess.check_output(
            ["git", "diff", "--unified=0", parents[1], commit, "--", *[row.split("\t", 1)[1] for row in rows]],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8")
    except (UnicodeDecodeError, subprocess.CalledProcessError):
        return False
    added_lines = [line[1:] for line in changed.splitlines() if line.startswith("+") and not line.startswith("+++")]
    return bool(added_lines) and not any(_sensitive_release_text(line) for line in added_lines)


def code_snapshot(pr, repository):
    snapshot = metadata.metadata_snapshot(pr, repository)
    require(isinstance(pr["head"].get("ref"), str) and bool(pr["head"]["ref"]), "missing PR head ref")
    snapshot["head_ref"] = pr["head"]["ref"]
    snapshot["base_sha"] = metadata.checked_base(pr)
    return {key: value for key, value in snapshot.items() if key not in {"metadata_digest", "api_base_sha"}}


@artifact_cache()
def reuse(repository, event, workflow, run_id, attempt, *, wait_seconds=0):
    require(re.fullmatch(r"[\w.-]+/[\w.-]+", repository), "invalid repository")
    require(workflow in {"governance-fast", "macos-pr"} and 0 <= wait_seconds <= 2640,
            "invalid component/wait budget")
    scope = module("ci-pr-scope").resolve(event, "pull_request")
    require(scope["text_only"] is True, "reuse requires a proven title/body event")
    number = scope["pull_request_numbers"][0]
    pr = api(repository, f"pulls/{number}")
    snapshot = code_snapshot(pr, repository)
    require(snapshot == code_snapshot(event["pull_request"], repository)
            and snapshot["target_sha"] == scope["target_sha"] and snapshot["base_sha"] == scope["base_sha"],
            "text event differs from current PR")
    own = api(repository, f"actions/runs/{run_id}")
    run_identity(repository, workflow, pr, own)
    require(own["id"] == run_id and own["run_attempt"] == attempt, "current text run/attempt mismatch")
    own["jobs"] = api(repository, f"actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100", pages_key="jobs")
    own_scope = run_scope(repository, workflow, pr, scope["base_sha"], own)
    require(own_scope is not None and own_scope["text_only"] is True
            and all(own_scope[key] == scope[key] for key in ("paths_digest", "native_required")),
            "current run has no verified text scope")
    deadline = time.monotonic() + wait_seconds
    while True:
        require(code_snapshot(api(repository, f"pulls/{number}"), repository) == snapshot, "PR changed during reuse")
        try:
            source = current_run(repository, workflow, pr, scope["base_sha"])
        except PendingProof:
            remaining = deadline - time.monotonic()
            require(remaining > 0, "source check did not finish within reuse wait budget")
            time.sleep(min(15, remaining))
            continue
        if workflow == "macos-pr":
            require(all(source[1][key] == own_scope[key] for key in ("paths_digest", "native_required")),
                    "native source scope differs from current diff")
        # Recheck the source after artifact validation; the PR can stay unchanged
        # while a new attempt invalidates the just-validated source proof.
        require(reference(*current_run(repository, workflow, pr, scope["base_sha"])) == reference(*source),
                "source attempt changed during reuse")
        require(code_snapshot(api(repository, f"pulls/{number}"), repository) == snapshot, "PR changed during reuse")
        return dict(reference(*source), workflow=workflow, target_sha=scope["target_sha"], base_sha=scope["base_sha"])


@artifact_cache()
def verify(repository, number, *, expected_sha=None, code_run_id=None):
    require(re.fullmatch(r"[\w.-]+/[\w.-]+", repository) and type(number) is int and number > 0, "invalid repository/PR")
    pr = api(repository, f"pulls/{number}")
    snapshot = metadata.metadata_snapshot(pr, repository)
    if expected_sha:
        require(snapshot["target_sha"] == expected_sha, "PR SHA differs from requested source")
    for sha in {snapshot["target_sha"], snapshot["api_base_sha"], snapshot["merge_commit_sha"]} - {None}:
        if subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            subprocess.run(["git", "fetch", "--no-tags", "origin", sha], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    branch_identity = code_snapshot(pr, repository)
    base = metadata.checked_base(pr)
    policy = json.loads((ROOT / ".github/pr-check-policy.json").read_text())
    old = historical(pr, policy)
    foundation = api(repository, f"pulls/{policy['foundation_pr']}")
    require(foundation.get("merged") is True and foundation.get("merge_commit_sha") == policy["foundation_sha"]
            and utc(foundation["merged_at"]) < utc(policy["activated_at"]), "unverified policy foundation")
    workflows = ["governance-fast"] if old else ["governance-fast", "macos-pr", "pr-metadata"]
    bundles = {name: current_run(repository, name, pr, base) for name in workflows}
    jobs = []
    for name in workflows:
        jobs.append((bundles[name][0], name))
        if name != "pr-metadata":
            jobs.append((bundles[name][0], "code-scope" if name == "governance-fast" else "macos-pr"))
    prefetch_artifacts(repository, jobs)
    gates = {name: current_gate(repository, name, pr, base) for name in workflows}
    if code_run_id is not None:
        require(str(bundles["governance-fast"][0]["id"]) == str(code_run_id), "referenced code run is no longer current")
    result = validate_bundle(pr, repository, policy, base, bundles)
    for name in workflows:
        require(reference(*current_run(repository, name, pr, base)) == reference(*bundles[name]),
                f"{name}: source attempt changed during verification")
        require(reference(*current_gate(repository, name, pr, base)) == reference(*gates[name]),
                f"{name}: gate attempt changed during verification")
    after = api(repository, f"pulls/{number}")
    require(metadata.metadata_snapshot(after, repository) == snapshot
            and code_snapshot(after, repository) == branch_identity,
            "PR changed while verifying checks")
    return result


def verify_source(repository, source_sha, *, included_prs=None):
    """Derive the actual release range; a moving/local-only tag is not a base."""
    require(re.fullmatch(r"[\w.-]+/[\w.-]+", repository)
            and re.fullmatch(r"[0-9a-f]{40}", source_sha), "invalid release source")
    policy = json.loads((ROOT / ".github/pr-check-policy.json").read_text())
    historical({}, policy)
    require(policy["repository"] == repository, "release policy repository mismatch")
    releases = api(repository, "releases?per_page=100", pages_key="")
    published = [r for r in releases if not r.get("draft") and not r.get("prerelease") and r.get("published_at")
                 and re.fullmatch(r"v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*", r.get("tag_name", ""))]
    require(bool(published), "published release base is unavailable")
    base = None
    base_release_tag = None
    for release in sorted(published, key=lambda item: utc(item["published_at"]), reverse=True):
        ref = api(repository, f"git/ref/tags/{release['tag_name']}")["object"]
        for _ in range(5):
            require(re.fullmatch(r"[0-9a-f]{40}", ref.get("sha", "")), "invalid published tag object")
            if ref.get("type") == "commit":
                break
            require(ref.get("type") == "tag", "published tag must resolve to a commit")
            ref = api(repository, f"git/tags/{ref['sha']}")["object"]
        require(ref.get("type") == "commit", "too many annotated tag levels")
        candidate = ref["sha"]
        if subprocess.run(["git", "cat-file", "-e", f"{candidate}^{{commit}}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            subprocess.run(["git", "fetch", "--no-tags", "origin", candidate], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Publishing this very candidate must not turn its attestation into an empty check set.
        if candidate != source_sha and not subprocess.run(
            ["git", "merge-base", "--is-ancestor", candidate, source_sha],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode:
            base = candidate
            base_release_tag = release["tag_name"]
            break
    require(base is not None, "previous published release ancestor is unavailable")
    commits = metadata._git("rev-list", "--first-parent", f"{base}..{source_sha}").splitlines()
    candidates, results = [], []
    covered = set()
    deferred_prs = set()
    metadata_kinds = set()
    for commit in commits:
        prs = api(repository, f"commits/{commit}/pulls?per_page=100", pages_key="")
        all_matches = [pr for pr in prs if pr.get("merged_at")
                       and pr.get("base", {}).get("ref") == "master"]
        matches = [pr for pr in prs if pr.get("merged_at") and pr.get("merge_commit_sha") == commit
                   and pr.get("base", {}).get("ref") == "master"]
        if not matches:
            if all_matches:
                require(len(all_matches) == 1 and isinstance(all_matches[0].get("number"), int),
                        "release commit maps to multiple merged pull requests")
                # Fast-forward merges expose the PR's individual commits on
                # the first-parent range before the tip commit that GitHub
                # records as merge_commit_sha. Defer those commits and verify
                # the PR exactly once when its merge commit is reached.
                deferred_prs.add(all_matches[0]["number"])
                continue
            kind = (
                "release-prep"
                if metadata_only_release_prep(commit, published_version=base_release_tag)
                else "closeout"
                if metadata_only_closeout(commit)
                else None
            )
            require(kind is not None,
                    "release contains source without a unique merged PR")
            require(kind not in metadata_kinds,
                    "release contains duplicate metadata-only commit kind")
            metadata_kinds.add(kind)
            continue
        require(len(matches) == 1, "release contains source without a unique merged PR")
        candidates.append((commit, matches[0]["number"]))

    candidate_prs = {number for _commit, number in candidates}
    require(deferred_prs <= candidate_prs,
            "release contains source without a unique merged PR")

    # PR checks are independent once the exact first-parent release range has
    # been derived. Keep the concurrency bounded, but do not serialize network
    # proof downloads behind the slowest PR. Results are consumed in release
    # order so the manifest remains deterministic.
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(8, len(candidates) or 1)
    ) as pool:
        futures = [pool.submit(verify, repository, number) for _commit, number in candidates]
        for (commit, _number), future in zip(candidates, futures):
            # A squash/rebase range can expose more than one commit for the
            # same PR. The first verified merge commit covers the remainder;
            # preserve that old exact-range rule while allowing the independent
            # futures to run concurrently.
            if commit in covered:
                continue
            proof = future.result()
            require(proof["merge_commit_sha"] == commit, "release PR merge identity changed")
            covered.update(metadata._git("rev-list", "--first-parent", f"{proof['base_sha']}..{commit}").splitlines())
            results.append(proof)
    numbers = sorted(proof["pr_number"] for proof in results)
    if included_prs is not None:
        require(sorted(included_prs) == numbers, "train PR set differs from the published-release range")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pr", type=int)
    source.add_argument("--source-sha")
    source.add_argument("--reuse-component", choices=("governance-fast", "macos-pr"))
    parser.add_argument("--event", type=Path)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--run-attempt", type=int)
    parser.add_argument("--wait-seconds", type=int, default=0)
    parser.add_argument("--included-prs")
    parser.add_argument("--expected-sha")
    parser.add_argument("--code-run-id")
    args = parser.parse_args()
    try:
        if args.reuse_component:
            require(args.event is not None and args.run_id and args.run_attempt
                    and not args.included_prs and not args.expected_sha and not args.code_run_id,
                    "reuse needs exact event/run identity only")
            result = reuse(args.repository, json.loads(args.event.read_text()), args.reuse_component,
                           args.run_id, args.run_attempt, wait_seconds=args.wait_seconds)
            if os.environ.get("GITHUB_STEP_SUMMARY"):
                with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as output:
                    output.write(
                        f"Reused validated `{result['workflow']}` source proof: "
                        f"https://github.com/{args.repository}/actions/runs/{result['run_id']} "
                        f"(attempt {result['run_attempt']}).\n\n"
                        f"HEAD: `{result['target_sha']}`; base: `{result['base_sha']}`. "
                        "Product tests were not repeated for this title/body edit.\n"
                    )
        elif args.source_sha:
            require(not args.expected_sha and not args.code_run_id, "source and PR evidence options cannot mix")
            numbers = [int(item) for item in args.included_prs.split(",")] if args.included_prs else None
            result = verify_source(args.repository, args.source_sha, included_prs=numbers)
        else:
            require(args.included_prs is None, "included PRs require release source")
            result = verify(args.repository, args.pr, expected_sha=args.expected_sha, code_run_id=args.code_run_id)
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        # A bare "could not be verified" hides whether the proof is missing, the
        # network hiccuped, or the train and the release range disagree.  The
        # reason costs nothing and is what makes the failure actionable.
        print("pr-checks: current complete GitHub proof could not be verified", file=sys.stderr)
        print(f"pr-checks: reason: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
