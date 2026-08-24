#!/usr/bin/env python3
"""Compatibility entry point for the metadata-only summary-slot reconciler.

The former script generated outcomes and read the retired meeting-global pointer.
Use the slot command instead; it performs no model call and never reads content.
"""

from __future__ import annotations

from twobrain_rec_server.cli.summary_slots import main as summary_slots_main

if __name__ == "__main__":
    summary_slots_main()
