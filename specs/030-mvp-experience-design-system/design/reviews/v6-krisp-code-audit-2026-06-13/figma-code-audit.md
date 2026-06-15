# Figma Programmatic Audit

File key: `ylPz3AxOOfVoLJEG4dF9Yr`
Page: `030 MVP Experience v5 - Full MVP Flow`
Inspection method: Figma Plugin API over live node properties.

## Summary

The current v5 page has 36 frames and 103 button-like candidates. It is broad
enough as a product coverage map, but it is not pixel-perfect enough for
handoff.

## Confirmed Blockers

### 1. Same-Row Button Styling Conflict

Frame: `V5 15 - Meeting review with transcript and timeline`

Row around `y=7388` contains:

| Node | Size | Radius | Problem |
|---|---:|---:|---|
| `button Спикеры` | 108x36 | 0 | stale/incorrect radius |
| `button Действия` | 108x36 | 0 | stale/incorrect radius |
| `button Поделиться` | 108x36 | 7 | inconsistent with adjacent controls |
| `button Экспорт` | 108x36 | 7 | inconsistent with adjacent controls |

The page also still contains older pill controls near the same toolbar area:
`pill Спикеры` and related labels. V6 must remove stale duplicates and define a
single toolbar model.

### 2. Technical Copy Leaks Into Product UI

The audit found visible product-screen text matching technical implementation
patterns:

- `Сервер в сети · RU` across many frames;
- `нативный` / `Нативный слой записи`;
- `серверный маршрут`;
- visible `API`, `Postgres`, `MinIO`, `Temporal`, and `Langfuse` in primary
  product copy.

Some technical names are valid in admin/deletion truth or developer docs, but
they must not appear as first-viewport product labels in the desktop/web MVP.

V6 rule:

- User UI says `Синхронизация работает`, `Офлайн`, `Загрузка идет`,
  `Транскрибация идет`, `Транскрипт готов`.
- Engineering labels move to diagnostics, audit details, or documentation.

### 3. Speaker Lanes Exist But Are Not Yet The Design Contract

`V5 16` and `V5 34` contain lane-like objects, but the overall review IA still
treats speaker assignment as an attached panel rather than a primary review
mode.

V6 rule:

- speaker assignment screen must have one row/lane per speaker;
- each lane shows label, color, segments, talk-time percentage, confidence or
  review state, and row actions;
- transcript turns, playback, and speaker editing must stay connected;
- desktop hosts the same server-owned route; native code must not create a
  separate local speaker editor.

### 4. V5 QA Docs Are Now Incorrect

Existing documents still state:

- `Button size QA: PASS`;
- `Speaker lane model: PASS`;
- `Accepted v5`.

These claims are no longer true after the 2026-06-13 live audit. V5 is
superseded and must be marked as rejected/needs v6.

## V6 Token Contract

| Component | Height | Radius | Notes |
|---|---:|---:|---|
| Primary action | 40 | 8 max | Record, Upload, Save. One primary action per region. |
| Secondary toolbar button | 36 | 7 or 8, consistent in row | Share, Export, Retry, Open. |
| Segment/tab | 32 | 6 | Transcript/Notes/Speakers tabs; separate from toolbar buttons. |
| Chip/filter | 28-32 | 6 | Status/filter tags only. |
| Icon button | 32 | 6 or circle native-equivalent | Tooltip required unless adjacent label exists. |
| Destructive button | 36-40 | 8 max | Delete/Stop; always labeled. |

Programmatic QA for v6 must group controls by visual row and semantic cluster,
then fail when adjacent controls in the same cluster use inconsistent height or
radius.
