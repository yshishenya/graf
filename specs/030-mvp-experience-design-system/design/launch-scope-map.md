# Launch Scope Map

## Surface Classification

| Surface | Type | Launch classification | Dependencies | Gate |
|---|---|---|---|---|
| Native desktop home | native_desktop | required_for_first_launch | accepted recording foundations | capture boundary review |
| Active recording | native_desktop | implemented foundation plus polish | 007, 008, 020, 025 | visible Stop |
| Upload queue | native_desktop | implemented context plus polish | 014 | status truth |
| Embedded cabinet account status | embedded_cabinet | required_for_first_launch | 028, 029 | native boundary |
| Embedded recent meetings | embedded_cabinet | required_for_first_launch | 014, 015, 016 candidate | route matrix |
| Embedded manual upload | embedded_cabinet | required_for_first_launch | 014, 015 | audio-first copy |
| Embedded meeting review | embedded_cabinet | required_for_first_launch | 015, 016 candidate | status matrix |
| Full browser meetings list | browser_cabinet | required_for_first_launch | 016 candidate | web IA |
| Full browser manual upload | browser_cabinet | required_for_first_launch | 014, 015 | upload truth |
| Full browser meeting review | browser_cabinet | required_for_first_launch | 015, 016 candidate | complete review |
| Retention/deletion execution | browser_cabinet | required after design | 018 candidate | deletion truth |
| Public sharing/downloads | browser_cabinet | deferred | 017 candidate | access policy |
| Billing/team/admin/audit/help/legal | browser_cabinet | deferred or browser-only marker | future slices | handoff only |
| Full video review | deferred | out_of_scope_for_mvp | future video slice | no false promise |

## Implemented Context

- `014`: desktop upload queue and server-mediated upload status are already context for design.
- `015`: MediaScribe processing pipeline is in a separate worktree/branch
  (`015-mediascribe-processing-pipeline`). Feature `030` treats it as a
  parallel dependency for processing status, transcription import, and
  transcript-readiness contracts. This worktree does not duplicate or edit
  `015`.
- `028`: provider auth/session defines user/session/device boundaries.
- `029`: email auth and account linking define fallback account surfaces.

## MVP Promise

2brain Rec MVP lets the owner record in the macOS app or upload owned media, see truthful status in desktop and web, wait through transcription, and receive a complete meeting review with transcript, playback context, summary, decisions, action items, provenance, and deletion/access entry points.

## Non-Promises

- No hidden recording.
- No production code implementation in this design slice.
- No full video timeline/review in MVP.
- No copied Krisp UI or assets.
- No universal deletion claim outside what 2brain Rec controls.
