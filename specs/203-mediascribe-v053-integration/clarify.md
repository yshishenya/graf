# Clarification: MediaScribe v0.5.3 integration fidelity

**Date**: 2026-08-25
**Result**: No blocking clarification questions remain.

The following decisions are carried into planning and implementation:

1. Provider diarization blocks are authoritative. GRAF must not duplicate the provider’s merge, pause, punctuation or length rules.
2. An omitted `source_role` on a normal single-track result means `mixed`; a missing role on a dual-track result is degraded/unknown rather than guessed.
3. `words` are typed and retained durably with diarization rows, but a new word-highlight interaction is out of scope.
4. Existing Feature 195 Temporal timers, manual check and recovery state are reused. A Temporal change is made only if the v0.5.3 contract tests expose a concrete gap.
5. Deployment and provider-side changes are out of scope; this slice stops after local validation and evidence.
