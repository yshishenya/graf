# AI Content Boundary Requirements Checklist: Complete Recording Workflows

## Langfuse content contract

- [x] CHK001 Is exactly one Langfuse generation required for each completed response durably captured by GRAF, with ambiguous pre-persist egress reported truthfully? [Completeness, Spec §FR-071, FR-091]
- [x] CHK002 Are complete plaintext request/transcript/raw-response/validated-result fields allowed across the explicit AI workflow observations while ordinary logs, audit, diagnostics, screenshots, and evidence remain metadata-only? [Consistency, Spec §FR-056, FR-071]
- [x] CHK003 Are raw audio and runtime credentials excluded by explicit source-field construction while credential-like meeting speech remains verbatim without masking? [Security, Spec §FR-071]
- [x] CHK004 Is one sole Langfuse publisher required to keep completed-call delivery durably pending until confirmation, independently of model retry, candidate readiness, and meeting deletion? [Reliability, Spec §FR-070–FR-073]
- [x] CHK005 Are the configured private Langfuse destination/environment, no-public-trace rule, operator-managed role access/retention, and deliberate no-GRAF-delete behavior explicit? [Governance, Spec §FR-078]

## Temporal content contract

- [x] CHK006 Is the complete canonical transcript required in Temporal History as deterministic plaintext chunks using the default converter? [Completeness, Spec §FR-088]
- [x] CHK007 Is the absence of Feature-121 PayloadCodec, encryption, redaction, masking, truncation, key ring, Codec endpoint, and History deletion explicit? [Simplicity, Spec §FR-088]
- [x] CHK008 Are deterministic pre-serialization and post-serialization chunk sizes, the 8-MiB canonical transcript/snapshot ceiling, Temporal payload/transaction/history limits, and oversized fail-closed behavior measurable? [Reliability, Spec §FR-089]
- [x] CHK009 Are plaintext chunk identity/count/order/duplicate/UTF-8/final-hash checks specified without an assembler service? [Correctness, Spec §FR-092]
- [x] CHK010 Are Search Attributes and Memo bounded as operational indexes rather than transcript stores? [Reliability, Spec §FR-088]
- [x] CHK011 Does meeting deletion cancel pre-egress work while preserving completed Generation Call delivery until Langfuse confirmation and retaining all three observability copies with truthful reporting? [Lifecycle, Spec §FR-073, FR-090]

## Optimization boundary

- [x] CHK012 Are real meeting-derived optimizer data still prohibited while exact synthetic model-call generations are allowed? [Scope, Spec §FR-084]
- [x] CHK013 Are complete plaintext synthetic inputs, outputs, feedback, and optimizer state allowed in Langfuse/Temporal while owner-controlled checkpoints remain resume authority and GRAF purge leaves those observability copies retained? [Observability, Spec §FR-082, FR-084]

## Measurability

- [x] CHK014 Does synthetic acceptance prove exact model-call content in Langfuse/Generation Call, exact-or-unknown usage/cost provenance, the exact transcript in Temporal History, size ceilings, no masking/truncation, durable fail-open delivery, and retained-observability deletion copy? [Measurability, Spec §FR-079, SC-015, SC-017]

## Notes

- 14/14 content-boundary requirement-quality checks pass on 2026-07-22 against constitution v4.0.0.
- These checks validate the written contract; runtime proof remains in T040,
  T042, T050, T073, T078, T089, and T091.
