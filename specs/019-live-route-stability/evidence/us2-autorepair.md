# US2 Autorepair Evidence

US2 evidence must show that supported external disruptions recover automatically and only report healthy after fresh client activity evidence.

Required metadata-only facts:

- autorepair trigger and timing tier
- attempt id, start time, completion time, outcome, and fresh-evidence timestamp
- resulting route state, including blocked non-recoverable reasons when applicable
- explicit user action audit events, especially `run_check`, recorded as diagnostic fallback rather than normal accepted recovery
- accepted macOS default route classes: built-in, wired, USB
- blocked or backlog route classes: Bluetooth, AirPods-class, aggregate, multi-output, HDMI/AirPlay, other virtual, unknown

Do not include raw audio, transcripts, meeting content, secrets, signed URLs, uploads, MediaScribe calls, or Langfuse traces.
