# Quickstart: Upload Status UX

1. Start the local GRAF server using the repository's local workflow.
2. Sign in to the cabinet and open `Мои встречи`.
3. Seed or use a manual upload with no source recording timestamp.
4. Confirm the row shows `Загружено <date>, <time>` and a distinct processing state.
5. Start another upload and confirm the compact activity card keeps state, percentage, violet bar, and action together without an empty middle area.
6. Exercise cancel, retry, accepted, and server-waiting states.
7. Open the upload dialog and confirm `Сохранить аудио` is aligned with a violet switch and its secondary explanation opens from the information button by hover and keyboard focus.
8. Open Account Settings and confirm light, dark, and system appear as one segmented native radio group with icons and live preview.
9. Open Notifications and Calendar Settings; confirm independent preferences use the same switch while calendar multi-selection remains checkbox-based.
10. Confirm security, billing, storage, and irreversible-action consequences remain visible rather than tooltip-only.
11. Repeat the main, dialog, and Settings checks at a 375px viewport and in light/dark themes with keyboard focus.
12. Build the macOS package and confirm native readiness, upload, meeting-prompt, and recording-action accents use the shared violet token rather than system blue.
13. Open an unavailable meeting directly and trigger meeting access loss from an open detail page; confirm both show the same compact state and standard action while private content, title, URL, focus, and history are cleaned up.
14. Open an unavailable invitation and an empty `Поделились со мной` page; confirm they reuse the shared state component while inline Settings and billing notices remain inline.
15. Repeat the shared-state checks at 375px and 200% zoom, then run the full CI, release, notarization, deployment, and exact-SHA smoke gates.

Expected: no «Без даты» for a manual upload with a server creation time, no product-blue GRAF accent in web or native macOS product surfaces, no detached percentage, no drifting Settings labels, no clipped actions, no misaligned binary controls, no hidden critical copy, no oversized unavailable card, no `new-button`, and no relevant browser console errors. Provider brand marks may keep official blue.
