# Security Checklist: MediaScribe Result Contract

- [x] CHK001 MediaScribe remains server-side; browser and desktop clients do not receive MediaScribe credentials. [Constitution III]
- [x] CHK002 Diagnostic metadata excludes raw audio, transcript text, credentials, signed URLs, object keys, and external download URLs. [Constitution III, Spec Edge Cases]
- [x] CHK003 Normal product UI does not expose external MediaScribe job IDs or dependency download URLs. [Product Gate]
- [x] CHK004 Failure-source persistence does not weaken tenant isolation or RLS inventory. [Constitution III]
- [x] CHK005 Input-audio business outcomes do not create a new deletion or external erasure promise. [Constitution IV]
- [x] CHK006 Langfuse/content tracing behavior is unchanged and metadata-only by default. [Constitution III]
