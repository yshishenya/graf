# Research: meeting-summary-ux

Дата исследования: 2026-08-04. Источники использованы как UX references, не как
копирование бренда или визуального языка.

## Наблюдения из продуктов

- [Krisp: Meetings page](https://help.krisp.ai/hc/en-us/articles/10291109632412-Meetings-page-in-account-dashboard)
  держит Notes простыми: Key Points и Action Items видны сразу, а подробный
  Outline создаётся отдельно и не занимает первый экран. Action Items можно
  править, но это отдельный рабочий слой, а не набор постоянных статусных
  карточек.
- [Krisp: AI meeting transcription](https://krisp.ai/meeting-transcription/)
  показывает спокойную пару Notes/Transcript, короткий summary и action items
  без отдельной панели provenance для каждого пункта.
- [Otter: Conversation Page Overview](https://help.otter.ai/hc/en-us/articles/5093228433687-Conversation-Page-Overview)
  разделяет Summary и Transcript, показывает outline/action items и связывает
  action item с местом в transcript.
- [Otter: Meeting Summary Overview](https://help.otter.ai/hc/en-us/articles/9156381229079-Meeting-Summary-Overview)
  выделяет общий summary, highlights и action items как разные полезные слои,
  а не как один технический список.
- [Otter: Export Summary](https://help.otter.ai/hc/en-us/articles/39503855767191-Export-Summary)
  показывает ценность отдельного копирования полного summary и отдельных
  секций/action items.
- [Microsoft Teams: Recap](https://support.microsoft.com/en-us/teams/meetings/recap-in-microsoft-teams)
  собирает recording, transcript, notes, agenda и follow-up tasks в одном
  recap-контексте и предупреждает о необходимости проверить AI-generated
  content.
- [Microsoft Teams: Custom recap summaries](https://support.microsoft.com/en-us/teams/meetings/customize-recap-summaries-in-microsoft-teams)
  подтверждает полезность шаблона/структуры summary, но не требует менять
  текущий GRAF candidate/accept lifecycle.
- [Read AI transcription](https://www.read.ai/transcription) группирует summary,
  topics, action items и key questions и даёт путь к impactful transcript
  moments.
- [Granola transcription](https://docs.granola.ai/help-center/taking-notes/transcription)
  держит transcript доступным отдельно и поддерживает работу с отдельными
  фрагментами, что поддерживает принцип «итог → доказательство».
- [Granola action items](https://www.granola.ai/blog/meeting-action-items-ai-extraction)
  подчёркивает owner, due date, commitment и source/context; условные
  формулировки требуют человеческой проверки.
- [Fathom summary templates](https://help.fathom.video/en/articles/640768)
  показывает, что section-oriented summary и follow-up email полезны, но
  экспорт/рассылка остаются отдельными действиями.
- [Microsoft Research: Summaries, Highlights, and Action items](https://www.microsoft.com/en-us/research/publication/summaries-highlights-and-action-items-design-implementation-and-evaluation-of-an-llm-powered-meeting-recap-system/)
  подтверждает, что summary, highlights и action items — разные поверхности
  принятия решений и должны оцениваться отдельно.

## Вывод для GRAF

P0 должен быть не новым «AI workspace», а спокойным review-слоем поверх
существующих stored outcomes: один Notes-документ с кратким summary, actions и
decisions, затем один collapsed-блок дополнительных разделов. Сохраняются
условные owner/due, простой source seek, truthful states и тот же
transcript/player. Cross-meeting search, editing, assignment и integrations
требуют отдельного scope, прав и audit trail.

## Локальные источники

- `apps/server/src/twobrain_rec_server/cabinet/view_models.py` уже сохраняет
  `owner_text`, `due_date_text`, `truth_label` и `source_refs`.
- `apps/server/src/twobrain_rec_server/cabinet/rendering.py` уже получает
  source/owner/due поля из view model; UI должен выводить их компактно и только
  при наличии.
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
  уже умеет `data-seek-seconds` и detail tabs.
- Синтетические desktop/mobile screenshots сохранены вне репозитория:
  `/Users/yshishenya/.codex/visualizations/2026/08/03/019fc8b1-c3c5-7031-9376-03a6fd32912e/meeting-summary-current-desktop.png`
  и `meeting-summary-current-mobile.png`. Они не содержат реальных встреч.
