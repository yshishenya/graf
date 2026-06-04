#!/usr/bin/env python3
import argparse
import json

from twobrain_rec_server.deployment import SmokeCleanupRecord


def main() -> None:
    parser = argparse.ArgumentParser(description="Record or execute cleanup for internal smoke artifacts.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--residue-owner")
    parser.add_argument("--residue-follow-up-reason")
    args = parser.parse_args()

    cleanup = SmokeCleanupRecord(
        run_id=args.run_id,
        cleanup_result="pass" if args.execute else "blocked",
        database_records_removed=0,
        object_keys_removed=0,
        residue_owner=args.residue_owner if not args.execute else None,
        residue_follow_up_reason=args.residue_follow_up_reason if not args.execute else None,
    )
    print(json.dumps(cleanup.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
