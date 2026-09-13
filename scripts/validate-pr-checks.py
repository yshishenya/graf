#!/usr/bin/env python3
"""Verify one current PR check set, including immutable GitHub artifact identity."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
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


def validate_bundle(pr, repository, policy, base, bundles):
    """Validate downloaded facts; callers obtain them from GitHub, not user files."""
    current = metadata.metadata_snapshot(pr, repository)
    require(policy["repository"] == repository, "policy repository mismatch")
    old = historical(pr, policy)
    require(set(bundles) == ({"governance-fast"} if old else {"governance-fast", "macos-pr", "pr-metadata"}),
            "incomplete PR check set")
    refs = {}
    for workflow, (run, proof) in bundles.items():
        require(run.get("name") == workflow and run.get("path") == f".github/workflows/{workflow}.yml"
                and run.get("status") == "completed" and run.get("conclusion") == "success",
                f"{workflow}: wrong workflow or unsuccessful run")
        target_event = "pull_request_target" if workflow == "pr-metadata" else "pull_request"
        require(run.get("event") == target_event, f"{workflow}: wrong event")
        require(str(proof.get("run_id")) == str(run["id"])
                and proof.get("run_attempt") == run.get("run_attempt"), f"{workflow}: mixed run/attempt")
        require(proof.get("target_sha") == current["target_sha"] and proof.get("base_sha") == base,
                f"{workflow}: stale or mixed head/base")
        if workflow == "governance-fast":
            require(not receipts.validate(proof), "invalid code receipt")
            require(proof["status"] == "passed" and proof["workflow"] == workflow
                    and proof["event_name"] == "pull_request"
                    and proof["pull_request_numbers"] == [pr["number"]]
                    and run.get("head_sha") == current["target_sha"], "code receipt identity mismatch")
        elif workflow == "macos-pr":
            require(proof.get("repository") == repository and proof.get("event_name") == "pull_request"
                    and proof.get("pull_request_numbers") == [pr["number"]]
                    and proof.get("text_only") is False and type(proof.get("native_required")) is bool
                    and run.get("head_sha") == current["target_sha"], "invalid native scope")
            require(re.fullmatch(r"[0-9a-f]{64}", proof.get("paths_digest", "")), "missing native diff digest")
            jobs = {job["name"]: job.get("conclusion") for job in run.get("jobs", [])}
            require(jobs.get("macos-pr") == "success" and jobs.get("Determine native scope") == "success"
                    and jobs.get("Swift build and tests") == ("success" if proof["native_required"] else "skipped"),
                    "required native execution did not pass")
        else:
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
        refs[workflow] = {"run_id": str(run["id"]), "run_attempt": run["run_attempt"],
                          "proof_digest": "sha256:" + hashlib.sha256(json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
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


def artifact(repository, run, workflow):
    names = {"governance-fast": "graf-governance-fast-evidence",
             "code-scope": f"graf-code-scope-{run['id']}-{run['run_attempt']}",
             "macos-pr": f"graf-native-scope-{run['id']}-{run['run_attempt']}",
             "pr-metadata": f"graf-pr-metadata-{run['id']}-{run['run_attempt']}"}
    rows = api(repository, f"actions/runs/{run['id']}/artifacts?per_page=100", pages_key="artifacts")
    matches = [row for row in rows if row.get("name") == names[workflow]]
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


def current_run(repository, workflow, pr, base):
    event = "pull_request_target" if workflow == "pr-metadata" else "pull_request"
    query = f"actions/workflows/{workflow}.yml/runs?event={event}&per_page=100"
    query += f"&head_sha={pr['head']['sha']}"
    runs = api(repository, query, pages_key="workflow_runs")
    for run in sorted(runs, key=lambda row: (utc(row["run_started_at"]), row["id"]), reverse=True):
        numbers = [item.get("number") for item in run.get("pull_requests", [])]
        if numbers and pr["number"] not in numbers:
            continue
        if workflow != "pr-metadata":
            jobs = api(repository, f"actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs?per_page=100", pages_key="jobs")
            if any(job.get("name") == workflow + "-text-change" for job in jobs):
                continue
            # GitHub leaves a skipped job's dynamic name unevaluated. Require
            # its actual scope artifact instead of trusting that display text.
            if workflow == "governance-fast" and len(jobs) == 2 and all(
                (job.get("name") == "Determine code scope" and job.get("conclusion") == "success")
                or (job.get("name") != "governance-fast" and job.get("conclusion") == "skipped") for job in jobs
            ):
                scope = artifact(repository, run, "code-scope")
                require(run.get("status") == "completed" and run.get("conclusion") == "success"
                        and scope.get("text_only") is True and scope.get("repository") == repository
                        and scope.get("target_sha") == pr["head"]["sha"] and scope.get("base_sha") == base
                        and scope.get("pull_request_numbers") == [pr["number"]]
                        and scope.get("event_name") == "pull_request"
                        and scope.get("run_id") == run["id"] and scope.get("run_attempt") == run["run_attempt"],
                        "unverified text-only code skip")
                continue
            require(run.get("conclusion") == "success", f"{workflow}: latest code run is not successful")
        if workflow != "pr-metadata":
            run["jobs"] = jobs
        require(run.get("status") == "completed" and run.get("conclusion") == "success",
                f"{workflow}: latest attempt is not successful")
        proof = artifact(repository, run, workflow)
        number = proof.get("pr_number") if workflow == "pr-metadata" else next(iter(proof.get("pull_request_numbers", [])), None)
        if number != pr["number"]:
            continue
        if workflow == "pr-metadata" and proof.get("target_sha") != pr["head"]["sha"]:
            continue
        require(proof.get("base_sha") == base, f"{workflow}: latest proof has stale base")
        return run, proof
    raise ValueError(f"{workflow}: no current proof")


def verify(repository, number, *, expected_sha=None, code_run_id=None):
    require(re.fullmatch(r"[\w.-]+/[\w.-]+", repository) and type(number) is int and number > 0, "invalid repository/PR")
    pr = api(repository, f"pulls/{number}")
    snapshot = metadata.metadata_snapshot(pr, repository)
    if expected_sha:
        require(snapshot["target_sha"] == expected_sha, "PR SHA differs from requested source")
    for sha in {snapshot["target_sha"], snapshot["api_base_sha"], snapshot["merge_commit_sha"]} - {None}:
        if subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            subprocess.run(["git", "fetch", "--no-tags", "origin", sha], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = metadata.checked_base(pr)
    policy = json.loads((ROOT / ".github/pr-check-policy.json").read_text())
    old = historical(pr, policy)
    foundation = api(repository, f"pulls/{policy['foundation_pr']}")
    require(foundation.get("merged") is True and foundation.get("merge_commit_sha") == policy["foundation_sha"]
            and utc(foundation["merged_at"]) < utc(policy["activated_at"]), "unverified policy foundation")
    workflows = ["governance-fast"] if old else ["governance-fast", "macos-pr", "pr-metadata"]
    bundles = {name: current_run(repository, name, pr, base) for name in workflows}
    if code_run_id is not None:
        require(str(bundles["governance-fast"][0]["id"]) == str(code_run_id), "referenced code run is no longer current")
    result = validate_bundle(pr, repository, policy, base, bundles)
    require(metadata.metadata_snapshot(api(repository, f"pulls/{number}"), repository) == snapshot,
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
            break
    require(base is not None, "previous published release ancestor is unavailable")
    commits = metadata._git("rev-list", "--first-parent", f"{base}..{source_sha}").splitlines()
    covered, results = set(), []
    for commit in commits:
        if commit in covered:
            continue
        prs = api(repository, f"commits/{commit}/pulls?per_page=100", pages_key="")
        matches = [pr for pr in prs if pr.get("merged_at") and pr.get("merge_commit_sha") == commit
                   and pr.get("base", {}).get("ref") == "master"]
        require(len(matches) == 1, "release contains source without a unique merged PR")
        proof = verify(repository, matches[0]["number"])
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
    parser.add_argument("--included-prs")
    parser.add_argument("--expected-sha")
    parser.add_argument("--code-run-id")
    args = parser.parse_args()
    try:
        if args.source_sha:
            require(not args.expected_sha and not args.code_run_id, "source and PR evidence options cannot mix")
            numbers = [int(item) for item in args.included_prs.split(",")] if args.included_prs else None
            result = verify_source(args.repository, args.source_sha, included_prs=numbers)
        else:
            require(args.included_prs is None, "included PRs require release source")
            result = verify(args.repository, args.pr, expected_sha=args.expected_sha, code_run_id=args.code_run_id)
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, zipfile.BadZipFile, subprocess.CalledProcessError):
        print("pr-checks: current complete GitHub proof could not be verified", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
