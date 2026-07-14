# Test Fixture Hygiene

Fixtures under this directory are synthetic and deterministic. Feature 099
must not commit media binaries, copied recordings, raw audio, transcript or
summary content, original filenames, object keys, signed URLs, credentials, or
private paths.

`playback_normalization.py` builds short in-memory PCM WAV bytes and allowlisted
probe/state dictionaries. Real format-matrix fixtures are generated inside a
disposable media container or a feature-specific temporary directory and are
deleted after validation. Authorized `test-rec` originals are copied to a
temporary working directory and remain read-only.

Evidence may contain only safe aliases, versions, format/profile facts,
size/duration buckets, state/reason counts, timestamps and cleanup results.
