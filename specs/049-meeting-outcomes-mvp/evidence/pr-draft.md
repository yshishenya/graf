# PR Draft: 049 Meeting Outcomes MVP

## PR Title

feat(cabinet): Add stored meeting outcomes for MVP

## PR Body

### Что изменилось

- Добавлены сохраненные итоги встречи: резюме, ключевые пункты, решения,
  действия, follow-up, риски, вопросы и evidence-состояния.
- Итоги строятся только из подтвержденной расшифровки. Если надежной опоры нет,
  категория показывает `not_found` или `not_inferable`, а не выдумывает текст.
- Веб-кабинет и встроенное окно macOS используют один server-owned review
  response: итоговые категории, source evidence rows, playback и transcript
  остаются вместе.
- Outcome content включен в privacy/deletion/RLS boundary: denied/deleted/list
  surfaces не раскрывают текст, deletion reports учитывают materialized
  outcomes, RLS inventory покрывает новые таблицы.
- Readiness truth обновлена: `notes-action-output` закрыт только stored outcome
  evidence, но production rollout остается отдельным gate.

### Как проверено

- RED/GREEN по outcome contracts, migration/RLS, generator/service/cabinet,
  browser parity, privacy/deletion/RLS и readiness truth.
- Focused quickstart validation:
  - server outcomes: `39 passed, 1 warning`;
  - migration/RLS: `6 passed, 1 warning`;
  - browser runtime verifier: `failures=[]`;
  - one-hour orchestration budget: `1 passed, 1 warning`;
  - readiness truth: `22 passed, 1 warning`.
- Full local CI: `ci_local_result=pass`; server tests `600 passed, 4 skipped,
  90 warnings`; server lint, Python compile and deployment evidence scan passed.
- Deploy dry-run: `deploy_result=dry_run`, branch `049-meeting-outcomes-mvp`,
  remote host `2brain.dev`, remote path `/opt/projects/2brain-rec`.
- Forbidden-content scans returned no matches for specs, docs, changelog and
  PR/release draft evidence.

### Совместимость и миграции

- Добавляется Alembic migration `0009_meeting_outcomes_mvp` с таблицами:
  `meeting_outcome_sets`, `meeting_outcome_items`,
  `meeting_outcome_generation_attempts`.
- OpenAPI contract обновлен под расширенный `notes_action_truth` response.
- Старые встречи без outcome rows продолжают показывать truthful deferred,
  processing, blocked или unavailable states.
- Desktop app changes не требуются: macOS embedded review использует тот же
  server-owned route.

### Ограничения

- Это не production rollout proof. После merge/release нужен обычный deploy
  closeout и production user-journey evidence.
- Это deterministic/extractive MVP outcome layer, не редактор, не ручное
  исправление итогов, не публичный share-link и не provider-quality tuning.
- Outcome quality ограничена качеством transcript/diarization source.

### Issue Links

Refs feature `049-meeting-outcomes-mvp` issues `#1637-#1704`.

## Release Notes Draft

### Добавлено

- В результате встречи появились сохраненные итоги: краткое резюме, ключевые
  пункты, решения, действия, follow-up, риски, вопросы и ссылки на evidence.
- Итоги видны и в веб-кабинете, и во встроенном окне macOS-приложения.

### Изменено

- Readiness теперь честно считает `notes-action-output` закрытым только когда
  есть stored outcomes evidence.

### Безопасность

- Outcome text не отдается в списке встреч и скрыт для denied/deleted/deleting
  состояний.
- Deletion flow учитывает сохраненные итоги, а RLS coverage включает новые
  outcome tables.

### Известные ограничения

- Релиз не означает готовность к user rollout. Нужны deploy closeout и
  production user-journey proof.
- Итоги являются MVP-слоем на базе расшифровки; editing и улучшение качества
  остаются отдельными задачами.

## Production Closeout Plan

1. После PR merge подготовить CalVer release через `./scripts/prepare-release.sh`.
2. Опубликовать GitHub Release с русскими release notes.
3. Выполнить `infra/scripts/cd-remote.sh --dry-run`.
4. После release gate выполнить `infra/scripts/cd-remote.sh --execute`.
5. Проверить production health live/ready.
6. Выполнить metadata-only owner journey proof без transcript text, audio,
   meeting IDs, account identifiers, signed URLs или private paths.
7. Закрыть полностью выполненные GitHub issues с русскими closure comments и
   evidence ссылками.
