"""Check the F289 content snapshot: hashes and complete change inventory."""

import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[2]
manifest_path = "specs/289-organic-measurement/evidence/file-manifest.json"
manifest = json.loads((root / manifest_path).read_text())


def git_paths(*args):
    return set(subprocess.check_output(
        ["git", *args], cwd=root, text=True,
    ).splitlines())


expected = git_paths("diff", "--name-only", manifest["base_sha"])
expected |= git_paths("ls-files", "--others", "--exclude-standard")
expected.discard(manifest_path)
entries = manifest["files"]
assert len(entries) == len({entry["path"] for entry in entries}), "duplicate paths"
actual = {entry["path"] for entry in entries}
assert actual == expected, {"missing": sorted(expected - actual),
                            "unexpected": sorted(actual - expected)}
for entry in entries:
    digest = hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest()
    assert digest == entry["sha256"], f"stale checksum: {entry['path']}"
print(f"PASS: {len(entries)} file hashes and complete diff inventory")
