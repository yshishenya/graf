# Security Checklist: Глобальный автозапуск и defaults

**Feature**: [spec.md](../spec.md)

- [x] Global scope requires an explicit approval flag.
- [x] Empty workspace ID is never treated as wildcard without global flag.
- [x] Ambiguous global + workspace configuration fails closed.
- [x] Policy references are opaque hashes and do not expose raw IDs.
- [x] Acknowledgement remains user/workspace/device-bound.
- [x] Legacy settings migration does not silently enable auto-record.
- [x] Diagnostics remain metadata-only and credential-free.
- [x] External/customer notice rollout is explicitly out of scope.
