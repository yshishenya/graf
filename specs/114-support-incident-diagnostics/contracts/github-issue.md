# Contract: Private GitHub Issue for runtime support incidents

## Title and labels

Runtime-created issues use:

```text
[114][P0|P1|P2][support/custody] T000: <короткое описание problem code>
```

Required labels include `feature:114`, the computed priority, `type:bug`,
`area:macos`, `area:api`, `area:privacy`, `source:user-report`,
`privacy:metadata-only` and `needs-triage`. The target repository must remain
private and be exactly `yshishenya/crisp`.

## Body

The generated block contains, in order:

1. CUST and sync status;
2. client/server report fingerprints and dedupe key;
3. canonical stage/problem/owner/next action;
4. a state matrix for local copy, server copy, upload, processing, deletion and
   risk;
5. bounded timeline and retry summary;
6. affected count/fingerprints;
7. full canonical redacted JSON in a fenced block.

Human sections outside the generated block remain intact when a deduped issue is
updated. The body must never contain raw paths, file names, secrets, tokens,
URLs with signed parameters, transcript/audio/content, email/name or raw UUID.
