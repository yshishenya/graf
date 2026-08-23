# Quickstart: Upload Status UX

1. Start the local GRAF server using the repository's local workflow.
2. Sign in to the cabinet and open `Мои встречи`.
3. Seed or use a manual upload with no source recording timestamp.
4. Confirm the row shows `Загружено <date>, <time>` and a distinct processing state.
5. Start another upload and confirm the compact activity card keeps state, percentage, violet bar, and action together without an empty middle area.
6. Exercise cancel, retry, accepted, and server-waiting states.
7. Open the upload dialog and confirm short copy plus violet checkbox/radio/focus treatment.
8. Open Settings overview and at least one detail page; confirm stable one-line desktop navigation rows and readable helper text.
9. Repeat the main, dialog, and Settings checks at a 375px viewport and with keyboard focus.

Expected: no «Без даты» for a manual upload with a server creation time, no product-blue GRAF accent, no detached percentage, no drifting Settings labels, no clipped actions, and no relevant browser console errors. Provider brand marks may keep official blue.
