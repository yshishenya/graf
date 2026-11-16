import asyncio
import fcntl
import json
import os
import stat
import tempfile
from collections.abc import Awaitable, Callable, Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from threading import Event
from uuid import UUID

from twobrain_rec_server.config import Settings

_MAX_STATE_BYTES = 4096
STRICT_SOURCE_READ_SECONDS = 30.0


def _open_regular(path: Path, resources: ExitStack, *, create: bool = False) -> int:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open(path, flags | (os.O_CREAT if create else 0), 0o600)
    resources.callback(os.close, fd)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        raise ValueError("Storage recovery requires a regular state file")
    return fd


def _unique_recovery_fields(fields: list[tuple[str, object]]) -> dict[str, object]:
    record = dict(fields)
    if len(record) != len(fields):
        raise ValueError("Duplicate storage recovery field")
    return record


def _read_recovery_record(fd: int) -> dict[str, object]:
    payload = os.read(fd, _MAX_STATE_BYTES + 1)
    if len(payload) > _MAX_STATE_BYTES:
        raise ValueError("Storage recovery record is too large")
    record = json.loads(payload, object_pairs_hook=_unique_recovery_fields)
    if not isinstance(record, dict) or type(record.get("schema")) is not int or record["schema"] != 1:
        raise ValueError("Invalid storage recovery record")
    return record


@contextmanager
def storage_recovery_snapshot(settings: Settings) -> Iterator[str | None]:
    """Yield the verified recovery ID; hold its shared lock through publication."""
    path, scope = settings.strict_storage_recovery_file, settings.strict_storage_scope
    expected = settings.strict_storage_recovery_id
    directory = settings.strict_storage_recovery_directory
    if directory is not None:
        if not directory.is_absolute() or path is not None:
            yield None
            return
        if scope is None and expected is None:
            if not settings.strict_storage_recovery_allow_legacy:
                yield None
                return
            # Before activation the dedicated volume is empty. After the stable
            # sidecar is provisioned, omitting runtime bindings must fail closed.
            try:
                with os.scandir(directory) as entries:
                    unused = next(entries, None) is None
            except OSError:
                unused = False
            yield "legacy" if unused else None
            return
        path = directory / "state.json"
    if path is None and scope is None and expected is None:
        yield "legacy"
        return
    if path is None or not path.is_absolute() or not scope or expected is None:
        yield None
        return

    with ExitStack() as resources:
        token = None
        try:
            # Operations holds this stable sidecar exclusively while changing the state file.
            lock = _open_regular(path.with_name(path.name + ".lock"), resources)
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
            record = _read_recovery_record(_open_regular(path, resources))
            if (
                record.get("scope") == scope
                and record.get("state") == "reconciled"
                and record.get("recovery_id") == str(expected)
            ):
                token = str(expected)
        except (OSError, ValueError):
            pass
        yield token


def storage_recovery_token(settings: Settings) -> str | None:
    with storage_recovery_snapshot(settings) as token:
        return token


def mark_storage_recovery_unknown(
    path: Path, *, scope: str, recovery_id: UUID, previous_id: UUID | None,
) -> None:
    """Record a new operation in the operator-owned directory outside all snapshots."""
    if not path.is_absolute() or not scope.strip() or recovery_id == previous_id:
        raise ValueError("Storage recovery requires a new operation and an absolute state path")
    predecessor = str(previous_id) if previous_id is not None else None
    payload = json.dumps({
        "schema": 1, "scope": scope, "recovery_id": str(recovery_id), "state": "recovery_unknown",
        "previous_recovery_id": predecessor,
    }).encode("utf-8")
    if len(payload) > _MAX_STATE_BYTES:
        raise ValueError("Storage recovery record is too large")

    with ExitStack() as resources:
        lock = _open_regular(path.with_name(path.name + ".lock"), resources)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        resources.callback(os.close, directory)
        try:
            current = _open_regular(path, resources)
        except FileNotFoundError:
            if previous_id is not None:
                raise ValueError("Expected storage recovery record is missing") from None
        else:
            record = _read_recovery_record(current)
            if record.get("scope") != scope:
                raise ValueError("Storage recovery scope does not match")
            if record.get("recovery_id") == str(recovery_id) and record.get("state") == "recovery_unknown":
                if "previous_recovery_id" not in record or record["previous_recovery_id"] != predecessor:
                    raise ValueError("Storage recovery predecessor does not match")
                os.fsync(current)
                os.fsync(directory)
                return
            if (
                predecessor is None or record.get("recovery_id") != predecessor
                or record.get("state") not in ("reconciled", "recovery_unknown")
            ):
                raise ValueError("Storage recovery predecessor does not match")

        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as pending:
            temporary = Path(pending.name)
            resources.callback(temporary.unlink, missing_ok=True)
            pending.write(payload)
            pending.flush()
            os.fchmod(pending.fileno(), 0o644)
            os.fsync(pending.fileno())
        os.replace(temporary, path)
        os.fsync(directory)


def meeting_storage_read_fence_path(
    settings: Settings, workspace_id: UUID, meeting_id: UUID,
) -> Path | None:
    directory = settings.strict_storage_read_fence_directory
    if directory is None or not directory.is_absolute():
        return None
    return directory / f"{workspace_id}.{meeting_id}.lock"


@contextmanager
def storage_read_fence(
    path: Path, *, exclusive: bool, create: bool = False,
) -> Iterator[ExitStack | None]:
    """Use only an operator-provisioned stable sidecar in a verified locking domain."""
    with ExitStack() as resources:
        try:
            if not path.is_absolute():
                raise ValueError("Storage read fence must use an absolute path")
            fd = _open_regular(path, resources, create=create)
            mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(fd, mode | fcntl.LOCK_NB)
        except (OSError, ValueError):
            yield None
        else:
            yield resources


async def await_storage_worker[T](operation: asyncio.Future[T], cancelled: Event) -> T:
    try:
        return await asyncio.shield(operation)
    except asyncio.CancelledError:
        cancelled.set()
        # Keep staging and ownership alive until the thread drains, even
        # when shutdown cancels the waiter more than once.
        while not operation.done():
            try:
                await asyncio.shield(operation)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if not operation.cancelled():
            operation.exception()
        raise


async def read_with_storage_fence[T](
    path: Path,
    *,
    admit: Callable[[], Awaitable[bool]],
    read: Callable[[Event], T],
) -> T | None:
    """Transfer the shared fence to the thread that owns the response."""
    with storage_read_fence(path, exclusive=False, create=True) as fence:
        if fence is None or await admit() is not True:
            return None
        cancelled = Event()
        owned = fence.pop_all()

        def run() -> T:
            with owned:
                return read(cancelled)

        try:
            operation = asyncio.get_running_loop().run_in_executor(None, run)
        except BaseException:
            owned.close()
            raise
        return await await_storage_worker(operation, cancelled)
