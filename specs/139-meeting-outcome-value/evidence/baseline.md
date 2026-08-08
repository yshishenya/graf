# Baseline evidence: meeting-outcome-value

- Дата: 2026-08-04
- Lane: high-risk AI/UX + release/deploy
- Контент: только synthetic; реальные transcript, audio, model output и judge feedback не использовались.
- Harness: `node specs/139-meeting-outcome-value/evidence/meeting-outcome-runtime-check.cjs`
- Browser: выбранный in-app Browser; desktop `1280×720`, mobile `390×844` CSS px.

## Зафиксированные состояния

| Состояние | Baseline | Наблюдение до изменений |
|---|---|---|
| Accepted owner | `01-current-accepted.jpg` | Сохранённые итоги были компактными, но runtime-источник и speaker provenance не были подтверждены полным циклом. |
| Ready candidate | `02-current-candidate.jpg` | Предпросмотр показывал технические category labels и плоские пункты; owner/due/source было трудно проверить до принятия. |
| Processing | runtime harness | Нужна одна агрегированная причина без повторов и выдуманного текста. |
| No player/transcript | runtime harness | Источник не должен выглядеть кликабельным без реального destination. |
| Summary-only | runtime harness | Browser entry должен отдавать локализованный HTML accepted projection, не JSON. |

Объединённое сравнение baseline и финального состояния при одинаковом desktop
viewport: `10-baseline-vs-after.jpg`.

## Forbidden content

В committed evidence запрещены реальные названия и содержимое встреч, исходные
аудиофайлы, transcript/model output, free-form judge feedback, credentials, tokens, secret
paths, signed URLs и Langfuse/private-heldout content. Разрешены только synthetic
labels, hashes, counts, versions, metric values и bounded error codes.
