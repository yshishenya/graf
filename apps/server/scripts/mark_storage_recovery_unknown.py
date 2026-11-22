import argparse
import fcntl
import os
import stat
import subprocess
from pathlib import Path
from uuid import UUID

from twobrain_rec_server.storage.recovery import mark_storage_recovery_unknown


def require_deployment_lock(fd: int) -> None:
    if fd < 3:
        raise ValueError("An inherited deployment descriptor is required")
    path = subprocess.check_output(
        ["git", "rev-parse", "--git-path", "twobrain-rec-deploy.lock"], text=True,
    ).rstrip("\n")
    expected = os.stat(path, follow_symlinks=False)
    opened = os.fstat(fd)
    if not stat.S_ISREG(expected.st_mode) or not os.path.samestat(expected, opened):
        raise ValueError("Descriptor does not identify the deployment lock")
    # This descriptor shares the operator's open file description. Closing it
    # in this child does not release the lock while the operator keeps it open.
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Block completion claims before a storage restore. Run on the stopped stack's operator host.",
    )
    parser.add_argument("--file", type=Path, required=True, help="Absolute path outside the restored snapshots")
    parser.add_argument("--scope", required=True)
    parser.add_argument("--recovery-id", type=UUID, required=True, help="Fresh ID from the operator's external log")
    parser.add_argument("--previous-id", type=UUID, help="Omit only for the initial state file")
    parser.add_argument("--deployment-lock-fd", type=int, required=True, help="Inherited descriptor for the deployment lock")
    args = parser.parse_args()
    try:
        require_deployment_lock(args.deployment_lock_fd)
    except BlockingIOError:
        parser.exit(1, "storage_recovery=blocked reason=deployment_lock_busy\n")
    except (OSError, ValueError, subprocess.CalledProcessError):
        parser.exit(1, "storage_recovery=blocked reason=deployment_lock_unverified\n")
    try:
        mark_storage_recovery_unknown(
            args.file, scope=args.scope, recovery_id=args.recovery_id, previous_id=args.previous_id,
        )
    except BlockingIOError:
        parser.exit(1, "storage_recovery=blocked reason=state_lock_busy\n")
    except ValueError as exc:
        parser.exit(1, f"storage_recovery=blocked reason=invalid_state ({type(exc).__name__})\n")
    except OSError:
        parser.exit(1, "storage_recovery=blocked reason=state_io_failed\n")
    print("storage_recovery=recovery_unknown")


if __name__ == "__main__":
    main()
