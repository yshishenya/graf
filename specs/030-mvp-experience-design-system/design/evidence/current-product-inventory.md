# Current Product Inventory

## Evidence Sources

- Installed app metadata: local 2brain Rec macOS app reports version `0.1.0`,
  bundle id `pro.2brain.rec`.
- Runtime metadata: `2brain Rec.app` launches as a local macOS process.
- Repository structure: native macOS app under `apps/macos/RecApp`, shared macOS code under `apps/macos/Shared`, server under `apps/server`.
- Spec baseline: `014` desktop upload queue is current local context; `015`
  MediaScribe processing is active in a separate worktree/branch and supplies
  parallel processing/transcript contracts for this design slice.
- Auth/account context: `028` provider auth/session and `029` email/account linking remain source specs for sign-in and account state.

## Accepted Foundations For MVP Experience

| Area | Status | Design implication |
|---|---|---|
| macOS native recording shell | Accepted foundation | Design must preserve visible local capture truth and one-action Stop. |
| Local recording artifact truth | Accepted foundation | UI can show local saved/local-only/queued without promising upload. |
| Desktop upload queue | Implemented context | UI must distinguish queued/uploading/uploaded from transcript readiness. |
| MediaScribe processing pipeline | Parallel worktree dependency | UI can represent extraction/transcription/transcript stages only when aligned with `015`; notes display remains owned by later dashboard/review work. |
| Auth/session/account linking | Source specs exist | UI must separate auth state from local recording truth. |
| Web cabinet/review UI | Launch gap | Needs designed screens before implementation. |
| Retention/deletion execution | Launch gap | Needs truthful entry points and later lifecycle implementation. |

## Not Proven By Current Evidence

- Live visual inspection confirmed the installed app is diagnostics-first and
  does not expose the launchable cabinet/review/upload experience yet.
- `https://rec.2brain.dev` did not return useful quick curl output during this pass, so live web cabinet review is repo/spec based.
- No production rollout readiness is claimed by this feature.
