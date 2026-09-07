#!/usr/bin/env python3
"""Native Quit/reopen regression; requires a GUI macOS session and GRAF Local.app.

Copies the local build to a unique test bundle. Never grants or resets TCC.
Only synthetic setup intent and metadata logs are used; no capture is started.
"""

import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import time
import uuid


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def main():
    source = Path(sys.argv[1]).resolve()
    with (source / "Contents/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    assert info["CFBundleIdentifier"] == "pro.2brain.graf.local", "Use only GRAF Local.app"
    domain = "pro.2brain.graf.permission-proof-" + uuid.uuid4().hex
    active_key = "permissionOnboarding.active"
    process = None
    with tempfile.TemporaryDirectory(prefix="graf-permission-restart-") as directory:
        root = Path(directory)
        app = root / "GRAF Permission Proof.app"
        run("ditto", str(source), str(app))
        info["CFBundleIdentifier"] = domain
        with (app / "Contents/Info.plist").open("wb") as stream:
            plistlib.dump(info, stream)
        run("codesign", "--force", "--deep", "--sign", "-", str(app))
        helper = root / "quit.swift"
        helper.write_text('''import AppKit
let target = NSAppleEventDescriptor(processIdentifier: Int32(CommandLine.arguments[1])!)
let event = NSAppleEventDescriptor(
    eventClass: AEEventClass(kCoreEventClass), eventID: AEEventID(kAEQuitApplication),
    targetDescriptor: target, returnID: AEReturnID(kAutoGenerateReturnID),
    transactionID: AETransactionID(kAnyTransactionID))
_ = try event.sendEvent(options: .noReply, timeout: 3)
''')
        run("swiftc", str(helper), "-o", str(root / "quit"))
        run("defaults", "write", domain, active_key, "-bool", "true")
        try:
            # The second process receives no launch override: setup must persist itself.
            for launch in (1, 2):
                log_dir = root / f"launch-{launch}"
                log_dir.mkdir()
                environment = dict(os.environ, GRAF_LOG_DIRECTORY=str(log_dir))
                process = subprocess.Popen(
                    [str(app / "Contents/MacOS" / info["CFBundleExecutable"])],
                    env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                log = log_dir / "graf.log"
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    assert process.poll() is None, "App exited before setup became visible"
                    contents = log.read_text() if log.exists() else ""
                    if "mode=page modal=false sheets=0" in contents:
                        break
                    time.sleep(0.1)
                else:
                    raise AssertionError("Setup did not resume as a nonmodal page")
                started = time.monotonic()
                run(str(root / "quit"), str(process.pid))
                process.wait(timeout=8)
                assert process.returncode == 0, "App did not terminate cleanly"
                contents = log.read_text()
                assert "event=app_termination_cleanup_requested" in contents
                assert "event=app_termination_cleanup_completed detail=reason=cleanup_finished" in contents
                assert "reason=timeout" not in contents, "Quit required fallback timeout"
                assert run("defaults", "read", domain, active_key) == "1", "Quit lost setup intent"
                print(f"PASS launch={launch} nonmodal_page=true quit_cleanup=finished "
                      f"exit=0 elapsed={time.monotonic() - started:.2f}s setup_intent=retained")
                process = None
        finally:
            if process is not None and process.poll() is None:
                # Kill only our failed disposable fixture, never an installed application.
                process.kill()
                process.wait(timeout=5)
            subprocess.run(["defaults", "delete", domain], capture_output=True)


if __name__ == "__main__":
    main()
