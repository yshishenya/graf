#!/usr/bin/env python3
"""Verify a pinned MinIO copy and keep the ownership metadata needed for restore."""

import hashlib
import json
import os
import re
import shlex
import stat
import sys
from pathlib import Path, PurePosixPath
from uuid import UUID


def require(condition):
    if not condition:
        raise ValueError("object backup contract mismatch")


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def require_key(key):
    require(key and all(part not in ("", ".", "..") for part in key.split("/"))
            and "\\" not in key and not any(ord(character) < 32 for character in key))
    require(PurePosixPath(key).as_posix() == key)


def require_metadata(attempt, content_type):
    if attempt is not None:
        require(str(UUID(attempt)) == attempt)
    if content_type is not None:
        require(isinstance(content_type, str) and content_type.isprintable() and len(content_type) <= 256)


def inventory(path, bucket):
    result = {}
    with path.open() as lines:
        for line in lines:
            row = json.loads(line, object_pairs_hook=unique)
            require(row["status"] == "success" and row["type"] == "file")
            require(row["name"].startswith(bucket + "/"))
            key = row["name"][len(bucket) + 1:]
            require_key(key)
            require(key not in result)
            require(type(row["size"]) is int and row["size"] >= 0 and bool(row["etag"]))
            raw = row.get("metadata", {})
            metadata = {name.lower(): value for name, value in raw.items()}
            require(len(metadata) == len(raw))
            attempt = metadata.get("x-amz-meta-graf-upload-attempt")
            content_type = metadata.get("content-type")
            require_metadata(attempt, content_type)
            result[key] = dict(key=key, size=row["size"], etag=row["etag"], attempt=attempt, content_type=content_type)
    return result


def verify(root, bucket):
    raw = [root / name for name in (".minio-version", ".minio-version-after",
                                     ".minio-incomplete-before", ".minio-incomplete-after",
                                     ".minio-before", ".minio-after", ".minio-hashes")]
    for path in raw:
        entry = path.lstat()
        require(stat.S_ISREG(entry.st_mode) and entry.st_nlink == 1)
    for path in raw[:2]:
        version = json.loads(path.read_text(), object_pairs_hook=unique)
        require(version["status"] == "success" and version["versioning"]["status"] == "")
    require(raw[2].stat().st_size == raw[3].stat().st_size == 0)
    before = inventory(raw[4], bucket)
    require(before == inventory(raw[5], bucket))
    source_hashes = {}
    with raw[6].open() as lines:
        for line in lines:
            digest, separator, key = line.removesuffix("\n").partition("\t")
            require(separator and re.fullmatch(r"[0-9a-f]{64}", digest) and key in before and key not in source_hashes)
            source_hashes[key] = digest
    require(set(source_hashes) == set(before))
    copied = {}
    for key, path, size in archived_objects(root / "minio-objects"):
        require(key in source_hashes)
        with path.open("rb") as stream:
            require(hashlib.file_digest(stream, "sha256").hexdigest() == source_hashes[key])
        copied[key] = size
    require(copied == {key: record["size"] for key, record in before.items()})
    with (root / "minio-inventory.jsonl").open("x") as output:
        output.write(json.dumps(dict(schema=1, bucket=bucket, versioning="disabled", incomplete=0)) + "\n")
        for key in sorted(before):
            output.write(json.dumps({**before[key], "sha256": source_hashes[key]}, sort_keys=True) + "\n")
    for path in raw:
        path.unlink()


def archived_objects(directory):
    require(directory.is_dir() and not directory.is_symlink())

    def walk_error(error):
        raise error

    for folder, subdirs, files in os.walk(directory, onerror=walk_error):
        for name in subdirs:
            require(not (Path(folder) / name).is_symlink())
        for name in files:
            path = Path(folder) / name
            entry = path.lstat()
            require(stat.S_ISREG(entry.st_mode) and entry.st_nlink == 1)
            yield path.relative_to(directory).as_posix(), path, entry.st_size


def restore_manifest(path):
    records = {}
    with path.open() as stream:
        header = json.loads(next(stream, "{}"), object_pairs_hook=unique)
        bucket = header["bucket"]
        require(isinstance(bucket, str) and bool(bucket) and header == {
            "schema": 1, "bucket": bucket, "versioning": "disabled", "incomplete": 0,
        })
        for line in stream:
            row = json.loads(line, object_pairs_hook=unique)
            key = row["key"]
            require_key(key)
            require(key not in records and type(row["size"]) is int and row["size"] >= 0)
            require(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]))
            require_metadata(row["attempt"], row["content_type"])
            records[key] = row
    return records


def prepare_rehearsal(root, manifest, bucket):
    objects = root / "minio-objects"
    require(objects.resolve() == objects)
    records = restore_manifest(manifest)
    require({key: size for key, _, size in archived_objects(objects)}
            == {key: row["size"] for key, row in records.items()})
    print("set -eu; set -o pipefail")
    for key, row in records.items():
        mounted = "/backup/minio-objects/" + key
        target = f"rec/{bucket}/{key}"
        options = []
        if row["content_type"] is not None:
            options += ["-H", "Content-Type:" + row["content_type"]]
        if row["attempt"] is not None:
            options += ["-H", "X-Amz-Meta-Graf-Upload-Attempt:" + row["attempt"]]
        print("sum=$(" + shlex.join(["sha256sum", mounted]) + ")")
        print(f'[ "${{sum%% *}}" = {row["sha256"]} ]')
        print(shlex.join(["mc", "put", *options, mounted, target]) + " >/dev/null")
        print("sum=$(" + shlex.join(["mc", "cat", target]) + " | sha256sum)")
        print(f'[ "${{sum%% *}}" = {row["sha256"]} ]')
    # Recursive stat exits with an error for an empty bucket, unlike ls.
    print(shlex.join(["mc", "--json", "stat" if records else "ls", "--recursive", f"rec/{bucket}"]))


def verify_rehearsal(manifest, listing, bucket):
    records = restore_manifest(manifest)
    actual = inventory(listing, bucket)
    require(actual.keys() == records.keys())
    for key, row in records.items():
        require(actual[key]["size"] == row["size"] and actual[key]["attempt"] == row["attempt"])
        if row["content_type"] is not None:
            require(actual[key]["content_type"] == row["content_type"])


if __name__ == "__main__":
    try:
        if len(sys.argv) == 3:
            verify(Path(sys.argv[1]), sys.argv[2])
        else:
            mode, first, second, bucket = sys.argv[1:]
            require(re.fullmatch(r"twobrain-rec-restore-rehearsal-[0-9a-f]{32}", bucket))
            if mode == "--prepare-rehearsal":
                prepare_rehearsal(Path(first), Path(second), bucket)
            else:
                require(mode == "--verify-rehearsal")
                verify_rehearsal(Path(first), Path(second), bucket)
    except (OSError, ValueError, AttributeError, KeyError, TypeError, IndexError):
        print("object_backup=blocked", file=sys.stderr)
        raise SystemExit(1) from None
