# Portable Harness Agent Guide

This directory contains the generic, dependency-free governance core. Keep
project-specific product, privacy, signing, deployment and data rules in the
consumer adapter.

## Rules

- Read this file and only the README/files needed for the current task.
- Never commit secrets, credentials, signed URLs, private data, raw audio,
  transcript text or machine-specific absolute paths.
- Keep releases immutable SemVer tags. Update changelog, migration notes and
  rollback ref together; never rewrite an existing tag.
- Prefer stdlib/native code and the smallest safe diff. Preserve fail-closed
  validation and leave one runnable self-test for new non-trivial behavior.
- Consumers pin an immutable release and provide their own adapter for build,
  health, signing and deployment behavior.

## Check

```sh
(cd sample && ../bin/harness-check --spec specs/001-example/spec.md)
PYTHONPATH=src python3 -c 'import dev_harness; print(dev_harness.__version__)'
```
