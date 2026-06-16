from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from twobrain_rec_server.readiness import build_default_readiness_report, write_readiness_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 034 MVP loop readiness evidence.")
    parser.add_argument(
        "--output-dir",
        default="../../docs/evidence/034-mvp-loop-readiness",
        help="Directory for readiness-report.json, readiness-report.md, and launch-gap-register.md.",
    )
    parser.add_argument(
        "--deployed-commit",
        default=None,
        help="Current deployed commit. Defaults to the local git HEAD when omitted.",
    )
    args = parser.parse_args()

    deployed_commit = args.deployed_commit or _git_head()
    output_dir = Path(args.output_dir).resolve()
    report = build_default_readiness_report(deployed_commit=deployed_commit)
    write_readiness_outputs(report, output_dir)
    print(f"readiness_report={output_dir / 'readiness-report.json'}")
    print(f"readiness_markdown={output_dir / 'readiness-report.md'}")
    print(f"launch_gap_register={output_dir / 'launch-gap-register.md'}")


def _git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


if __name__ == "__main__":
    main()

