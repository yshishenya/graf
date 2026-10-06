# Задачи F281

Umbrella issue: #7391

- [x] T001 Подготовить отдельное руководство, маршрут и sitemap; сверить утверждения и protected diff.
- [x] T002 Проверить HTTP, canonical, ссылки, tracking, mobile 360/390/768 и регрессии public pages.
- [x] T003 Пройти exact-SHA CI и штатный ограниченный выпуск с production read-back.
- [x] T004 Подготовить отдельный учебный guide протокола, маркировку, route/sitemap и копируемый шаблон.
- [x] T005 Проверить metadata/условия/ссылки/copy/mobile, exact-SHA CI и штатную публикацию нового guide.


Предыдущая публикация подтверждена: первый материал `v2026.09.30.2`, второй `v2026.10.01.3`, PR7411/7415, source/runtime/tag216ab38e6eeb112aefa23f8c87cf69bf6f064b08; Full36927435763 SUCCESS и production200/readback PASS.

- [x] T006 Реализовать и проверить `/guides`, типы/реестр публичного контента, взаимные ссылки и единственную footer-ссылку главной; FR006–FR010, (Issue #7419), parent #7391.
- [x] T007 Пройти exact-SHA CI/provenance и штатную публикацию hub с backup, Full/CD и protected production readback; FR010, (Issue #7419), parent #7391.

Hub опубликован в v2026.10.02.2: source/runtime/tag540f322b4de8016d3b920c74fb8a72c3881ad915, Full36941465329 PASS, CD/backup/smoke cleanup/public readback PASS. Доказательства: evidence/guides-hub-publication.json.

- [x] T008 Подготовить третью статью о проверке качества расшифровки, учебные пометки/первоисточники, route/registry/sitemap/related links и прежний L1 surface; FR011–FR015 (Issue #7429).
- [x] T009 Проверить copy/metadata/links/mobile/measurements/protected diff, exact-SHA CI и штатную публикацию с production readback; FR011–FR015 (Issue #7429).

Третья статья опубликована v2026.10.02.3, source721b5125d, Full36949473232 PASS, CD/backup/readback PASS.
- [x] T010 Реализовать и проверить общую шапку и ссылку главной, current/mobile/keyboard/no-JS/unchanged body; FR016–18 (Issue #7431).
- [ ] T011 Пройти exact-SHA PR/Full/CD, backup/recovery и live readback; FR016–18 (Issue #7431).

- [x] T012 Унифицировать оформление трех статей с лендингом; сохранить текст/SEO/ссылки и проверить mobile/text200%/keyboard; FR019–20 (Issue #7435).
- [ ] T013 Пройти exact-SHA CI и штатную публикацию общего дизайна с protected readback; FR019–20 (Issue #7435).

## Предметная помощь по двум источникам звука

- [x] T014 [US4] Подготовить и локально проверить `/help` и статью одной стороны записи в `public/content.py`, `public/web.py`, `public/templates/public/help.html`, `one_sided_audio_help.html`, общую навигацию и `tests/contract/test_public_audio_help.py`; FR021–26 (Issue #7544).
- [x] T015 [US4] Создать узкий draft PR, проверить exact-SHA `governance-fast`, `macos-pr`, `pr-metadata` общим `scripts/validate-pr-checks.py` и записать ограничения в `specs/281-mac-meeting-guide/audio-help-evidence.md`; FR026 (Issue #7544). Исходный draft-срез не включает merge/release/deploy.

T015 подтверждена на исходном head `6fe34ead257b8c10fecde4605c5ca7f4af17a4b6`: PR7545, governance-fast37364831663 attempt2, macos-pr37364831594 attempt2, pr-metadata37364833578 attempt1 SUCCESS, общий exact-SHA validator PASS. При обновлении базы требуется новый proof; прежний PASS его не заменяет.

- [x] T016 [US4] Выполнить отдельно разрешенную публикацию Help: актуальный exact-SHA PR proof, завершенный чужой baseline, frozen Full, штатные backup/CD/health и production HTTP200/canonical/sitemap/navigation/mobile/protected readback; FR027–28 (Issue #7544). Свежая штатная копия GRAF разрешена владельцем 2026-10-06; новое хранилище и резервный PostHog исключены. Незавершенный F286 автоматически не выпускать.

Условие отдельной базы T016 подтверждено: F286 v2026.10.06.1 опубликован 2026-10-06 на29264c66520ee36b1a2f287fa7edd6e92139dd9f, Full37527256994 SUCCESS; CD durable result deployed, migration0104, live/ready200 и lock освобожден. Это не proof собственного будущего Help Full/CD.

T016 завершена: v2026.10.07.1 опубликован 2026-10-06T22:25:10Z, source
`ad597c114e3bf9e627525c578ec68e353d54a44e`. Единственный Full37537979359 SUCCESS,
candidate `rc-20261006T220142Z-95a12ddbc931`, train/decision go. Штатный CD PASS,
attempt `599561ecaa474082b65ce28cfe345373`, свежий backup
`/opt/projects/2brain-rec/backups/20261006T221459Z`; публикация подтверждена
immutable attestation 22:25:18Z. Live Help/guides/canonical/sitemap/navigation,
Chromium320/390/768/1440,text200%,keyboard/noJS и protected/source readback PASS.
Полные границы проверки и доказательства — в `audio-help-evidence.md`.
