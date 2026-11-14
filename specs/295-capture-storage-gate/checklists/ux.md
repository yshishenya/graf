# UX Checklist: Честная проверка локального места

**Review Ownership**: reviewer-owned UX-quality artifact.

**Prior review**: 2026-11-14 — FAIL; CHK008 open; CHK011 and CHK012 added after that review. Final re-review 2026-11-14 — PASS, 12/12.

- [x] CHK001 Warning is visibly informational, not an error card.
- [x] CHK002 Warning does not hide idle/record controls or set `hasActionableProblem`.
- [x] CHK003 Warning copy is plain Russian and explains the action without jargon.
- [x] CHK004 Critical/full/reserve blocker explains what to free or change.
- [x] CHK005 `.failed` tray state shows “Повторить запись” and a safe reason.
- [x] CHK006 `.failed` does not show the red recording light; `.degraded`/`.stopping` do.
- [x] CHK007 Active recording still shows Stop and timer.
- [x] CHK008 VoiceOver labels cover warning, failed reason and active stop.
- [x] CHK011 Warning card exposes a full accessibility label, not only visible copy.
- [x] CHK012 Failed-reason row exposes the full safe reason to VoiceOver, with visible truncation and tooltip.
- [x] CHK009 Long reason text is truncated in the menu with a full tooltip.
- [x] CHK010 F284 local playback and local-only labels are unchanged.

**Final review 2026-11-14**: 12/12 checked; CHK008, CHK011 and CHK012 closed after the plan update. See [review-2026-11-14-final.md](review-2026-11-14-final.md).
