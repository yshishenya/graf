"""Fixed mail-only one-shot controller. Private inputs never enter output."""
import asyncio
import json
import os
import stat
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from twobrain_rec_server.auth.email_delivery import PostalEmailLoginClient
from twobrain_rec_server.billing.observation_alerts import (
    MAX_RECORD,
    AlertJournal,
    canonical,
    closed,
    decode,
    require,
    stamp,
    uuid,
)

JOURNAL = Path("/state/journal.jsonl")
CONFIG = Path("/run/secrets/billing-observation-mail.json")


def read_protected(path):
    path = Path(path)
    before = path.lstat()
    for parent in path.absolute().parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in {0, os.getuid()} and not info.st_mode & 0o022)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) in {0o400, 0o440}
                and (before.st_dev, before.st_ino) == (info.st_dev, info.st_ino))
        raw = os.read(fd, MAX_RECORD + 1)
        require(len(raw) <= MAX_RECORD)
        return decode(raw)
    finally:
        os.close(fd)


def envelope(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid in {0, os.getuid()}
                    and not info.st_mode & 0o022 and info.st_nlink == 1)
            return decode(os.read(fd, MAX_RECORD + 1))
        finally:
            os.close(fd)
    except (OSError, ValueError, RuntimeError):
        return None


def configuration():
    config = read_protected(CONFIG)
    closed(config, {"role", "source_profile", "source_generation", "binding_version", "mail"})
    require(config["role"] in {"primary", "witness"})
    for field in ("source_profile", "source_generation", "binding_version"):
        uuid(config[field])
    closed(config["mail"], {"api_url", "api_key", "from_address", "recipient", "host_header"})
    from urllib.parse import urlsplit

    target = urlsplit(config["mail"]["api_url"])
    require(target.scheme == "https" and target.hostname and not target.username and not target.password
            and target.path in {"", "/"} and not target.query and not target.fragment)
    for field in ("api_key", "from_address", "recipient"):
        value = config["mail"][field]
        require(type(value) is str and 0 < len(value.encode()) <= 255 and "\r" not in value and "\n" not in value)
    require(all(config["mail"][f].count("@") == 1 for f in ("from_address", "recipient")))
    header = config["mail"]["host_header"]
    require(header is None or (type(header) is str and len(header) <= 255 and "\r" not in header and "\n" not in header))
    return config


def restore():
    """Publish only a fully checked candidate already carrying recovery hold."""
    candidate = JOURNAL.with_name("journal.restore-candidate")
    require(not JOURNAL.exists() and not candidate.exists())
    with AlertJournal(Path("/backup/journal.jsonl"), read_only=True) as backup:
        backup.backup(candidate)
    with AlertJournal(candidate) as restored:
        restored.append("discontinuity", {"reason": "source_generation_changed",
                        "at": restored.last_now, "hold": True})
    # link is exclusive; the final name can never replace a live journal.
    os.link(candidate, JOURNAL, follow_symlinks=False)
    candidate.unlink()
    directory = os.open(JOURNAL.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


async def run(mode):
    deadline = time.monotonic() + 60
    now = datetime.now(UTC)
    if mode == "status":
        with AlertJournal(JOURNAL, deadline=deadline, read_only=True) as journal:
            return journal.status()
    if mode == "restore":
        restore()
        return {"schema_version": 1, "result_code": "recovery_hold"}
    config = configuration()
    if mode == "activate":
        AlertJournal.activate(JOURNAL, **{k: config[k] for k in ("source_profile", "source_generation", "binding_version", "role")}, now=now)
        return {"schema_version": 1, "result_code": "activated"}
    with AlertJournal(JOURNAL, deadline=deadline, clock=lambda: datetime.now(UTC), recovery=mode == "recover") as journal:
        require(journal.activation["source_profile"] == config["source_profile"]
                and journal.activation["role"] == config["role"])
        if mode == "transfer":
            journal.transfer(read_protected(Path("/relay/decision.json")), now=now)
            return {"schema_version": 1, "result_code": "reaction_recorded"}
        if mode == "backup":
            return {"schema_version": 1, **journal.backup(Path("/backup/journal.jsonl"))}
        if mode == "recover":
            manifest = read_protected(Path("/relay/recovery.json"))
            closed(manifest, {"expected_head", "source_generation", "evidence_ref"})
            require(manifest["source_generation"] == config["source_generation"])
            journal.append("recovery", {**manifest, "at": stamp(now)})
            return {"schema_version": 1, "result_code": "lineage_recovered"}
        require(mode in {"tick", "witness"} and (mode == "tick") == (config["role"] == "primary")
                and journal.activation["source_generation"] == config["source_generation"])
        mail = config["mail"]
        client = PostalEmailLoginClient(mail["api_url"], mail["api_key"], mail["from_address"],
                                       host_header=mail["host_header"], timeout_seconds=10)
        return await journal.tick(source=envelope("/input/source.json") if mode == "tick" else None,
            peer=envelope("/input/peer.json"), now=now, binding_version=config["binding_version"],
            client=client, recipient=mail["recipient"])


def main():
    try:
        require(len(sys.argv) == 2 and sys.argv[1] in {"tick", "witness", "status", "activate", "transfer", "backup", "restore", "recover"})
        result = asyncio.run(run(sys.argv[1]))
        require(len(canonical(result)) + 1 <= MAX_RECORD)
        code = 0
    except (Exception, KeyboardInterrupt):
        result, code = {"schema_version": 1, "result_code": "observation_unavailable"}, 1
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
